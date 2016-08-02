# -*- coding: utf-8 -*-
import os
import json
import warnings
import operator
import collections

import numpy as np
import scipy.stats
from scipy.stats import probplot
import matplotlib
matplotlib.rcParams.update({'font.size': 16})
import matplotlib.pyplot as figure

from sympathy.api import qt
import colormaps as cmaps


QtGui = qt.QtGui
cmap = cmaps.viridis

ALPHA_LIMIT = 0.1  # Allowed risk of rejecting a correct distribution

FONTSIZE = 8

DEBOUNCE_TYPES = collections.OrderedDict((
    ('Count sequences (default)', 'count_seq_acc'),
    ('Count sequences, non-accumulative', 'count_seq_nonacc'),
    ('Count intervals', 'count_int_acc')))

NUMBER_TYPES = collections.OrderedDict((
    ('None', None),
    ('Same as debounce type (default)', 'heatmap'),
    ('Count sequences', 'count_seq_acc'),
    ('Count sequences, non-accumulative', 'count_seq_nonacc'),
    ('Count intervals', 'count_int_acc')))

SPLIT = collections.OrderedDict((
    ('Count high values', 'count_high'),
    ('Count low value', 'count_low'),
    ('Split at zero', 'split_zero'),
    ('Split at Y axis mean', 'split_mean')))

DISTRIBUTIONS = collections.OrderedDict((
    ('Uniform', 'uniform'),
    ('Normal', 'norm'),
    ('Log Normal', 'lognorm'),
    ('Exponential', 'expon'),
    ('Logistic', 'logistic'),
    ("Student's t", 't'),
    ('Beta', 'beta'),
    ('Gamma', 'gamma'),
    ('Rayleigh', 'rayleigh'),
    ('Generalized Pareto', 'genpareto'),
    ('Generalized extreme value', 'genextreme'),
    ('Weibull', 'dweibull')))


class IHeatMapAccumulator(object):
    def __init__(self):
        raise NotImplementedError

    def add_data(self, data):
        raise NotImplementedError

    def value(self):
        raise NotImplementedError


class CountAccumulator(IHeatMapAccumulator):
    def __init__(self):
        self._count = 0

    def add_data(self, data):
        self._count += data.size

    def value(self):
        return self._count


class MinAccumulator(IHeatMapAccumulator):
    def __init__(self):
        self._min = None

    def add_data(self, data):
        if not data.size:
            return
        if self._min is None:
            self._min = data.min()
        else:
            self._min = min(self._min, data.min())

    def value(self):
        return self._min


class MaxAccumulator(IHeatMapAccumulator):
    def __init__(self):
        self._max = None

    def add_data(self, data):
        if not data.size:
            return
        if self._max is None:
            self._max = data.min()
        else:
            self._max = max(self._max, data.max())

    def value(self):
        return self._max


class MeanAccumulator(IHeatMapAccumulator):
    def __init__(self):
        self._means = []
        self._counts = []

    def add_data(self, data):
        self._means.append(data.mean())
        self._counts.append(data.size)

    def value(self):
        return (np.sum(m * c for m, c in zip(self._means, self._counts)) /
                np.sum(self._means))


class MedianAccumulator(IHeatMapAccumulator):
    def __init__(self):
        self._values = []

    def add_data(self, data):
        self._values.append(data)

    def value(self):
        if self._values:
            return np.median(np.vstack(self._values))
        else:
            return np.nan


REDUCE_FUNCTION = collections.OrderedDict((
    ('Count', CountAccumulator),
    ('Min', MinAccumulator),
    ('Max', MaxAccumulator),
    ('Mean', MeanAccumulator),
    ('Median', MedianAccumulator)))


def grow_range(range_, factor):
    mean = np.mean(range_)
    diff = abs(mean - range_[1])
    new_range = (mean - factor*diff, mean + factor*diff)
    return new_range


def get_label(data_adaf, signal_name):
    unit = data_adaf.ts[signal_name].unit()
    if unit:
        return u"{} [{}]".format(signal_name, unit)
    else:
        return signal_name


def get_label_adafs(data_adafs, signal_name):
    for data_adaf in data_adafs:
        unit = data_adaf.ts[signal_name].unit()
        if unit:
            return u"{} [{}]".format(signal_name, unit)
    return signal_name


def outside_range_text(x=None, y=None, dims=None):
    """Return a text saying how many samples are outside the figure and
    possibly what the data ranges in are."""
    def outside_dim_range_text(data, range_, label):
        if not len(data) or np.all(np.isnan(data)):
            return [], ''
        min_, max_ = range_
        data = data[np.logical_not(np.isnan(data))]
        range_line = u"{}: [{:.2f}, {:.2f}]".format(
            label, min(data), max(data))
        samples_outside = np.logical_or(data < min_, data > max_)
        return samples_outside, range_line

    if dims is None:
        dims = []
    if x is not None:
        dims.insert(0, (x[0], x[1], u"Data x-range"))
    if y is not None:
        dims.insert(0, (y[0], y[1], u"Data y-range"))

    count = 0
    range_lines = []
    samples_outside = []
    for data, range_, label in dims:
        samples_outside_dim, range_line = outside_dim_range_text(
            data, range_, label)
        if any(samples_outside_dim):
            range_lines.append(range_line)
            samples_outside.append(samples_outside_dim)
    count = np.count_nonzero(np.logical_or.reduce(samples_outside))

    if count:
        return u"Samples outside figure: {}<br>{}".format(
            count, u"<br>".join(range_lines))
    else:
        return u""


class OutsideSamplesAccumulator(object):
    """Return a text saying how many samples are outside the figure and
    possibly what the data ranges are."""
    def __init__(self, x_limits=None, y_limits=None, dims=None):
        self.count = 0
        self.outside = []
        self.limits = []
        self.ranges = []
        self.labels = []

        if x_limits is not None:
            self.limits.append(x_limits)
            self.labels.append(u"Data x-range")
            self.ranges.append((np.inf, -np.inf))
            self.outside.append(False)
        if y_limits is not None:
            self.limits.append(y_limits)
            self.labels.append(u"Data y-range")
            self.ranges.append((np.inf, -np.inf))
            self.outside.append(False)
        if dims is not None:
            for label, limits in dims:
                self.limits.append(limits)
                self.labels.append(label)
                self.ranges.append((np.inf, -np.inf))
                self.outside.append(False)

    def _max_range(self, r1, r2):
        return min(r1[0], r2[0]), max(r1[1], r2[1])

    def add_data(self, x_data=None, y_data=None, dims_data=None):
        all_data = []
        if x_data is not None:
            all_data.append(x_data)
        if y_data is not None:
            all_data.append(y_data)
        if dims_data is not None:
            all_data.extend(dims_data)

        samples_outside = []
        for i, data in enumerate(all_data):
            if not len(data):
                continue

            self.ranges[i] = self._max_range(
                self.ranges[i], (min(data), max(data)))
            finite_data = data[np.logical_not(np.isnan(data))]
            samples_outside_dim = np.logical_or(
                finite_data < self.limits[i][0],
                finite_data > self.limits[i][1])
            if any(samples_outside_dim):
                samples_outside.append(samples_outside_dim)
                self.outside[i] = True
        self.count += np.count_nonzero(np.logical_or.reduce(samples_outside))

    def text(self):
        range_lines = [
            "{}: [{:.2f}, {:.2f}]<br>\n".format(l, r[0], r[1])
            for l, r, o in zip(self.labels, self.ranges, self.outside) if o]

        if self.count:
            return u"<b>Samples outside figure:</b> {}<br>\n{}".format(
                self.count, u"".join(range_lines))
        else:
            return u""


def missing_signals_text(data_adafs, signal_names):
    missing_signals = collections.defaultdict(int)
    for data_adaf in data_adafs:
        try:
            all_missing_signals = json.loads(
                data_adaf.meta['missing_signals'].value()[0])
        except:
            continue

        for signal_name in signal_names:
            if signal_name in all_missing_signals:
                missing_signals[signal_name] += 1

    if missing_signals:
        text = ("<b>Missing signals:</b><br>\n" +
                "".join(
                    ["{} ({} file{})<br>\n".format(
                        s, count, "" if count == 1 else "s")
                     for s, count in missing_signals.iteritems()]))

        return text
    else:
        return ""


def aliases_text(data_adafs, signal_names):
    aliases = collections.defaultdict(int)
    for data_adaf in data_adafs:
        try:
            all_aliases = json.loads(
                data_adaf.meta['used_aliases'].value()[0])
        except:
            continue

        for src, dst in all_aliases.iteritems():
            if dst in signal_names:
                aliases[(src, dst)] += 1

    if aliases:
        text = ("<b>Alterate signals:</b><br>\n" +
                "".join(
                    ["{}: {} ({} file{})<br>\n".format(
                        s, d, count, "" if count == 1 else "s")
                     for (s, d), count in aliases.iteritems()]))

        return text
    else:
        return ""


def add_dataset_meta_multiple(adaf_files, name, value):
    for adaf_file in adaf_files:
        add_dataset_meta(adaf_file, name, value)


def add_dataset_meta(adaf_file, name, value):
    meta_len = adaf_file.meta.number_of_rows()
    adaf_file.meta.create_column(u'DATASET_{}'.format(name),
                                 np.array([value]*meta_len))


def adjust_ts_parameter(parameter, data_adafs):
    old_value_names = parameter.value_names

    if data_adafs.is_valid():
        signals = set(old_value_names)
        for data_adaf in data_adafs:
            signals.update(data_adaf.ts.keys())
        signals = sorted(signals)
    else:
        signals = old_value_names

    parameter.list = signals
    parameter.value_names = old_value_names


def colorbar(figure, artist, label):
    cbar = figure.colorbar(artist)
    cbar.get_mpl_artist().set_label(label, fontsize=FONTSIZE)
    cbar.get_mpl_artist().ax.tick_params(
        axis='both', which='major', labelsize=FONTSIZE)


def set_tick_font(ax):
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(FONTSIZE)
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(FONTSIZE)


def draw_base_histogram(ax, signal, bins, bins_range, ax_range, logy,
                        signal_label, fault_limits):
    """
    Draw a simple histogram in the upper left subplot.

    Arguments:
    ax : SyAxes or matplotlib Axes
        SyAxes object to draw onto.
    x_range : tuple or None
        If None (default) autoscale the histogram to match the data. If
        tuple used to specify the range (min, max).
    logy : bool
        If True the y axis will be logarithmic. Defaults to False, meaning
        linear y axis.
    """
    if len(signal):
        ax.hist(signal, bins=bins, range=bins_range, color='steelblue',
                log=logy)
    ax.set_xlim(ax_range)
    for fl in fault_limits:
        ax.axvline(fl, color='#008000', linewidth=2)

    ax.set_title("Histogram", fontsize=FONTSIZE)
    ax.set_xlabel(signal_label, fontsize=FONTSIZE)
    ax.set_ylabel("Samples per x-interval", fontsize=FONTSIZE)
    set_tick_font(ax)


def draw_pdf(ax, signal, bins, dist, x_range, percentiles, logy):
    """
    Draw pdf normalized to have the same area as the histogram.
    Also draws percentiles.
    """
    # TODO: This should probably account for nan values.
    histogram_area = len(signal) * (x_range[1] - x_range[0])/bins
    x = np.linspace(x_range[0], x_range[1], 10000)
    pdf = dist.pdf(x)*histogram_area

    # For logarithmic y axis, remove data points close to 0 since they
    # would ruin the scale.
    if logy:
        mask = pdf >= 0.1
        pdf = pdf[mask]
        x = x[mask]

    # Plot pdf and percentiles.
    ax.plot(x, pdf, label='pdf', color='#800000')
    for percentile in percentiles:
        ax.axvline(dist.ppf(percentile/100.), color='#000080',
                   linestyle='--')


def draw_prob_plot(ax, signal, dist, x_range, dist_name, p, signal_label):
    """
    Draw a probability plot that shows good a distribution fits the data.
    """
    if len(signal):
        ((osm, osr), (slope, intercept, _)) = probplot(signal, dist=dist)
        x = np.array([osr[0], osr[-1]])
        y = (x - intercept) / float(slope)
        ax.plot(x, y, color='#800000', linestyle='--')
        ax.plot(osr, osm, marker='o', markerfacecolor='steelblue',
                linestyle='None')
        ax.set_ylim(grow_range((min(osm[0], y[0]),
                                max(osm[-1], y[-1])), 1.2))
    ax.set_xlim(x_range)

    ax.set_title("Model fit - {} distribution (p-value = {:.3f})".format(dist_name, p), fontsize=FONTSIZE)
    ax.set_xlabel(signal_label, fontsize=FONTSIZE)
    ax.set_ylabel("Distribution quantiles", fontsize=FONTSIZE)
    set_tick_font(ax)


def draw_alpha_beta_plot(ax, dist, fault_limits):
    """
    Draw plot that shows the alpha/beta risk as a function of fault limit
    values.
    """
    # Make sure that the x scale for the alfa beta plot contains all fault
    # limits and an arbitrary percentile which shows that the cdf is
    # changing.
    x_points = fault_limits[:]
    if any(np.array(fault_limits) < dist.ppf(0.5)):
        x_points.append(dist.ppf(0.1))
    if any(np.array(fault_limits) > dist.ppf(0.5)):
        x_points.append(dist.ppf(0.9))
    x_points.sort()
    ax_range = grow_range((x_points[0], x_points[-1]), 1.1)
    # ax.set_xlim(ax_range)

    # Draw cdf if any fault limits are lower than the distribution
    # mean.
    if any(np.array(fault_limits) < dist.ppf(0.5)):
        x = np.linspace(
            ax_range[0], min(ax_range[1], dist.ppf(0.2)), 1000)
        ax.plot(x, dist.cdf(x), label='pdf', color='#800000')
    # Draw survival function (1 - cdf) if any fault limits are higher
    # than the distribution mean.
    if any(np.array(fault_limits) > dist.ppf(0.5)):
        x = np.linspace(
            max(ax_range[0], dist.ppf(1 - 0.2)), ax_range[1], 1000)
        ax.plot(x, dist.sf(x), label='pdf', color='#800000')

    # Draw fault limits
    for fl in fault_limits:
        ax.axvline(fl, color='#008000', linewidth=2)

    ax.set_title("Alpha-FL chart", fontsize=FONTSIZE)
    ax.set_xlabel("Limit value", fontsize=FONTSIZE)
    ax.set_ylabel("Alpha-risk", fontsize=FONTSIZE)
    set_tick_font(ax)


def find_dist_fit(signal, chosen_dist):
    """
    Try to find the distribution that fits the data best.

    Arguments:
    signal : numpy array
        One-dimensional array of measured values.
    chosen_dist : str or unicode
        Either 'Auto' or the name of a continuous distribution.
    """
    if chosen_dist == 'Auto':
        distributions = []
        for conf_name, scipy_name in DISTRIBUTIONS.iteritems():
            # try:
            dist, p, D = single_dist_fit(signal, scipy_name)
            # except:
            #     continue
            distributions.append((dist, conf_name, p, abs(D)))
        distributions = sorted(distributions,
                               key=operator.itemgetter(3))

        # p-value for the best-fitting distribution
        best_p = distributions[0][2]
        if best_p > 1 - ALPHA_LIMIT:
            # Found a distribution which could not be rejected! Return only
            # the best-fitting distribution. Skip the D value in the
            # returned tuple.
            return [distributions[0][:3]]
        else:
            # No good fit found. Return the four best fitting
            # distributions. Skip the p values in the returned tuples.
            return [d[:3] for d in distributions[:4]]
    else:
        # Specific distribution chosen in the configuration.
        dist_name = chosen_dist
        scipy_name = DISTRIBUTIONS[dist_name]
        dist, p, _ = single_dist_fit(signal, scipy_name)
        return [(dist, dist_name, p)]


def single_dist_fit(signal, dist_name):
    """
    Try to fit a signal against a single type of distribution.

    Arguments:
    signal : numpy array
        One-dimensional array of measured values.
    dist_name : str or unicode
        The name of a scipy distribution.
    """
    dist_class = getattr(scipy.stats, dist_name)
    with warnings.catch_warnings():
        # Suppress any warnings during fitting.
        warnings.simplefilter('ignore')
        dist = dist_class(*dist_class.fit(signal))

    # kstest is sensitive to zero-length data
    if signal.size:
        D, p = scipy.stats.kstest(signal, dist.cdf)
    else:
        # Infinitly bad fit. Hypothesis will always be rejected.
        D, p = (np.inf, 0)
    return dist, p, abs(D)


def distribution_plot_subsets(subsets, out_dir):
    data_adafs = subsets
    x_min = -1.0
    x_max = 3.0
    bins = 120
    dist_fit = 'Auto'
    logy = False
    signal_name = "OxiCat_facHCCnvRat"
    signal_label = get_label_adafs(data_adafs, signal_name)

    # The entire signal is needed for distribution fitting so simply
    # extract it all here:
    total_length = 0
    for data_adaf in data_adafs:
        total_length += data_adaf.ts[signal_name].basis().size()
    signal = np.zeros(total_length, dtype=float)
    i = 0
    for data_adaf in data_adafs:
        time_series = data_adaf.ts[signal_name]
        length = time_series.basis().size()
        signal[i:i+length] = time_series.y
        i += length

    x_range = (x_min, x_max)
    fault_limits = [
        float(fl.strip())
        for fl in ["0.4"]
        if fl.strip()]
    percentiles = [
        float(p.strip())
        for p in [""]
        if p.strip()]

    ax11 = ax12 = ax21 = ax22 = None
    good_dist = None

    if dist_fit == 'None':
        # Set up one subplot.
        ax11 = figure.subplots(1, 1)[0][0]
        draw_base_histogram(ax11, signal, bins, x_range, x_range,
                            logy, signal_label, fault_limits)
    else:
        # Returns one distribution on success or four on failure.
        distributions = find_dist_fit(signal, dist_fit)

        # For each returned distribution, set up two or four subplots
        # depending on whether there are any fault limits.
        if len(distributions) == 1:
            good_dist = distributions[0]
            if fault_limits:
                f, ((ax11, ax21),
                 (ax12, ax22)) = figure.subplots(2, 2)
                f.subplots_adjust(wspace=0.2, hspace=0.5)
                f.set_size_inches(25, 17)
                ax11_list = [ax11]
                ax21_list = [ax21]
                ax12_list = [ax12]
                ax22_list = [ax22]
            else:
                f, ((ax11,),
                 (ax12,)) = figure.subplots(2, 1)
                f.subplots_adjust(wspace=0.2, hspace=0.5)
                f.set_size_inches(25, 17)
                ax11_list = [ax11]
                ax21_list = [None]
                ax12_list = [ax12]
                ax22_list = [None]
        elif len(distributions) == 4:
            if fault_limits:
                f, ((ax111, ax211, ax112, ax212),
                 (ax121, ax221, ax122, ax222),
                 (ax113, ax213, ax114, ax214),
                 (ax123, ax223, ax124, ax224)) = figure.subplots(4, 4)
                f.subplots_adjust(wspace=0.2, hspace=0.5)
                f.set_size_inches(25, 17)
                ax11_list = [ax111, ax112, ax113, ax114]
                ax21_list = [ax211, ax212, ax213, ax214]
                ax12_list = [ax121, ax122, ax123, ax124]
                ax22_list = [ax221, ax222, ax223, ax224]
            else:
                f, ((ax111, ax112),
                 (ax121, ax122),
                 (ax113, ax114),
                 (ax123, ax124)) = figure.subplots(4, 2)
                f.subplots_adjust(wspace=0.2, hspace=0.5)
                f.set_size_inches(25, 17)
                ax11_list = [ax111, ax112, ax113, ax114]
                ax21_list = [None,  None,  None,  None]
                ax12_list = [ax121, ax122, ax123, ax124]
                ax22_list = [None,  None,  None,  None]
        else:
            # self.find_dist_fit returned something other than one or four
            # distributions. Panic mode.
            raise ValueError(
                'Incorrect return value from self.find_dist_fit()')

        # Draw all subplots for each distribution.
        for ax11, ax12, ax21, ax22, (dist, dist_name, p) in zip(
                ax11_list, ax12_list, ax21_list, ax22_list, distributions):

            # Draw left-most subplots
            if signal.size:
                ax11_x_range = grow_range(
                    (signal.min(), signal.max()), 1.6)
            else:
                ax11_x_range = (0, 1)
            draw_base_histogram(
                ax11, signal, bins, x_range, ax11_x_range, logy,
                signal_label, fault_limits)
            draw_pdf(
                ax11, signal, bins, dist, ax11_x_range, percentiles, logy)
            draw_prob_plot(
                ax12, signal, dist, ax11_x_range, dist_name, p,
                signal_label)

            # Rightmost subplots only exist in some circumstances:
            if ax21 is not None:
                draw_base_histogram(
                    ax21, signal, bins, x_range, x_range, logy,
                    signal_label, fault_limits)
                draw_pdf(
                    ax21, signal, bins, dist, x_range, percentiles, logy)
            if ax22 is not None:
                draw_alpha_beta_plot(ax22, dist, fault_limits)

        # Set up the meta data to be shown on the side of the plot.
        texts = [outside_range_text(x=(signal, x_range))]

        # Descriptive statistics
        if signal.size:
            if good_dist is not None:
                dist = good_dist[0]
                desc_stat_text = (
                    "<b>Descriptive statistics:</b><br>\n"
                    "<b>Mean:</b> {mean:.3f} (dist)<br>\n"
                    "<b>Std:</b> {std:.3f} (dist)<br>\n"
                    "<b>Min:</b> {min:.3f}<br>\n"
                    "<b>Max:</b> {max:.3f}<br>\n").format(
                    mean=dist.mean(), min=signal.min(), max=signal.max(),
                    std=dist.std())
                texts.append(desc_stat_text)
            else:
                desc_stat_text = (
                    "<b>Descriptive statistics:</b><br>\n"
                    "<b>Mean:</b> {:.3f}<br>\n"
                    "<b>Std:</b> {:.3f}<br>\n"
                    "<b>Min:</b> {:.3f}<br>\n"
                    "<b>Max:</b> {:.3f}<br>\n").format(
                    signal.mean(), signal.min(), signal.max(),
                    signal.std())
                texts.append(desc_stat_text)

        # Percentiles
        if good_dist is not None and percentiles:
            dist = good_dist[0]
            percentiles_texts = "<br>\n".join([
                                                  "<b>{}:</b> {:.4f}".format(
                                                      percentile, dist.ppf(percentile/100.))
                                                  for percentile in percentiles])
            percentiles_text = "<b>Percentiles:</b><br>{}<br>\n".format(
                percentiles_texts)
            texts.append(percentiles_text)

        # Fault limits
        if fault_limits:
            fault_limits_lines = []
            for fl in fault_limits:
                # TODO: distributions isn't always initialized here
                for dist, dist_name, p in distributions:
                    line = "<b>{}:</b> {:.4f} / {:.4f} ({})".format(
                        fl, dist.cdf(fl), dist.sf(fl), dist_name)
                    fault_limits_lines.append(line)
            fault_limits_text = "<b>Fault limits:</b><br>{}<br>\n".format(
                "<br>\n".join(fault_limits_lines))
            texts.append(fault_limits_text)

        # Warning if no distribution fits
        if good_dist is None:
            texts.append("<i><b>Warning:</b> All tested distributions were "
                         "rejected at &alpha; &lt; {}. The four best fitting "
                         "distributions are shown instead.</i>".format(
                ALPHA_LIMIT))

        text = "<br>\n".join(texts)
        missing_text = missing_signals_text(data_adafs, (signal_name,))
        alias_text = aliases_text(data_adafs, (signal_name,))

        for i, data_adaf in enumerate(data_adafs):
            add_dataset_meta(data_adaf, 'missing_text', missing_text)
            add_dataset_meta(data_adaf, 'alias_text', alias_text)
            add_dataset_meta(data_adaf, 'extra_text', text)

        # save plots
        plots_name = "B_KatDiagnos_Dist fit_input.png"
        file_path = os.path.join(out_dir, plots_name)
        figure.savefig(file_path, dpi=100)

