# Copyright (c) 2016, System Engineering Software Society
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the System Engineering Software Society nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.
# IN NO EVENT SHALL SYSTEM ENGINEERING SOFTWARE SOCIETY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)
import ast
import os
import six
import numpy as np

from collections import defaultdict
from datetime import datetime

import matplotlib as mpl
from matplotlib import markers as mpl_markers
from matplotlib import lines as mpl_lines
from matplotlib.transforms import IdentityTransform

from sylib.util import base_eval
from sylib.figure import colors, widgets
from sympathy.platform.exceptions import sywarn
from sympathy.typeutils import figure
from sympathy.typeutils.figure import SyAxes


_color_cycle = None


def color_cycle():
    global _color_cycle
    if _color_cycle is None:
        mpl_version = [int(i) for i in mpl.__version__.split('.')]
        if mpl_version < [1, 5, 0]:
            _color_cycle = mpl.rcParams['axes.color_cycle']
        else:
            _color_cycle = [i['color']
                            for i in mpl.rcParams['axes.prop_cycle']]
    return _color_cycle


MARKERS = mpl_markers.MarkerStyle.markers
LINESTYLES = mpl_lines.lineStyles

DRAWSTYLES = ['default', 'steps', 'steps-pre',
              'steps-mid', 'steps-post']

LEGEND_LOC = {
    'best': 0,  # (only implemented for axes legends)
    'upper right': 1,
    'upper left': 2,
    'lower left': 3,
    'lower right': 4,
    'right': 5,
    'center left': 6,
    'center right': 7,
    'lower center': 8,
    'upper center': 9,
    'center': 10
}

FONTSIZE = ['xx-small', 'x-small', 'small', 'medium',
            'large', 'x-large', 'xx-large']

# the allowed parameters are listed in dictionaries where the value
# contains: (type, default_value, choices or None, required, widget)

COLOR_T = ('colortype', 'g', colors.COLORS, False, widgets.SyMPLColorPicker)
LINESTYLE_T = ('linestyletype', '-', LINESTYLES.keys(), False,
               widgets.SyMPLComboBox)
LINEWIDTH_T = (float, 1., (0., None, 1.), False, widgets.SyMPLDoubleSpinBox)

LINE = {
    'xdata': (unicode, '', None, True, widgets.SyMPLTextEdit),
    'ydata': (unicode, '', None, True, widgets.SyMPLTextEdit),
    'axes': ('axestype', '_default_', None, True, widgets.SyMPLTextEdit),
    'label': (unicode, '', None, False, widgets.SyMPLTextEdit),
    'marker': (str, 'o', MARKERS, False, widgets.SyMPLComboBox),
    'markersize': (float, 5, (0., None, 1.), False,
                   widgets.SyMPLDoubleSpinBox),
    'markeredgecolor': COLOR_T,
    'markeredgewidth': (float, 0.1, (0., None, 0.01), False,
                        widgets.SyMPLDoubleSpinBox),
    'markerfacecolor': COLOR_T,
    'linestyle': LINESTYLE_T,
    'linewidth': LINEWIDTH_T,
    'color': COLOR_T,
    'alpha': (float, 1., (0., 1., 0.05), False, widgets.SyMPLDoubleSpinBox),
    'zorder': (float, 1, (1, None, 1), False, widgets.SyMPLSpinBox),
    'drawstyle': ('drawstyletype', 'default', DRAWSTYLES, False,
                  widgets.SyMPLComboBox),
    # 'xdate': (bool, False, None, False),
    # 'ydate': (bool, False, None, False),
}

GRID = {
    'color': COLOR_T,
    'linestyle': LINESTYLE_T,
    'linewidth': LINEWIDTH_T,
    'which': (str, 'major', ['major', 'minor', 'both'], False,
              widgets.SyMPLComboBox),
    'axis': (str, 'both', ['x', 'y', 'both'], False, widgets.SyMPLComboBox)
}

LEGEND = {
    'loc': ('locationtype', 'upper right', LEGEND_LOC.keys(), False,
            widgets.SyMPLComboBox),
    'ncol': (int, 1, (1, None, 1), False, widgets.SyMPLSpinBox),
    'fontsize': ('fontsizetype', None, FONTSIZE, False, None),
    'frameon': (bool, True, None, False, widgets.SyMPLCheckBox),
    'title': (unicode, '', None, False, widgets.SyMPLTextEdit),
    # 'markerfirst': (bool, True, None, False),
    # 'numpoints': (int, None, None, False),
    # 'scatterpoints': (int, None, None, False),
    # 'fancybox': (bool, False, None, False),
    # 'shadow': (bool, False, None, False),
    # 'framealpha': (float, 1., None, False),
    # 'borderpad': (float, None, None, False),
    # 'labelspacing': (float, None, None, False),
    # 'handlelength': (float, None, None, False),
    # 'handletextpad': (float, None, None, False),
    # 'borderaxespad': (float, None, None, False),
    # 'columnspacing': (float, None, None, False),
}

AXES = {
    'xaxis': ('axestype', 'x1', ['x', 'x1', 'x2'], True,
              widgets.SyMPLComboBox),
    'yaxis': ('axestype', 'y1', ['y', 'y1', 'y2'], True,
              widgets.SyMPLComboBox),
    'title': (unicode, '', None, False, widgets.SyMPLTextEdit),
    'xlabel': (unicode, '', None, False, widgets.SyMPLTextEdit),
    'ylabel': (unicode, '', None, False, widgets.SyMPLTextEdit),
    'xlim': (ast.literal_eval, (None, None), None, False, None),
    'ylim': (ast.literal_eval, (None, None), None, False, None),
    'xscale': (str, 'linear', ['linear', 'log'], False, widgets.SyMPLComboBox),
    'yscale': (str, 'linear', ['linear', 'log'], False, widgets.SyMPLComboBox),
    'aspect': (str, 'auto', ['auto', 'equal', '1.'], False, None),
    'legend': LEGEND,
    'grid': GRID,
}

FIGURE = {
    'title': (unicode, '', None, False, None),
}

PARAMETER_OPTIONS = {
    'AXES': {
        'icon': 'view-plot-axes-symbolic.svg',
        'parameter': AXES,
        'default_parameter': ('xaxis', 'yaxis')},
    'GRID': {
        'icon': 'view-plot-grid-symbolic.svg',
        'parameter': GRID,
        'default_parameter': ('axis', 'which')},
    'LEGEND': {
        'icon': 'view-plot-legend-symbolic.svg',
        'parameter': LEGEND,
        'default_parameter': ('loc',)},
    'LINE': {
        'icon': 'view-plot-line-symbolic.svg',
        'parameter': LINE,
        'default_parameter': ('xdata', 'ydata', 'color', 'label')},
    'SCATTER': {
        'icon': 'view-plot-scatter-symbolic.svg',
        'parameter': LINE,
        'default_parameter': ('xdata', 'ydata', 'color', 'marker', 'label')},
}


def get_full_icon_name(name):
    path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(path, 'svg_icons', name)


def verify_options(value, options):
    """Check if value is within the options."""
    if value in options:
        return value
    return None


def gen_config_by_prefix(config, prefix):
    """
    Return a generator returning (key, value) where the key
    start with the given prefix.
    """
    return ((k.lower(), v) for k, v in config
            if k.lower().startswith(prefix.lower()))


def parse_type(value, type_):
    t, default, options, required = type_[:4]
    if t == 'colortype':
        return colors.parse_color_to_mpl_color(six.text_type(value))
    elif t in ['linestyletype', 'locationtype',
               'drawstyletype', 'fontsizetype']:
        return verify_options(six.text_type(value), options)
    elif t == 'axestype':
        if value in ['x', 'y']:
            return '{}1'.format(value)
        elif value in ['x1', 'x2', 'y1', 'y2']:
            return value
        return None
    else:
        return t(value)


def fill_in_global_parameters(global_params, local_params):
    """
    Update the local parameters with existing global parameters
    without overriding existing ones.
    """
    for key, value in six.iteritems(global_params):
        for local in local_params.values():
            if key not in local:
                local[key] = value


def parse_config_lines(config, axes=None):
    """Parse the line parameters."""
    if axes is None:
        axes = {}
    global_line_params = {}
    lines = defaultdict(dict)
    for key, value in config:
        key_splitted = key.lower().split('.')
        if len(key_splitted) == 3:
            identifier, param = key_splitted[1:]
        elif len(key_splitted) == 2:
            identifier, param = None, key_splitted[1]
        type_ = LINE.get(param, None)
        # continue if type is unknown
        if type_ is None:
            continue
        if param == 'axes':
            if value in axes.keys():
                parsed_value = value
            else:
                # default case
                continue
        else:
            parsed_value = parse_type(value, type_)
        # jump parameter if it's value is unknown
        if parsed_value is None:
            continue
        if identifier is None:
            global_line_params[param] = parsed_value
        else:
            lines[identifier][param] = parsed_value

    # get required parameters
    required_parameters = [k for k, v in six.iteritems(LINE) if v[3]]
    # update line parameters from global parameters if missing and
    # defined in global line parameter
    for line_id, params in six.iteritems(lines):
        is_valid = True
        for required_param in required_parameters:
            if required_param in params.keys():
                continue
            if (required_param not in params.keys() and
                    required_param in global_line_params.keys()):
                value = global_line_params[required_param]
            else:
                value = LINE[required_param][1]
                if required_param in ['xdata', 'ydata']:
                    is_valid = False
            lines[line_id][required_param] = value
        lines[line_id]['valid'] = is_valid

    fill_in_global_parameters(global_line_params, lines)
    return lines, global_line_params


def parse_sub_config(param, value, config_dict):
    type_ = config_dict.get(param, None)
    if type_ is None:
        return None, None
    parsed_value = parse_type(value, type_)
    return param, parsed_value


def parse_config_axes(config):
    """Parse the axes parameters."""
    global_axes = {}
    axes = defaultdict(dict)
    for key, value in config:
        key_splitted = key.lower().split('.')
        sub_param = []
        if len(key_splitted) == 3 and key_splitted[1] not in AXES.keys():
            identifier, param = key_splitted[1:]
        elif len(key_splitted) == 3 and key_splitted[1] in AXES.keys():
            identifier = None
            param = key_splitted[1]
            sub_param = key_splitted[2:]
        elif len(key_splitted) == 2:
            identifier, param = None, key_splitted[1]
        else:
            identifier = key_splitted[1]
            param = key_splitted[2]
            sub_param = key_splitted[3:]
        type_ = AXES.get(param, None)
        if type_ is None:
            continue
        if param in ['grid', 'legend']:
            if (identifier is None and
                    param not in global_axes.keys()):
                global_axes[param] = {'show': True}
            elif (identifier is not None and
                    param not in axes[identifier].keys()):
                axes[identifier][param] = {'show': True}
            if len(sub_param):
                sconfig = GRID if param == 'grid' else LEGEND
                p, v = parse_sub_config(sub_param[0], value, sconfig)
                if p is not None and v is not None:
                    if identifier is None:
                        global_axes[param][p] = v
                    else:
                        axes[identifier][param][p] = v
        else:
            parsed_value = parse_type(value, type_)
            if identifier is None:
                global_axes[param] = parsed_value
            else:
                axes[identifier][param] = parsed_value

    # get all defined x and y axes
    defined_yaxis = set(
        [a['yaxis'] for a in axes.values() if 'yaxis' in a])

    # get required parameters
    required_parameters = [k for k, v in six.iteritems(AXES) if
                           not isinstance(v, dict) and v[3]]
    # update line parameters from global parameters if missing and
    # defined in global line parameter
    for axis_id, params in six.iteritems(axes):
        for required_param in required_parameters:
            if required_param in params.keys():
                continue
            if required_param in global_axes.keys():
                value = global_axes[required_param]
            else:
                value = AXES[required_param][1]
                if required_param == 'yaxis':
                    if value in defined_yaxis:
                        value = 'y2'
            axes[axis_id][required_param] = value
    fill_in_global_parameters(global_axes, axes)
    return axes


def parse_config_figure(config):
    """Parse the figure parameters."""
    figure = {}
    for key, value in config:
        param = key.lower().lstrip('figure.')
        type_ = FIGURE.get(param, None)
        if type_ is None:
            continue
        parsed_value = parse_type(value, type_)
        figure[param] = parsed_value
    return figure


def parse_configuration(config):
    """
    Parse a configuration table containing with
    a parameter and value column.
    """
    axes = parse_config_axes(
        gen_config_by_prefix(config, 'axes.'))

    lines, global_line_params = parse_config_lines(
        gen_config_by_prefix(config, 'line.'), axes)

    figure = parse_config_figure(
        gen_config_by_prefix(config, 'figure.'))

    return {'figure': figure,
            'axes': axes,
            'line': lines}


def reconstruct_twin_axes(start_axes, axes):
    """Reconstruct the relationship between overlaying twin axes."""
    sibling_axes = {start_axes: (1, 1)}
    shared_ax = {ax: (ax._sharex, ax._sharey) for ax in axes}

    for ax in axes:
        if ax in sibling_axes.keys():
            continue
        has_shared = shared_ax.get(ax)
        if has_shared is not None and has_shared != (None, None):
            sharex, sharey = has_shared
            if sharex is not None and sharey is None:
                x_parent_pos = sibling_axes.get(sharex)
                pos = x_parent_pos[0], x_parent_pos[1] + 1
            elif sharex is None and sharey is not None:
                y_parent_pos = sibling_axes.get(sharey)
                pos = y_parent_pos[0] + 1, y_parent_pos[1]
            else:
                raise ValueError('Unknown axes configuration')
            sibling_axes[ax] = pos
    return sibling_axes


def get_twin_axes(axes_dict, xaxis, yaxis):
    """
    Return the twin axes given by `xaxis`, `yaxis`.

    Parameters
    ----------
    axes_dict : dict
        A dictionary containing at least the default axes
        with xaxis='x1' and yaxis='y1'.
    xaxis : unicode
        The name of the xaxis. Supported values are 'x1' and 'x2'.
    yaxis : unicode
        The name of the yaxis. Supported values are 'y1' and 'y2'.

    Returns
    -------
    ax : matplotlib.axes._subplots.AxesSubplot
    """
    ax = axes_dict.get((xaxis, yaxis), None)
    default_axes = axes_dict[('x1', 'y1')]
    if isinstance(default_axes, figure.SyAxes):
        default_axes = default_axes.get_mpl_axes()
    if ax is None:
        if xaxis == 'x1' and yaxis == 'y2':
            ax = default_axes.twinx()
        elif xaxis == 'x2' and yaxis == 'y1':
            ax = default_axes.twiny()
        elif xaxis == 'x2' and yaxis == 'y2':
            x1y2axes = get_twin_axes(axes_dict, 'x1', 'y2')
            ax = x1y2axes.twiny()
        else:
            raise ValueError('The axes type "{}, {}" is not '
                             'supported.'.format(xaxis, yaxis))
        axes_dict[(xaxis, yaxis)] = ax
    return ax


def classify_axes(axes):
    """
    Classify the axes in the scheme ('x1', 'y1').

    The axes get stored with a (x,y) key in a dictionary
    depending on their shared x or y axes. The first axes
    will always be set as ('x1', 'y1').
    """
    if len(axes):
        classed_axes = reconstruct_twin_axes(axes[0], axes)
        return {('x{}'.format(v[0]), 'y{}'.format(v[1])): k
                for k, v in six.iteritems(classed_axes)}
    return {}


def move_lines_to(source, target, existing_colors, auto_recolor=True):
    """
    Move a line artist from a source to a target axes.

    Remove the line artist from the source mpl.axes and
    add it to the target axes.
    """
    if isinstance(target, figure.SyAxes):
        target = target.get_mpl_axes()
    if isinstance(source, figure.SyAxes):
        source = source.get_mpl_axes()

    for i, line in enumerate(source.lines):
        # create new Line2D object
        x, y = line.get_data()
        new_line = mpl_lines.Line2D(x, y)
        new_line.update_from(line)
        # extend the label if same already exists
        label = line.get_label()
        used_labels = [l.get_label() for l in target.lines]
        if label in used_labels:
            i = 2
            while '{}_{}'.format(label, i) in used_labels:
                i += 1
            new_line.set_label('{}_{}'.format(label, i))
        # this is a bit of a hack to remove axes specific properties
        new_line.set_transform(IdentityTransform())
        new_line._transformed_path = None
        new_line._transformSet = False
        new_line._xy = None
        new_line._x = None
        new_line._y = None

        # auto assign new color from mpl color_cycle
        if auto_recolor:
            unique_colors = np.unique(existing_colors)
            # workaround for numpy version < 1.9
            # we could use return_count in np.unique in the future
            color_count = [(np.array(existing_colors) == item).sum()
                           for item in unique_colors]
            unique_colors = list(unique_colors)  # otherwise FutureWarning
            hex_color_cycle = [colors.color2hex(c) for c in color_cycle()]
            unused_colors = [c for c in hex_color_cycle if
                             c not in unique_colors]
            current_color = colors.color2hex(new_line.get_color())
            if current_color in unique_colors:
                # assign a new color
                if len(unused_colors):
                    new_color = unused_colors[0]
                else:
                    least_occuring_color = unique_colors[
                        np.argsort(color_count)[0]]
                    if len(least_occuring_color):
                        new_color = least_occuring_color
                    else:
                        new_color = color_cycle[0]()
            else:
                new_color = current_color
            new_line.set_color(new_color)
        target.add_line(new_line)
        existing_colors.append(new_line.get_color())


parameter_list_to_copy = [
    # 'title',  # doesn't work for whichever reason
    'xscale',
    'yscale',
    'xlabel',
    'ylabel',
    'xlim',
    'ylim'
]


def copy_axes_parameter(source, target):
    """
    Copy axes parameters from a source to a target axes.

    Copy the parameters defined in the ``parameter_list_to_copy``
    from the ``source`` mpl axes to the ``target`` mpl axes.
    """
    if isinstance(target, figure.SyAxes):
        target = target.get_mpl_axes()
    if isinstance(source, figure.SyAxes):
        source = source.get_mpl_axes()
    for attr in parameter_list_to_copy:
        value = getattr(source, 'get_{}'.format(attr))()
        setter = getattr(target, 'set_{}'.format(attr))
        setter(value)

    # has to be done manually
    target.set_title(source.get_title())

    for saxis, taxis in zip([source.xaxis, source.yaxis],
                            [target.xaxis, target.yaxis]):
        grid_params = {}
        major_grid_on = saxis._major_tick_kw.get('gridOn', False)
        minor_grid_on = saxis._minor_tick_kw.get('gridOn', False)

        if major_grid_on and minor_grid_on:
            grid_params['which'] = 'both'
        elif major_grid_on:
            grid_params['which'] = 'major'
        elif minor_grid_on:
            grid_params['which'] = 'minor'

        line_properties = saxis.get_gridlines()[0].properties()
        for prop in ['color', 'linewidth', 'linestyle']:
            value = line_properties.get(prop, None)
            grid_params[prop] = value

        grid_params['zorder'] = 1
        if saxis._gridOnMajor or saxis._gridOnMinor:
            taxis.grid(**grid_params)


def compress_axes(axes_of_figures, default_output_axes,
                  legends_join=False, legend_location='best',
                  copy_properties_from=0, auto_recolor=True,
                  auto_rescale=True):
    """
    Compress the lines and parameters from different axes into one.

    Parameters
    ----------
    axes_of_figures : array-like
        List of mpl axes
    default_output_axes : axes
        Mpl axes
    legends_join : bool
        Set true if legends for different twin axes should be joined
        into one. Default False.
    legend_location : unicode or str or int
        Location of the joined legend in mpl strings or int.
        Default 'best'.
    copy_properties_from : int
        The set of twinaxes from which the axes properties should be
        copied to the resulting axes. Default 0.
    auto_recolor : bool
        Set True if artists should be automatically recolored [Default: True].
    auto_rescale : bool
        Automatically rescale all axes to fit the visible data.
    """
    default_axes = default_output_axes

    output_axes_dict = {('x1', 'y1'): default_axes}
    if copy_properties_from >= len(axes_of_figures):
        copy_properties_from = 0
        sywarn('The figure specified as source for the new axes '
               'parameter does not exist. The first figure will '
               'be used!')

    legend_in_subaxes = {}

    last_axes_drawn_to = None
    existing_colors = []

    for idx, axes in enumerate(axes_of_figures):
        axes_dict = classify_axes(axes)

        for ax_id, source_ax in six.iteritems(axes_dict):
            # save old ids, required to find last added axes
            old_axes_ids = output_axes_dict.keys()
            target_ax = get_twin_axes(output_axes_dict,
                                      ax_id[0], ax_id[1])
            move_lines_to(source_ax, target_ax, existing_colors,
                          auto_recolor=auto_recolor)

            # save the last added axes
            if ax_id not in old_axes_ids:
                last_axes_drawn_to = target_ax

            if idx == copy_properties_from:
                copy_axes_parameter(source_ax, target_ax)

            # call _update_axisinfo to reformat date axis
            target_ax.xaxis._update_axisinfo()
            target_ax.yaxis._update_axisinfo()

            if auto_rescale:
                target_ax.relim()
                target_ax.autoscale()

            # save if source_ax had legend
            legend = source_ax.get_legend()
            if (legend is not None and (ax_id not in legend_in_subaxes or
                                        idx == copy_properties_from)):
                # collect legends parameters
                legend_props = {}
                for prop in LEGEND.keys():
                    value = None
                    if hasattr(legend, prop):
                        value = getattr(legend, prop)
                    elif hasattr(legend, '_{}'.format(prop)):
                        value = getattr(legend, '_{}'.format(prop))
                    elif hasattr(legend, 'get_{}'.format(prop)):
                        value = getattr(legend, 'get_{}'.format(prop))()
                    if value is not None:
                        legend_props[prop] = value
                legend_in_subaxes[ax_id] = legend_props

    lookup = {('x1', 'y1'): '$\downarrow\leftarrow$',
              ('x1', 'y2'): '$\downarrow\\rightarrow$',
              ('x2', 'y1'): '$\\uparrow\leftarrow$',
              ('x2', 'y2'): '$\\uparrow\\rightarrow$'}
    # draw legend for each axes
    legend_handles = []
    legend_labels = []

    multiple_axes = len(set(legend_in_subaxes.keys())) > 1

    for ax_id, props in six.iteritems(legend_in_subaxes):
        ax = output_axes_dict[ax_id]
        if not legends_join:
            title = props.pop('title', None)
            if title is not None and title.get_text() != 'None':
                props['title'] = title.get_text()
            ax.legend(**props)
        else:
            if isinstance(ax, figure.SyAxes):
                ax = ax.get_mpl_axes()
            handles, labels = ax.get_legend_handles_labels()
            legend_handles.extend(handles)

            if multiple_axes:
                labels = ['{} ({})'.format(l, lookup[ax_id]) for l in labels]
            legend_labels.extend(labels)
    if legends_join:
        # copy legend properties from the default axes
        parent_legend_props = legend_in_subaxes.get(('x1', 'y1'), {})
        parent_legend_props.pop('loc', None)
        parent_legend_props.pop('title', None)
        parent_legend_props['loc'] = legend_location
        if len(legend_labels) or len(legend_handles):
            # to place the legend on top of everything else, we
            # need to add it to the last axes we added to the plot
            if last_axes_drawn_to is not None:
                ax = last_axes_drawn_to
            else:
                ax = default_axes
            ax.legend(legend_handles, legend_labels, **parent_legend_props)


def parse_value(text, data_table):
    """
    Evaluate expression in a limited python environment.

    If evaluation fails, the input text will be returned as
    ``unicode``.

    Parameters
    ----------
    text : unicode or str
    data_table : sympathy.api.table.File

    Returns
    -------
    Returns the evaluated text.
    """
    try:
        parsed_value = base_eval(
            six.text_type(text), {'table': data_table})
    except (NameError, SyntaxError):
        parsed_value = six.text_type(text)
    return parsed_value


def parse_values_in_dict(d, data_table):
    """Parse the values in a dict with `parse_value`."""
    return {key: parse_value(value, data_table)
            for key, value in six.iteritems(d)}


class CreateFigure(object):
    """
    This :class:`CreateFigure` class is used to create a populate a
    ``matplotlib`` figure with data from `date_table` as defined in
    `parsed_param`.
    """
    def __init__(self, data_table, figure, parsed_param):

        self.data_table = data_table
        self.figure = figure
        self.parsed_param = parsed_param
        self.axes = {('x1', 'y1'): self.figure.first_subplot().get_mpl_axes()}
        self.axes_by_name = {'_default_': self.axes[('x1', 'y1')]}
        self.axes_legend = {}

    def create_figure(self):
        fig_param = self.parsed_param.get('figure', None)
        if fig_param:
            self.apply_figure_parameters(fig_param)
        ax_param = self.parsed_param.get('axes', None)
        if ax_param:
            self.apply_axes_parameters(ax_param)
        line_param = self.parsed_param.get('line', None)
        if line_param:
            self.add_lines(line_param)

        self.draw_legends()
        return self.figure

    def apply_axes_parameters(self, parameters):
        """Create all defined axes."""
        for axes_id, axes_params in six.iteritems(parameters):
            # save legend parameters for later handling
            axes_params = axes_params.copy()
            self.axes_legend[axes_id] = axes_params.pop('legend',
                                                        {'show': False})
            # add a grid if specified
            grid_params = axes_params.pop('grid', None)

            # evaluate parameters
            axes_params = parse_values_in_dict(axes_params, self.data_table)

            # create the defined axes
            xaxis = axes_params.pop('xaxis', 'x1')
            yaxis = axes_params.pop('yaxis', 'y1')
            ax = get_twin_axes(self.axes, xaxis, yaxis)
            self.axes_by_name[axes_id] = ax

            if grid_params is not None:
                self.apply_axes_grid_parameters(ax, grid_params)
            # set the remaining parameters
            if isinstance(ax, SyAxes):
                ax = ax.get_mpl_axes()
            ax.set(**axes_params)

    def add_lines(self, parameters):
        for id_, line in six.iteritems(parameters):
            line = parse_values_in_dict(line, self.data_table)

            if not line.pop('valid', False):
                continue

            xdata = line.pop('xdata')
            ydata = line.pop('ydata')

            axes_desc = line.pop('axes', '_default_')
            axes = self.axes_by_name.get(axes_desc)

            # get the column data if data is specified as string
            if (isinstance(xdata, unicode) and
                    xdata in self.data_table.column_names()):
                xdata = self.data_table.get_column_to_array(xdata)
            if (isinstance(ydata, unicode) and
                    ydata in self.data_table.column_names()):
                ydata = self.data_table.get_column_to_array(ydata)

            if (not isinstance(xdata, np.ndarray) or
                    not isinstance(ydata, np.ndarray)):
                sywarn('The data for line plot #{} is not accessible and '
                       'will not be plotted!'.format(id_))
                continue

            # cleanup parameters
            if 'linestyle' in line.keys() and line['linestyle'] is None:
                line['linestyle'] = 'none'

            xdate = xdata.dtype.kind == 'M'
            ydate = ydata.dtype.kind == 'M'
            if xdate or ydate:
                if xdate:
                    xdata = xdata.astype(datetime)
                if ydate:
                    ydata = ydata.astype(datetime)
                line['xdate'] = xdate
                line['ydate'] = ydate

                if 'linestyle' not in line.keys():
                    line['linestyle'] = '-'
                if 'marker' not in line.keys():
                    line['marker'] = ''

                axes.plot_date(xdata, ydata, **line)

                # FIXME: (Bene) max recursion error at pickling prevents:
                # if xdate:
                #     self.figure.get_mpl_figure().autofmt_xdate()
            else:
                # TODO: implement different plot types
                # (like plot, hist, scatter, bar, etc)
                axes.plot(xdata, ydata, **line)

    def draw_legends(self):
        for ax_id, params in six.iteritems(self.axes_legend):
            ax = self.axes_by_name[ax_id]
            self.apply_axes_legend_parameters(ax, params)

    def apply_figure_parameters(self, parameters):
        parameters = parse_values_in_dict(parameters, self.data_table)
        for param, value in six.iteritems(parameters):
            if param == 'title':
                self.figure.set_title(value)

    def apply_axes_grid_parameters(self, axes, params):
        parsed_params = parse_values_in_dict(params, self.data_table)
        if parsed_params.pop('show', False):
            axes.grid(**parsed_params)

    def apply_axes_legend_parameters(self, axes, params):
        parsed_params = parse_values_in_dict(params, self.data_table)
        if parsed_params.pop('show', False):
            axes.legend(**parsed_params)


if __name__ == '__main__':
    test_config = [['line.1.name', 'testline'],
                   # ['line.color', 'blue'],
                   ['line.xdata', 'col 1'],
                   ['line.ydata', 'y data col'],
                   ['line.1.ydata', 'col 2'],
                   ['line.1.axes', 'xy'],
                   ['line.2.ydata', 'col 3y'],
                   ['line.2.color', '123, 2'],
                   # ['line.22', ''],
                   ['line.xdata', 'col 3x'],
                   ['line.3.ydata', 'col 5x'],
                   ['figure.title', 'test title'],
                   ['axes.legend.loc', 'best'],
                   ['axes.legend.markerfirst', False],
                   ['axes.xy.grid.color', '12, 12']

                   # ['axes.xy.xaxis', 'x'],
                   # ['axes.xy.yaxis', 'y'],
                   # ['axes.xy.xlim', '0, 12'],
                   # ['axes.xy.grid', True],
                   # ['axes.xy.grid.color', '(1., 1., 1.)'],
                   # ['axes.xy.legend.fancybox', True],
                   # ['axes.xy.legend.title', 'legend title'],
                   # ['axes.xy.legend.loc', 'upper left'],
                   # ['axes.x1y2.xlim', '0, 12'],
                   # ['axes.grid.color', 'red'],
                   # ['axes.legend.peter', '']  # shouldn't show up
                   ]
    output = parse_configuration(test_config)
    #
    # for k, o in six.iteritems(output):
    #     print(k + ':')
    #     for id_, line in six.iteritems(o):
    #         print('\t', id_, line)
