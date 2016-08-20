# coding: utf8
# Copyright (c) 2013, System Engineering Software Society
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
"""
Interpolate timeseries timeseries to a single timebasis. The new timebasis can
either be an existing timebasis in the adaf-file or a timebasis with a timestep
defined by the user. The timeseries that will be interpolated are selected in a
list. The output file will contain a single system and raster with all the
chosen timeseries.
"""
import collections

import numpy as np
from scipy.interpolate import interp1d

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyDataError, SyConfigurationError, sywarn
from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui')


_METHODS = ['zero', 'nearest', 'linear', 'quadratic', 'cubic']


def resample_file_with_spec(parameter_root, spec, in_adaffile, out_adaffile,
                            progress):
    signals_col = parameter_root['signals_colname'].selected
    dt_col = parameter_root['dt_colname'].selected
    tb_col = parameter_root['tb_colname'].selected
    signals = spec.get_column_to_array(signals_col)
    if dt_col is not None:
        dts = spec.get_column_to_array(dt_col)
    else:
        dts = np.zeros(signals.shape, dtype=float) * np.nan
    if tb_col is not None:
        to_tbs = spec.get_column_to_array(tb_col)
    else:
        to_tbs = np.zeros(signals.shape, dtype=unicode)

    dt_to_signals = collections.defaultdict(list)
    tbname_to_signals = collections.defaultdict(list)
    for i, (dt, to_tb, signal) in enumerate(zip(dts, to_tbs, signals)):
        if not np.isnan(dt):
            dt_to_signals[dt].append(signal)
        elif to_tb:
            tbname_to_signals[to_tb].append(signal)
        else:
            raise SyDataError("Row {} in specification table specifies "
                              "neither dt nor a target time basis.".format(i))

    new_timebases = []
    for dt, dt_signals in dt_to_signals.items():
        # Create output system/raster
        new_timebasis, unit = get_new_timebasis(in_adaffile, dt, dt_signals)
        system_name = 'Resampled system'
        raster_name = 'Resampled raster {:.2}'.format(dt)
        new_timebases.append(
            (system_name, raster_name, new_timebasis, unit, dt_signals))
    for tbname, tb_signals in tbname_to_signals.items():
        raster_dict = get_raster_dict(in_adaffile)
        try:
            old_system_name, old_raster_name = raster_dict[tbname]
        except KeyError:
            sywarn('No such system/raster: {}'.format(tbname))
            continue
        old_tb_column = (
            in_adaffile.sys[old_system_name][old_raster_name].basis_column())

        system_name = 'Resampled system'
        raster_name = old_raster_name
        new_timebasis = old_tb_column.value()
        unit = old_tb_column.attr['unit'] or 's'
        new_timebases.append(
            (system_name, raster_name, new_timebasis, unit, tb_signals))

    for i, (system_name, raster_name, new_timebasis, unit,
            signals) in enumerate(new_timebases):
        if not unit:
            unit = 's'
        if system_name not in out_adaffile.sys.keys():
            new_system = out_adaffile.sys.create(system_name)
        if raster_name not in new_system.keys():
            new_raster = new_system.create(raster_name)
        new_raster.create_basis(new_timebasis, attributes={'unit': unit})

        # Loop over all signals and resample them
        for i_signal, signal_name in enumerate(signals):
            if signal_name not in in_adaffile.ts.keys():
                continue

            progress(100. * (i + float(i_signal) / len(signals)) /
                     len(new_timebases))
            signal = in_adaffile.ts[signal_name]
            origin_raster_name = signal.raster_name()
            origin_system_name = signal.system_name()
            origin_raster = (
                in_adaffile.sys[origin_system_name][origin_raster_name])
            resample_signal(parameter_root, origin_raster, new_raster, signal)
    progress(100.)


def resample_file(parameter_root, in_adaffile, out_adaffile, progress):
    dt = parameter_root['dt'].value
    use_dt = parameter_root['use_dt'].value
    new_tb = parameter_root['new_tb'].selected
    resample_all = parameter_root['resample_all_rasters'].value
    chosen_signals = parameter_root['ts'].value_names

    if resample_all:
        signals = in_adaffile.ts.keys()
    else:
        signals = chosen_signals

    # Create output system/raster
    if use_dt:
        system_name = 'Resampled system'
        raster_name = 'Resampled raster'
        new_timebasis, unit = get_new_timebasis(in_adaffile, dt, signals)
    else:
        raster_dict = get_raster_dict(in_adaffile)
        system_name, raster_name = raster_dict[new_tb]
        old_tb_column = (in_adaffile.sys[system_name][raster_name]
                         .basis_column())
        new_timebasis = old_tb_column.value()
        unit = old_tb_column.attr['unit']
    new_system = out_adaffile.sys.create(system_name)
    new_raster = new_system.create(raster_name)
    if unit:
        attributes = {'unit': unit}
    else:
        attributes = {}
    new_raster.create_basis(new_timebasis, attributes=attributes)

    # Loop over all signals and resample them
    for i, signal_name in enumerate(signals):
        if signal_name not in in_adaffile.ts.keys():
            continue

        progress(100. * i / len(signals))
        signal = in_adaffile.ts[signal_name]
        origin_raster_name = signal.raster_name()
        origin_system_name = signal.system_name()
        origin_raster = in_adaffile.sys[origin_system_name][origin_raster_name]
        resample_signal(parameter_root, origin_raster, new_raster, signal)


def resample_signal(parameter_root, origin_raster, new_raster, signal):
    """Resample signal to new timebasis."""
    interp_methods = (parameter_root['bool_interp_method'].selected,
                      parameter_root['int_interp_method'].selected,
                      parameter_root['interpolation_method'].selected)

    origin_basis = origin_raster.basis_column().value()
    new_basis = new_raster.basis_column().value()

    if len(signal.y) and len(new_basis):
        f_i = get_interpolated_function(origin_basis, signal.y, interp_methods)
        new_y = f_i(new_basis)
    else:
        new_y = np.zeros_like(new_basis, dtype=signal.y.dtype)
        if signal.y.dtype.kind == 'f':
            new_y *= np.nan
    attrs = dict(signal.signal().attr.items())
    new_raster.create_signal(signal.name, new_y, attrs)


def get_new_timebasis(in_adaffile, dt, signals):
    """
    Get new timebasis covering the same range as all the old timebases using
    step size dt.
    """
    if dt <= 0:
        raise SyConfigurationError('Time step must be positive.')

    t_start = np.inf
    t_end = -np.inf
    basis_kind = None
    basis_unit = None

    # The range of the new time basis should be the superset of all the
    # times in the resampled rasters.
    # TODO: What about reference times here?
    for signal_name in signals:
        if signal_name not in in_adaffile.ts.keys():
            sywarn("Missing signal: {}".format(signal_name))
            continue
        signal = in_adaffile.ts[signal_name]
        raster_name = signal.raster_name()
        system_name = signal.system_name()
        old_basis = in_adaffile.sys[system_name][raster_name].basis_column()
        basis = old_basis.value()
        unit = old_basis.attr.get_or_empty('unit')

        if basis_kind:
            if basis_kind != basis.dtype.kind:
                raise SyDataError(
                    "Either all time bases must be datetime type or "
                    "all rasters must be numeric.")
        else:
            basis_kind = basis.dtype.kind
        if basis_unit and unit and basis_unit != unit:
            raise SyDataError(
                "All selected signals must have the same time unit.")
        elif unit:
            basis_unit = unit

        t_start = min(t_start, basis[0])
        t_end = max(t_end, basis[-1])
    if t_end <= t_start:
        # None of the selected signals were present, return empty target basis
        return np.array([]), ''
    if basis_kind == 'M':
        dt *= np.timedelta64(1000000, 'us')
    timebasis_new = np.arange(t_start, t_end, dt)
    return timebasis_new, basis_unit


def nearest_any(tb_old, ts_old):
    """Returns nearest neighbour function for tb_old and ts_old."""
    def nearest_inner(tb_new):
        if len(tb_old) == 1:
            result = np.array([ts_old[0]] * len(tb_new))
        else:
            f = interp1d(tb_old, np.arange(len(tb_old)), bounds_error=False)
            i_new = f(tb_new)
            i_new += 0.5

            # If the old time basis starts with multiple data points with the
            # same time stamp, the interpolation will give NaN values for that
            # time. Since this only happens at the start we can treat any NaN
            # values as being too early.
            too_early = np.logical_or(tb_new < tb_old[0], np.isnan(i_new))
            too_late = tb_new > tb_old[-1]
            i_new[too_early] = 0
            i_new[too_late] = -1

            result = ts_old[list(i_new)]
        return result
    return nearest_inner


def zero_any(tb_old, ts_old):
    """Returns nearest previous neighbour function for tb_old and ts_old."""
    def zero_inner(tb_new):
        # Sometimes time bases contain several equal times in a row. This mask
        # tries to filter out such data points. It is true for the last value
        # for any sequence of equal time stamps. Be aware that it will be of
        # length one if the input is of zero length.
        mask = np.append((tb_old[1:] != tb_old[:-1]), True)

        if len(tb_old) == 0:
            raise SyDataError('Empty (zero rows) rasters are not supported.')
        elif np.count_nonzero(mask) == 1:
            result = np.array([ts_old[mask][0]] * len(tb_new))
        else:
            f = interp1d(tb_old[mask], np.flatnonzero(mask),
                         bounds_error=False, fill_value=-1)
            if any(np.isnan(tb_new)):
                sywarn("NaNs in tb_new")
            i_new = f(tb_new)
            if any(np.isnan(i_new)):
                sywarn("NaNs in i_new")

            result = ts_old[list(i_new)]

        # Samples that aren't covered by the tb_old domain should be "empty".
        # This is as close to "empty" as we can get without using masked
        # arrays.
        too_early = tb_new < tb_old[0]
        if result.dtype.kind in ('f', 'c'):
            result[too_early] = np.nan
        elif result.dtype.kind in ('i', 'u', 'b', 'm', 'M'):
            result[too_early] = 0
        elif result.dtype.kind in ('S', 'U'):
            result[too_early] = ''
        else:
            raise TypeError('Unknown dtype: {}'.format(result.dtype))
        return result
    return zero_inner


def get_interpolated_function(tb_old, ts_old, interp_methods):
    """Get interplated function from timbase and timeserie."""
    def datetime_wrapper(interp):
        def dt_inner(tb_new):
            tb_old = (tb_new - tb_new[0]) / timeunit
            return interp(tb_old)
        return dt_inner

    bool_interp_method = interp_methods[0]
    int_interp_method = interp_methods[1]
    float_interp_method = interp_methods[2]

    if tb_old.dtype.kind == 'M':
        tb_is_datetime = True
    else:
        tb_is_datetime = False
    timeunit = np.timedelta64(1, 'us')

    kind = ts_old.dtype.kind
    if kind in ('b', 'S', 'U'):
        interp = bool_interp_method
    elif kind in ('i', 'u'):
        interp = int_interp_method
    else:
        interp = float_interp_method

    if interp == 'nearest':
        return nearest_any(tb_old, ts_old)
    elif interp == 'zero':
        return zero_any(tb_old, ts_old)

    if tb_old.size == ts_old.size == 1:
        # Signals with one sample can only be resampled using 'nearest' or
        # 'zero'.
        sywarn("Can't interpolate signal with one sample using method '{}', "
               "falling back to method 'nearest'".format(interp))
        return nearest_any(tb_old, ts_old)
    else:
        if tb_is_datetime:
            tb_old = (tb_old - tb_old[0]) / timeunit
        f_i = interp1d(tb_old, ts_old, kind=interp, bounds_error=False)

    if tb_is_datetime:
        return datetime_wrapper(f_i)
    else:
        return f_i


def get_adaflist_signals(input_list):
    signals = set()
    if input_list.is_valid():
        for adaffile in input_list:
            signals.update(adaffile.ts.keys())
    signals = sorted(signals)
    return signals


def get_adaflist_rasters(input_list):
    rasters = set()
    if input_list.is_valid():
        for adaffile in input_list:
            rasters.update(get_rasters(adaffile))
    rasters = sorted(rasters)
    return rasters


def get_rasters(adaffile):
    return get_raster_dict(adaffile).keys()


def get_raster_dict(adaffile):
    if adaffile.is_valid():
        return collections.OrderedDict(
            [('/'.join([system_name, raster_name]), (system_name, raster_name))
             for system_name, system in adaffile.sys.items()
             for raster_name in system.keys()])
    else:
        return {}


class SuperNode(object):
    author = 'Helena Olen <helena.olen@combine.se'
    copyright = '(C) 2013 Combine AB'
    version = '2.0'
    icon = 'interpolate.svg'
    tags = Tags(Tag.Analysis.SignalProcessing)

    parameters = synode.parameters()
    parameters.set_boolean(
        'resample_all_rasters', value=True, label="Resample all signals",
        description='Apply resampling to all signals')
    ts_editor = synode.Util.selectionlist_editor('multi')
    ts_editor.set_attribute('filter', True)
    parameters.set_list(
        'ts', label="Choose signals", editor=ts_editor.value())
    parameters.set_float(
        'dt', label='Time step',
        description=('Time step in new timebasis. If old timebasis is of '
                     'type datetime this is considered to be in seconds.'))
    parameters.set_list(
        'new_tb', label='Timebasis to use for interpolation',
        description=('Timebasis to use as new timebasis '
                     'for selected timeseries'),
        editor=synode.Util.combo_editor().value())
    parameters.set_boolean('use_dt', value=True)
    parameters.set_list(
        'bool_interp_method', plist=['zero', 'nearest'], value=[1],
        description=('Method used to interpolate boolean, text, and '
                     'byte string data'),
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'int_interp_method', plist=_METHODS, value=[_METHODS.index('nearest')],
        description='Method used to interpolate integer data',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'interpolation_method', plist=_METHODS,
        value=[_METHODS.index('linear')],
        description='Method used to interpolate other data types',
        editor=synode.Util.combo_editor().value())


class InterpolationNode(SuperNode, synode.Node):
    """
    Interpolation of timeseries in an ADAF.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : ADAF
            ADAF with interpolated data.
    :Configuration:
        **Use custom timestep**
            Create a new time basis by specifying a time step.
        **Time step**
            Choose time step of new basis. If time basis has type datetime,
            this parameter will be assumed to be in seconds, otherwise it is
            assumed to be in the same unit as the time basis. Only available if
            *Use custom timestep* is selected.
        **Interpolate using existing timebasis**
            Select existing basis as target basis for selected columns.
        **Time basis column**
            Select raster to choose target time series columns from. Only
            available if *Interpolate using exisisting timebasis* is selected.
        **Interpolation methods**
            Select interpolation method for different groups if data types.
        **Time series columns**
            Select one or many time series columns to interpolate to the new
            basis.
        **Resample all signals**
            Always resample all available time series instead of only the ones
            selected in *Time series columns*.

    :Ref. nodes: :ref:`Interpolate ADAFs`
    """

    name = 'Interpolate ADAF'
    description = 'Interpolation of data'
    nodeid = 'org.sysess.sympathy.data.adaf.interpolateadaf'

    inputs = Ports([Port.ADAF('Input ADAF', name='port1')])
    outputs = Ports([Port.ADAF('Interpolated ADAF', name='port1')])

    def adjust_parameters(self, node_context):
        parameter_root = node_context.parameters
        in_adaffile = node_context.input['port1']
        rasters = get_rasters(in_adaffile)
        if in_adaffile.is_valid():
            signals = in_adaffile.ts.keys()
        else:
            signals = []
        parameter_root['new_tb'].list = rasters
        parameter_root['ts'].list = signals
        return node_context

    def exec_parameter_view(self, node_context):
        adaffile = node_context.input['port1']
        parameter_root = node_context.parameters
        rasters = get_rasters(adaffile)
        return InterpolationWidget(parameter_root, rasters)

    def execute(self, node_context):
        in_adaffile = node_context.input['port1']
        out_adaffile = node_context.output['port1']
        parameter_root = node_context.parameters
        out_adaffile.meta.from_table(in_adaffile.meta.to_table())
        out_adaffile.res.from_table(in_adaffile.res.to_table())
        resample_file(parameter_root, in_adaffile, out_adaffile,
                      progress=self.set_progress)


class InterpolationNodeADAFs(SuperNode, synode.Node):
    """
    Interpolation of timeseries in ADAFs.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : ADAF
            ADAF with interpolated data.
    :Configuration:
        **Use custom timestep**
            Create a new time basis by specifying a time step.
        **Time step**
            Choose time step of new basis. If time basis has type datetime,
            this parameter will be assumed to be in seconds, otherwise it is
            assumed to be in the same unit as the time basis. Only available if
            *Use custom timestep* is selected.
        **Interpolate using existing timebasis**
            Select existing basis as target basis for selected columns.
        **Time basis column**
            Select raster to choose target time series columns from. Only
            available if *Interpolate using exisisting timebasis* is selected.
        **Interpolation methods**
            Select interpolation method for different groups if data types.
        **Time series columns**
            Select one or many time series columns to interpolate to the new
            basis.
        **Resample all signals**
            Always resample all available time series instead of only the ones
            selected in *Time series columns*.

    :Ref. nodes: :ref:`Interpolate ADAF`
    """

    name = 'Interpolate ADAFs'
    description = 'Interpolation of data'
    nodeid = 'org.sysess.sympathy.data.adaf.interpolateadafs'

    inputs = Ports([Port.ADAFs('Input ADAFs', name='port1')])
    outputs = Ports([Port.ADAFs('Interpolated ADAFs', name='port1')])

    def adjust_parameters(self, node_context):
        parameter_root = node_context.parameters
        input_list = node_context.input['port1']

        rasters = get_adaflist_rasters(input_list)
        signals = get_adaflist_signals(input_list)
        parameter_root['new_tb'].list = rasters
        parameter_root['ts'].list = signals
        return node_context

    def exec_parameter_view(self, node_context):
        parameter_root = node_context.parameters
        return InterpolationWidget(parameter_root)

    def execute(self, node_context):
        input_list = node_context.input['port1']
        output_list = node_context.output['port1']
        parameter_root = node_context.parameters
        for i, in_adaffile in enumerate(input_list):
            progress = lambda x: self.set_progress(
                (100. * i + x) / len(input_list))
            out_adaffile = output_list.create()
            out_adaffile.meta.from_table(in_adaffile.meta.to_table())
            out_adaffile.res.from_table(in_adaffile.res.to_table())
            resample_file(parameter_root, in_adaffile, out_adaffile,
                          progress=progress)
            output_list.append(out_adaffile)


class InterpolationNodeADAFsFromTable(synode.Node):
    """
    Interpolation of timeseries in ADAFs using a specification table. The
    specification table should have two to three columns. It must have a column
    with the names of the signals that should be interpolated. Furthermore it
    should have either a column with resampling rate for each signal or a
    column with the names of the signals to whose time basis it should
    interpolate each signal. It can also have both columns and if both of them
    have values for the same row it will use the resample rate.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : ADAF
            ADAF with interpolated data.
    :Configuration:
        **Use custom timestep**
            Create a new time basis by specifying a time step.
        **Time step**
            Choose time step of new basis. If time basis has type datetime,
            this parameter will be assumed to be in seconds, otherwise it is
            assumed to be in the same unit as the time basis. Only available if
            *Use custom timestep* is selected.
        **Interpolate using existing timebasis**
            Select existing basis as target basis for selected columns.
        **Time basis column**
            Select raster to choose target time series columns from. Only
            available if *Interpolate using exisisting timebasis* is selected.
        **Interpolation methods**
            Select interpolation method for different groups if data types.
        **Time series columns**
            Select one or many time series columns to interpolate to the new
            basis.
        **Resample all signals**
            Always resample all available time series instead of only the ones
            selected in *Time series columns*.

    :Ref. nodes: :ref:`Interpolate ADAF`
    """

    name = 'Interpolate ADAFs with Table'
    description = 'Interpolation of data'
    nodeid = 'org.sysess.sympathy.data.adaf.interpolateadafswithtable'
    version = '1.0'
    copyright = 'Copyright (c) 2015 SysESS'
    author = 'Magnus Sandén <magnus.sanden@combine.se>'
    icon = 'interpolate.svg'
    tags = Tags(Tag.Analysis.SignalProcessing)

    inputs = Ports([Port.Table('Specification Table', name='spec'),
                    Port.ADAFs('Input ADAFs', name='port1')])
    outputs = Ports([Port.ADAFs('Interpolated ADAFs', name='port1')])

    parameters = synode.parameters()
    parameters.set_list(
        'signals_colname', label='Column with signal names.',
        description='Resample the time series in this column.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'dt_colname', label='Column with sample rates.',
        description=('The selected column should contain sample rates to '
                     'which the selected signals will be resampled. '
                     'At least one of this parameter and the time bases '
                     'parameter must be specified.'),
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'tb_colname', label='Column with time bases.',
        description=('The selected column should contain existsing time bases '
                     'to which the selected signals will be resampled. '
                     'At least one of this parameter and the time bases '
                     'parameter must be specified.'),
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'bool_interp_method', plist=['zero', 'nearest'], value=[1],
        description=('Method used to interpolate boolean, text, and '
                     'byte string data'),
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'int_interp_method', plist=_METHODS, value=[_METHODS.index('nearest')],
        description='Method used to interpolate integer data',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'interpolation_method', plist=_METHODS,
        value=[_METHODS.index('linear')],
        description='Method used to interpolate other data types',
        editor=synode.Util.combo_editor().value())

    def adjust_parameters(self, node_context):
        spec_table = node_context.input['spec']
        if spec_table.is_valid():
            spec_cols = spec_table.column_names()
        else:
            spec_cols = []

        parameters = node_context.parameters
        pnames = ['signals_colname', 'dt_colname', 'tb_colname']
        extra_values = [[], [None], [None]]
        for pname, extra in zip(pnames, extra_values):
            p = parameters[pname]
            old_selected = p.selected
            if old_selected is None or old_selected in spec_cols:
                p.list = extra + spec_cols
            else:
                p.list = extra + [old_selected] + spec_cols

    def exec_parameter_view(self, node_context):
        parameter_root = node_context.parameters
        tab_widget = QtGui.QTabWidget()
        methods_tab = MethodsTab(parameter_root)
        choose_spec_cols_tab = ChooseSpecColsTab(parameter_root)
        tab_widget.addTab(choose_spec_cols_tab, 'Specification table')
        tab_widget.addTab(methods_tab, 'Interpolation method')
        return tab_widget

    def execute(self, node_context):
        input_list = node_context.input['port1']
        spec = node_context.input['spec']
        output_list = node_context.output['port1']
        parameter_root = node_context.parameters

        for i, in_adaffile in enumerate(input_list):
            progress = lambda x: self.set_progress(
                (100. * i + x) / len(input_list))
            out_adaffile = output_list.create()
            out_adaffile.meta.from_table(in_adaffile.meta.to_table())
            out_adaffile.res.from_table(in_adaffile.res.to_table())
            resample_file_with_spec(parameter_root, spec, in_adaffile,
                                    out_adaffile, progress=progress)
            output_list.append(out_adaffile)


class ChooseSpecColsTab(QtGui.QWidget):
    def __init__(self, parameter_root):
        super(ChooseSpecColsTab, self).__init__()
        layout = QtGui.QVBoxLayout()
        layout.addWidget(parameter_root['signals_colname'].gui())
        layout.addWidget(parameter_root['dt_colname'].gui())
        layout.addWidget(parameter_root['tb_colname'].gui())

        layout.addStretch(0)
        self.setLayout(layout)


class MethodsTab(QtGui.QWidget):
    def __init__(self, parameter_root):
        super(MethodsTab, self).__init__()
        layout = QtGui.QVBoxLayout()
        layout.addWidget(QtGui.QLabel(
            "Choose interpolation methods for different data types."))
        form_layout = QtGui.QFormLayout()

        categories = ['Boolean, text, and byte string', 'Integer',
                      'Other data types']
        parameters = ['bool_interp_method', 'int_interp_method',
                      'interpolation_method']
        for category, parameter in zip(categories, parameters):
            widget = parameter_root[parameter].gui()
            form_layout.addRow(category, widget)

        layout.addLayout(form_layout)
        layout.addStretch(0)
        self.setLayout(layout)


class InterpolationWidget(QtGui.QWidget):
    """A widget containing a TimeBasisWidget and a ListSelectorWidget."""

    def __init__(self, parameter_root, parent=None):
        super(InterpolationWidget, self).__init__()
        self._parameter_root = parameter_root
        self._init_gui()

    def _init_gui(self):
        # Create widgets and add to layout
        tab_widget = QtGui.QTabWidget()
        tb_tab = self._init_tb_tab()
        tab_widget.addTab(tb_tab, 'New time basis')
        methods_tab = MethodsTab(self._parameter_root)
        tab_widget.addTab(methods_tab, 'Interpolation method')
        signals_tab = self._init_signals_tab()
        tab_widget.addTab(signals_tab, 'Signals')

        layout = QtGui.QVBoxLayout()
        layout.addWidget(tab_widget)
        self.setLayout(layout)
        self._init_gui_from_parameters()

    def _init_tb_tab(self):
        # Create radio button group
        self._dt_or_tb = QtGui.QButtonGroup()
        self._dt_or_tb.setExclusive(True)

        self._custom_dt_button = QtGui.QRadioButton('Use custom timestep')
        self._use_tb_button = QtGui.QRadioButton(
            'Interpolate using existing timebasis')

        # Add buttons to group
        self._dt_or_tb.addButton(self._custom_dt_button)
        self._dt_or_tb.addButton(self._use_tb_button)

        self._new_tb = self._parameter_root['new_tb'].gui()
        self._dt = self._parameter_root['dt'].gui()

        tb_ts_vlayout = QtGui.QVBoxLayout()
        tb_ts_vlayout.addWidget(self._custom_dt_button)
        tb_ts_vlayout.addWidget(self._dt)

        tb_ts_vlayout.addWidget(self._use_tb_button)
        tb_ts_vlayout.addWidget(self._new_tb)
        tb_ts_vlayout.addStretch(0)

        tb_tab = QtGui.QWidget()
        tb_tab.setLayout(tb_ts_vlayout)

        self._dt_or_tb.buttonClicked.connect(self._button_changed)

        return tb_tab

    def _init_signals_tab(self):
        signals_tab = QtGui.QWidget()

        self._ts_selection = self._parameter_root['ts'].gui()
        self._resample_all_signals = (
            self._parameter_root['resample_all_rasters'].gui())

        signals_vlayout = QtGui.QVBoxLayout()
        signals_vlayout.addWidget(self._resample_all_signals)
        signals_vlayout.addWidget(self._ts_selection)
        signals_vlayout.addStretch(0)

        self._resample_all_signals.editor().toggled.connect(
            self._ts_selection.set_disabled)
        self._ts_selection.set_disabled(
            self._parameter_root['resample_all_rasters'].value)

        signals_tab.setLayout(signals_vlayout)
        return signals_tab

    def _init_gui_from_parameters(self):
        dt_checked = self._parameter_root['use_dt'].value
        self._custom_dt_button.setChecked(dt_checked)
        self._use_tb_button.setChecked(not dt_checked)
        self._use_tb_button.setChecked(not dt_checked)
        self._dt.setEnabled(dt_checked)
        self._new_tb.setEnabled(not dt_checked)

    def _button_changed(self, button):
        """
        Radiobuttton clicked. Enable/disable custom coefficient edits or
        predefined filter widgets depedning on which button that is pressed.
        """
        if button == self._custom_dt_button:
            self._dt.setEnabled(True)
            self._new_tb.setEnabled(False)
            self._parameter_root['use_dt'].value = True
        else:
            self._dt.setEnabled(False)
            self._new_tb.setEnabled(True)
            self._parameter_root['use_dt'].value = False
