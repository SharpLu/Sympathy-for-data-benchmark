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
.. deprecated:: 1.2.5
    Use :ref:`Interpolate ADAF` or :ref:`Interpolate ADAFs` instead.

Interpolate timeseries by the chosen interpolation method and calculate the
new timeseries based on a new timebasis. The new timebasis can either be an
existing timebasis in the adaf-file or a timebasis with a timestep defined
by the user. The timeseries that will be interpolated are selected in a list.
The output file will contain the unmodified timeseries, and the modfied ones.
The modified timeseries will be moved to a new timebasis if a timestep is
used and to the existing timebasis if that alternative is chosen.
"""
from itertools import izip

import numpy as np
from scipy.interpolate import interp1d, UnivariateSpline

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import sywarn, SyConfigurationError
from sympathy.api import qt as qt_compat
from sympathy.api import table
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module('QtGui')


def deprecationwarn(plural=""):
    sywarn("This Interpolate ADAF{} node is being deprecated in an upcoming "
           "release of sympathy. Please remove the node and add a new one "
           "to your workflow.".format(plural))


def resample_raster(parameter_root, raster_dict, adaffile):
    """Resample raster."""
    use_dt = parameter_root['use_dt'].value
    interpolation_method = parameter_root['interpolation_method'].selected

    try:
        # Avoid breaking older nodes without this option.
        resample_all = parameter_root['resample_all_rasters'].value
    except KeyError:
        resample_all = False

    if resample_all:
        rasters = (raster for system in adaffile.sys.values()
                   for raster in system.values())
    else:
        try:
            rasters = [raster_dict[parameter_root['tb'].selected]]
        except KeyError:
            # If the raster is unavailable don't resample.
            rasters = []

    for origin_raster in rasters:
        origin_basis = origin_raster.basis_column().value()

        if not len(origin_basis):
            # Do not attempt to resample an empty raster. Creating NaN values
            # would probably not be useful and cannot be used in any type.
            return

        if use_dt:
            dt = parameter_root['dt'].value
            if not dt:
                raise SyConfigurationError(
                    'Time step must be set and non-zero.')
            if origin_basis.dtype.kind == 'M':
                dt *= np.timedelta64(1000000, 'us')

            target_basis = get_new_timebasis(dt, origin_basis)
        else:
            target_basis = raster_dict[
                parameter_root['new_tb'].selected].basis_column().value()

        data = []

        for name, series in origin_raster.items():
            data.append((name, series.y, dict(series.signal().attr.items())))

        basis_attrs = dict(origin_raster.basis_column().attr.items())
        origin_raster.from_table(table.File(), basis_name=None)

        for name, y, attrs in data:

            column = resample_signal(
                origin_basis,
                target_basis,
                y,
                interpolation_method)
            origin_raster.create_signal(
                name, column, attrs)

        origin_raster.create_basis(target_basis, basis_attrs)


def get_new_timebasis(dt, tb):
    """
    Get new timebasis covering the same range as old timebasis using
    step size dt.
    """
    t_start = tb[0]
    t_end = tb[-1]
    timebasis_new = np.arange(t_start, t_end, dt)
    return timebasis_new


def nearest_any(tb_old, ts_old):
    """
    Returns nearest neighbour function for tb_old and ts_old.
    The function works for any type of ts as long as tb can be ordered with
    < and >.
    """
    def inner(tb_new):
        in_iter = izip(ts_old, tb_old)
        curr_y, curr_t = in_iter.next()
        prev_y = curr_y
        prev_t = curr_t
        result = []
        try:
            for t in tb_new:
                while curr_t is not None and t > curr_t:
                    # Move the position.
                    prev_y = curr_y
                    prev_t = curr_t
                    curr_y, curr_t = in_iter.next()
                if curr_t is None:
                    result.append(prev_y)
                if prev_t is None:
                    result.append(curr_y)

                if curr_t - t < t - prev_t:
                    result.append(curr_y)
                else:
                    result.append(prev_y)
        except StopIteration:
            if len(tb_new) > len(result):
                result.extend((len(tb_new) - len(result)) * [curr_y])

        return np.array(result, dtype=ts_old.dtype)
    return inner


def get_interpolated_function(tb, ts, interpolation_method):
    """Get interplated function from timbase and timeserie."""
    def datetime_wrapper(interp):
        def inner(tb_new):
            tb = (tb_new - tb_new[0])/timeunit
            return interp(tb)
        return inner

    if tb.dtype.kind == 'M':
        is_datetime = True
    else:
        is_datetime = False
    timeunit = np.timedelta64(1, 'us')

    try:
        if is_datetime:
            tb = (tb - tb[0])/timeunit
        if ts.dtype.kind == 'f':
            if interpolation_method == 'cubic':
                f_i = UnivariateSpline(tb, ts, k=3)
            elif interpolation_method == 'quadratic':
                f_i = UnivariateSpline(tb, ts, k=4)
            else:
                f_i = interp1d(
                    tb, ts, kind=interpolation_method, bounds_error=False)
        else:
            f_i = interp1d(
                tb, ts, kind='nearest', bounds_error=False)
    except ValueError:
        return nearest_any(tb, ts)
    if is_datetime:
        return datetime_wrapper(f_i)
    else:
        return f_i


def resample_signal(tb_old, tb_new, ts, interpolation_method):  # dtype, ???!!
    """Resample signal to new timebasis t_new if singal more than 1 point."""
    if len(ts) > 1 and len(tb_old) > 1:
        f_i = get_interpolated_function(tb_old, ts, interpolation_method)
        ts_new = f_i(tb_new)
    else:
        ts_new = ts
    return ts_new


def check_consistence(parameter_root, raster_dict):
    """Check if items in widgets are consistent with input file."""
    if sorted(parameter_root['tb'].list) == sorted(raster_dict.keys()):
        return True
    else:
        return False


def reinit_interpolation(parameter_root):
    """Reinitialize node when infile has changed."""
    parameter_root['tb'].list = []
    parameter_root['tb'].value = [0]
    parameter_root['tb'].value_names = []
    parameter_root['ts'].list = []
    parameter_root['ts'].value = [0]
    parameter_root['ts'].value_names = []
    parameter_root['new_tb'].list = []
    parameter_root['new_tb'].value = [0]
    parameter_root['new_tb'].value_names = []
    parameter_root['interpolation_method'].value = [0]
    parameter_root['dt'].value = 0
    parameter_root['use_dt'].value = True


def check_and_reinit_node(parameter_root, raster_dict):
    """
    Check if node_context consistent with info from input file and
    reinitialize if not.
    """
    if not check_consistence(parameter_root, raster_dict):
        reinit_interpolation(parameter_root)


def get_interpolations():
    """Get list of available interpolation methods."""
    interpolation_methods = ['linear', 'nearest', 'zero',
                             'slinear', 'quadratic', 'cubic']
    return interpolation_methods


def get_raster_dict(adaffile):
    if adaffile.is_valid():
        return dict([('/'.join([system_name, raster_name]), raster)
                     for system_name, system in adaffile.sys.items()
                     for raster_name, raster in system.items()])
    else:
        return dict()


class SuperNode(object):
    author = 'Helena Olen <helena.olen@combine.se'
    copyright = '(C) 2013 Combine AB'
    version = '1.0'
    icon = 'interpolate.svg'
    tags = Tags(Tag.Hidden.Deprecated)

    def update_parameters(self, old_params):
        # From the beginning there was no parameter called resample_all_rasters.
        if 'resample_all_rasters' not in old_params:
            # At that point the node behaved as though the parameter was False.
            old_params.set_boolean(
                'resample_all_rasters', value=False,
                label="Resample all rasters",
                description='Apply resampling to all rasters')
        else:
            # Then there was a parameter, but it didn't have label/description.
            if not old_params['resample_all_rasters'].description:
                old_params['resample_all_rasters'].description = (
                    'Apply resampling to all rasters')
            if not old_params['resample_all_rasters'].label:
                old_params['resample_all_rasters'].label = 'Resample all rasters'


def base_parameters():
    parameter_root = synode.parameters()
    ts_editor = synode.Util.selectionlist_editor('multi')
    ts_editor.set_attribute('filter', True)
    parameter_root.set_list('tb',
                            label="Time basis column",
                            value=[0],
                            editor=synode.Util.list_editor().value())
    parameter_root.set_list('ts',
                            label="Time series columns in preview",
                            value=[0],
                            editor=ts_editor.value())
    parameter_root.set_list('interpolation_method', plist=get_interpolations(),
                            label='Interpolation method',
                            value=[0],
                            description='Function used to detrend data',
                            editor=synode.Util.combo_editor().value())
    parameter_root.set_float('dt', label='Time step',
                             description='Time step in new timebasis. If old '
                                         'timebasis is of type datetime this '
                                         'is considered to be in seconds.')
    parameter_root.set_list('new_tb', value=[0],
                            label='Timebasis to use for interpolation',
                            description=('Timebasis to use as new timebasis'
                            'for selected timeseries'),
                            editor=synode.Util.combo_editor().value())
    parameter_root.set_boolean('use_dt', value=True)
    parameter_root.set_boolean(
        'resample_all_rasters', value=True,
        label="Resample all rasters",
        description='Apply resampling to all rasters')
    return parameter_root


class InterpolationNodeOld(SuperNode, synode.Node):
    """
    .. deprecated:: 1.2.5
        Use :ref:`Interpolate ADAF` instead.

    Interpolation of timeseries in an ADAF.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : ADAF
            ADAF with interpolated data.
    :Configuration:
        **Use custom timestep**
            Specify the custom step length for basis in a new raster.
        **Interpolate using existing timebasis**
            Select basis in another raster as new basis for selected columns.
        **Interpolation method**
            Select interpolation method.
        **Time basis column**
            Select raster to choose time series columns from.
        **Time series columns**
            Select one or many time series columns to interpolate to the new
            basis.
    :Ref. nodes: :ref:`Interpolate ADAF`
    """
    name = 'Interpolate ADAF (deprecated)'
    description = 'Interpolation of data'
    nodeid = 'org.sysess.sympathy.data.adaf.interpolationnode'

    inputs = Ports([Port.ADAF('ADAFInput', name='port1')])
    outputs = Ports([Port.ADAF('ADAFOutput', name='port1')])

    parameters = base_parameters()

    def exec_parameter_view(self, node_context):
        deprecationwarn()
        adaffile = node_context.input['port1']
        parameter_root = node_context.parameters
        raster_dict = get_raster_dict(adaffile)
        check_and_reinit_node(parameter_root, raster_dict)
        return InterpolationWidget(parameter_root, raster_dict)

    def execute(self, node_context):
        deprecationwarn()
        in_adaffile = node_context.input['port1']
        out_adaffile = node_context.output['port1']
        parameter_root = node_context.parameters
        raster_dict = get_raster_dict(in_adaffile)
        check_and_reinit_node(parameter_root, raster_dict)
        resample_raster(parameter_root, raster_dict, in_adaffile)
        out_adaffile.source(in_adaffile)


class InterpolationNodeADAFsOld(SuperNode, synode.Node):
    """
    .. deprecated:: 1.2.5
        Use :ref:`Interpolate ADAFs` instead.

    Interpolation of timeseries in ADAFs.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : ADAF
            ADAF with interpolated data.
    :Configuration:
        **Use custom timestep**
            Specify the custom step length for basis in a new raster.
        **Interpolate using existing timebasis**
            Select basis in another raster as new basis for selected columns.
        **Interpolation method**
            Select interpolation method.
        **Time basis column**
            Select raster to choose time series columns from.
        **Time series columns**
            Select one or many time series columns to interpolate to the new
            basis.
    :Ref. nodes: :ref:`Interpolate ADAFs`
    """
    name = 'Interpolate ADAFs (deprecated)'
    description = 'Interpolation of data'
    nodeid = 'org.sysess.sympathy.data.adaf.interpolationnodeADAFs'

    inputs = Ports([Port.ADAFs('ADAFInput', name='port1')])
    outputs = Ports([Port.ADAFs('ADAFOutput', name='port1')])

    parameters = base_parameters()

    def exec_parameter_view(self, node_context):
        deprecationwarn(plural="s")
        input_list = node_context.input['port1']
        parameter_root = node_context.parameters

        if input_list.is_valid() and len(input_list):
            # Present GUI based on the first element.
            first = iter(input_list).next()
            raster_dict = get_raster_dict(first)
        else:
            raster_dict = {}

        check_and_reinit_node(parameter_root, raster_dict)
        return InterpolationWidget(parameter_root, raster_dict)

    def execute(self, node_context):
        deprecationwarn(plural="s")
        input_list = node_context.input['port1']
        output_list = node_context.output['port1']
        parameter_root = node_context.parameters
        for in_adaffile in input_list:
            raster_dict = get_raster_dict(in_adaffile)
            resample_raster(parameter_root, raster_dict, in_adaffile)
            output_list.append(in_adaffile)

class InterpolationWidget(QtGui.QWidget):
    """A widget containing a TimeBasisWidget and a ListSelectorWidget."""

    def __init__(
            self, parameter_root, raster_dict, parent=None):
        super(InterpolationWidget, self).__init__()
        self._parameter_root = parameter_root
        self._raster_dict = raster_dict
        self._figure = None
        self._axes = None
        self._canvas = None
        self._toolbar = None

        self._init_gui()

    def _init_gui(self):
        self._pre_init_gui_from_parameters()

        # Create widgets and add to layout
        self._tb_selection = self._parameter_root['tb'].gui()

        self._interpolation_method = (self._parameter_root[
            'interpolation_method'].gui())

        # Create radio button group
        self._dt_or_tb = QtGui.QButtonGroup()
        self._dt_or_tb.setExclusive(True)

        self._custom_dt_button = QtGui.QRadioButton(
            'Use custom timestep')
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

        tb_ts_vlayout.addWidget(self._interpolation_method)
        tb_ts_vlayout.addWidget(self._tb_selection)

        if 'resample_all_rasters' in self._parameter_root:
            # Avoid breaking older nodes without this option.
            resample_all_gui = (
                self._parameter_root['resample_all_rasters'].gui())
            tb_ts_vlayout.addWidget(resample_all_gui)
            resample_all_gui.editor().toggled.connect(
                self._tb_selection.set_disabled)
            if self._parameter_root['resample_all_rasters'].value:
                self._tb_selection.set_disabled(True)

        hlayout = QtGui.QHBoxLayout()
        hlayout.addLayout(tb_ts_vlayout)

        layout = QtGui.QVBoxLayout()
        layout.addLayout(hlayout)

        self.setLayout(layout)

        self._init_gui_from_parameters()
        self._dt_or_tb.buttonClicked.connect(self._button_changed)

    def _pre_init_gui_from_parameters(self):
        """Pre-initialize GUI from parameters."""
        if self._parameter_root['tb'].list == []:
            self._parameter_root['tb'].list = self._raster_dict.keys()

        if self._parameter_root['tb'].value == []:
            self._parameter_root['tb'].value = [0]

        if self._parameter_root['new_tb'].list == []:
            self._parameter_root['new_tb'].list = self._raster_dict.keys()
            self._parameter_root['new_tb'].value = [0]

    def _init_gui_from_parameters(self):
        dt_checked = self._parameter_root['use_dt'].value
        self._custom_dt_button.setChecked(dt_checked)
        self._use_tb_button.setChecked(not dt_checked)
        self._dt.setEnabled(dt_checked)
        self._new_tb.setEnabled(not dt_checked)

    def _button_changed(self, button):
        """
        Radiobuttton clicked. Enable/disable custom coefficient edits or
        predefined filter widgets depedning on which button that is
        pressed.
        """
        if button == self._custom_dt_button:
            self._dt.setEnabled(True)
            self._new_tb.setEnabled(False)
            self._parameter_root['use_dt'].value = True
        else:
            self._dt.setEnabled(False)
            self._new_tb.setEnabled(True)
            self._parameter_root['use_dt'].value = False
