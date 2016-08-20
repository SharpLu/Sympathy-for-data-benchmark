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
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import collections
import ast
import sys
import warnings

import six

import numpy as np
import scipy.signal as signal

from sympathy.api import table, ParameterView
from sympathy.api import qt as qt_compat
from sympathy.platform.exceptions import sywarn

QtCore = qt_compat.QtCore  # noqa
QtGui = qt_compat.QtGui  # noqa
qt_compat.backend.use_matplotlib_qt()  # noqa

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg \
    import NavigationToolbar2QT as NavigationToolbar

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.utils import prim


class capture_print(list):
    """Context manager for capturing print output."""
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = six.StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout


def write_group(in_group, out_group):
    """Write meta from input file to output ADAF file."""
    def attributes(table):
        return {column: table.get_column_attributes(column)
                for column in table.column_names()}

    attrs_meta = prim.flip(attributes(in_group.to_table()))
    data_meta = in_group.to_table()
    for name in in_group.keys():
        try:
            attrs = attrs_meta[name]
        except KeyError:
            attrs = {}
        out_group.create_column(
            name, data_meta.get_column_to_array(name), attrs)


def write_res(in_adaffile, out_adaffile):
    """Write results from input file to output ADAF file."""
    write_group(in_adaffile.res, out_adaffile.res)


def write_meta(in_adaffile, out_adaffile):
    """Write meta from input file to output ADAF file."""
    write_group(in_adaffile.meta, out_adaffile.meta)


def filter_signals(in_adaffile, out_adaffile, parameters):
    """
    Filter all timeseries in in_adaffile and write to output
    ADAF file with old timebasis, meta and result.
    """
    write_res(in_adaffile, out_adaffile)
    write_meta(in_adaffile, out_adaffile)
    # Generate global filter design
    b, a = generate_filter(parameters)
    for system_name, in_system in in_adaffile.sys.items():
        out_system = out_adaffile.sys.create(system_name)
        for raster_name, in_raster in in_system.items():
            out_raster = out_system.create(raster_name)
            # Making use of the table API to build the output raster.
            # While at the same time taking care to propagate attributes.
            in_raster_table = in_raster.to_table()
            out_raster_table = table.File()
            for column_name in in_raster.keys():
                column_data = in_raster_table.get_column_to_array(column_name)
                attributes = in_raster_table.get_column_attributes(column_name)
                try:
                    column = filter_signal(parameters, b, a, column_data)
                    attributes['Filtering'] = six.text_type(
                        create_filter_parameter_attributes(parameters)
                    )
                except ValueError as e:
                    sywarn('A ValueError occurred during signal filtering. '
                           'The column "{}" is returned unfiltered!\n'
                           'Error message: {}'.format(column_name, e))
                    column = column_data
                    attributes['Filtering'] = 'Unfiltered due to Error'
                out_raster_table.set_column_from_array(column_name, column)
                out_raster_table.set_column_attributes(column_name, attributes)
            in_basis = in_raster.basis_column()
            out_raster.from_table(out_raster_table)
            out_raster.create_basis(
                in_basis.value(), dict(in_basis.attr.items()))


def generate_filter(parameters):
    """Generate filter."""
    filter_type = parameters['filter_type'].selected
    if filter_type == 'IIR':
        b, a = iir_filter_design(parameters)
    else:
        b, a = fir_filter_design(parameters)
    return b, a


def create_filter_parameter_attributes(parameters):
    """Generate a filter parameter attribute representation."""
    filter_type = parameters['filter_type'].selected
    filter_dict = collections.OrderedDict()
    filter_dict['Filter Type'] = filter_type
    if filter_type == 'IIR':
        values = get_iir_filter_parameters(parameters)
        for var, value in zip(['iir_wp', 'iir_ws', 'iir_gpass', 'iir_gstop',
                               'iir_filters'], values):
            label = parameters[var].label
            filter_dict[label] = value
    else:
        fir_dict = get_fir_window_dict()
        fir_window = parameters['fir_windows'].selected
        window = fir_dict[fir_window]['name']
        params = fir_dict[fir_window]['param']
        filter_dict['Filter window'] = window
        filter_dict['Filter length'] = parameters['fir_len'].value
        filter_dict['Cutoff frequency'] = parameters['fir_cutoff'].value
        if len(params) >= 1:
            label = parameters['fir_w1'].label
            filter_dict[label] = parameters['fir_w1'].value
        if len(params) == 2:
            label = parameters['fir_w2'].label
            filter_dict[label] = parameters['fir_w2'].value
        filter_dict['Frequency pass type'] = parameters['freq_type'].selected
    filter_dict['Filtering Type'] = parameters['filtering'].selected
    return '; '.join(['{}: {}'.format(k, v) for k, v in six.iteritems(
        filter_dict)])


def filter_signal(parameters, b, a, ts):
    """Filter timeserie ts."""
    filtering_dict = get_filtering_dict()
    return filtering_dict[parameters['filtering'].selected](b, a, ts)


def get_iir_filter_parameters(parameter_root):
    iir_dict = get_iir_filter_dict()
    wp_str = parameter_root['iir_wp'].value
    wp = ast.literal_eval(wp_str)
    ws_str = parameter_root['iir_ws'].value
    ws = ast.literal_eval(ws_str)
    gpass_str = parameter_root['iir_gpass'].value
    gpass = float(gpass_str)
    gstop_str = parameter_root['iir_gstop'].value
    gstop = float(gstop_str)
    ftype = iir_dict[parameter_root['iir_filters'].selected]
    return wp, ws, gpass, gstop, ftype


def iir_filter_design(parameter_root):
    """Design and return parameters for iir filter."""
    wp, ws, gpass, gstop, ftype = get_iir_filter_parameters(parameter_root)
    b, a = signal.iirdesign(wp, ws, gpass, gstop, ftype=ftype)
    return b, a


def get_fir_filter_parameters(parameter_root):
    fir_dict = get_fir_window_dict()
    fir_window = parameter_root['fir_windows'].selected
    window = fir_dict[fir_window]['name']
    params = fir_dict[fir_window]['param']
    if len(params) == 0:
        window_tuple = (window, )
    elif len(params) == 1:
        arg1 = float(parameter_root['fir_w1'].value)
        window_tuple = (window, arg1)
    else:
        arg1 = float(parameter_root['fir_w1'].value)
        arg2 = float(parameter_root['fir_w2'].value)
        window_tuple = (window, arg1, arg2)
    M = int(parameter_root['fir_len'].value)
    cutoff = ast.literal_eval(parameter_root['fir_cutoff'].value)
    if parameter_root['freq_type'].selected in ['Highpass', 'Bandpass']:
        freq_type = False
    else:
        freq_type = True
    return M, cutoff, window_tuple, freq_type


def fir_filter_design(parameter_root):
    """Get FIR filter coefficients."""
    M, cutoff, window_tuple, freq_type = get_fir_filter_parameters(
        parameter_root)
    b = signal.firwin(M, cutoff, window=window_tuple, pass_zero=freq_type)
    return b, [1.0]


def get_filtering_dict():
    filtering = {'Forward': signal.lfilter,
                 'Forward-Backward': signal.filtfilt}
    return filtering


def get_fir_window_dict():
    fir = {'Bartlett-Hann': {'name': 'barthann',
                             'param': []},
           'Bartlett': {'name': 'bartlett', 'param': []},
           'Blackman': {'name': 'blackman', 'param': []},
           'Blackman-Harris': {'name': 'blackmanharris',
                               'param': []},
           'Bohman': {'name': 'bohman', 'param': []},
           'Boxcar': {'name': 'boxcar', 'param': []},
           'Dolph-Chebyshev': {'name': 'chebwin',
                               'param': ['Attenuation (dB)']},
           'Flat top': {'name': 'flattop', 'param': []},
           'Gaussian': {'name': 'gaussian',
                        'param': ['std']},
           'Generalized Gaussian': {'name': 'general_gaussian',
                                    'param': ['p', 'Sigma']},
           'Hamming': {'name': 'hamming', 'param': []},
           'Hann': {'name': 'hann', 'param': []},
           'Kaiser': {'name': 'kaiser', 'param': ['Beta']},
           'Nuttall': {'name': 'nuttall', 'param': []},
           'Parzen': {'name': 'parzen', 'param': []},
           'Slepian': {'name': 'slepian',
                       'param': ['width']},
           'Triangular': {'name': 'triang', 'param': []}}
    return fir


def get_iir_filter_dict():
    iir = {'Butterworth': 'butter', 'Chebyshev 1': 'cheby1',
           'Chebyshev 2': 'cheby2', 'Elliptic': 'ellip'}
    return iir


class FilterADAFs(synode.Node):
    """
    Filter ADAFs with a specified filter.
    Both IIR filters and FIR filters
    can be selected. The filter can be a forward or forward-backward filter.
    The filter coefficients can either be specified by the
    user or predefined filters can be selected to calculate these coefficients.
    For the predefined filters, lowpass, highpass, bandpass and bandstop
    filters can be defined.

    The FIR filter windows that can be used are:
        - Bartlett-Hann_
        - Bartlett_
        - Blackman_
        - Blackman-Harris_
        - Bohman_
        - Boxcar_
        - Dolph-Chebyshev_
        - `Flat top`_
        - Gaussian_
        - `Generalized Gaussian`_
        - Hamming_
        - Hann_
        - Kaiser_
        - Nuttall_
        - Parzen_
        - Slepian_
        - Triangular_

    .. _Bartlett-Hann: http://en.wikipedia.org/wiki/Window_function#Bartlett.E2.80.93Hann_window
    .. _Bartlett: http://en.wikipedia.org/wiki/Window_function#Triangular_window
    .. _Blackman: http://en.wikipedia.org/wiki/Window_function#Blackman_windows
    .. _Blackman-Harris: http://en.wikipedia.org/wiki/Window_function#Blackman.E2.80.93Harris_window
    .. _Bohman: http://en.wikipedia.org/wiki/Window_function#Cosine_window
    .. _Boxcar: http://en.wikipedia.org/wiki/Window_function#Rectangular_window
    .. _Dolph-Chebyshev: http://en.wikipedia.org/wiki/Window_function#Dolph.E2.80.93Chebyshev_window
    .. _`Flat top`: http://en.wikipedia.org/wiki/Window_function#Flat_top_window
    .. _Gaussian: http://en.wikipedia.org/wiki/Window_function#Gaussian_window
    .. _`Generalized Gaussian`: http://en.wikipedia.org/wiki/Window_function#Gaussian_window
    .. _Hamming: http://en.wikipedia.org/wiki/Window_function#Hamming_window
    .. _Hann: http://en.wikipedia.org/wiki/Window_function#Hann_.28Hanning.29_window
    .. _Kaiser: http://en.wikipedia.org/wiki/Kaiser_window
    .. _Nuttall: http://en.wikipedia.org/wiki/Window_function#Nuttall_window.2C_continuous_first_derivative
    .. _Parzen: http://en.wikipedia.org/wiki/Window_function#Parzen_window
    .. _Slepian: http://en.wikipedia.org/wiki/Window_function#DPSS_or_Slepian_window
    .. _Triangular: http://en.wikipedia.org/wiki/Window_function#Triangular_window

    The IIR filter functions supported are:
        - Butterworth_
        - `Chebyshev 1`_
        - `Chebyshev 2`_
        - Elliptic_

    .. _Butterworth: http://en.wikipedia.org/wiki/Butterworth_filter
    .. _`Chebyshev 1`: http://en.wikipedia.org/wiki/Chebyshev_filter#Type_I_Chebyshev_filters
    .. _`Chebyshev 2`: http://en.wikipedia.org/wiki/Chebyshev_filter#Type_II_Chebyshev_filters
    .. _Elliptic: http://en.wikipedia.org/wiki/Elliptic_filter

    :Inputs:  ADAFs
    :Outputs: ADAFs
    :Configuration: Choose FIR or IIR filter and specify filter coefficients or
                    the function/window to calculate them.
    :Opposite node:
    :Ref. nodes:
    """

    author = 'Helena Olen <helena.olen@combine.se>'
    copyright = '(c) 2013 Combine AB'
    description = 'Filter ADAF data.'
    name = 'Filter ADAFs (deprecated)'
    nodeid = 'org.sysess.sympathy.data.adaf.filteradafs'
    version = '1.0'
    icon = 'filter_adaf.svg'
    tags = Tags(Tag.Analysis.SignalProcessing, Tag.Hidden.Deprecated)

    inputs = Ports([Port.ADAFs('Input ADAFs', name='port1')])
    outputs = Ports([Port.ADAFs(
        'Output ADAFs with filter applied', name='port1')])

    parameters = synode.parameters()
    parameters.set_list(
        'filter_type', plist=['IIR', 'FIR'], label='Filter type', value=[0],
        description='Combo of filter types',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'freq_type', plist=['Lowpass', 'Highpass', 'Bandpass', 'Bandstop'],
        value=[0], description='Frequency pass type',
        label='Frequency pass type',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'fir_windows', plist=sorted(get_fir_window_dict().keys()), value=[12],
        label='Filter windows', description='Filter windows for FIR filter',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'iir_filters', plist=sorted(get_iir_filter_dict().keys()), value=[0],
        label='Filter designs', description='IIR filters',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'filtering', plist=sorted(get_filtering_dict().keys()), value=[0],
        label='Filtering', description='Filtering types',
        editor=synode.Util.combo_editor().value())
    parameters.set_string(
        'filter_param_template', label='Required filter parameters',
        description='Template for required parameters.')
    parameters.set_string(
        'filter_parameters', label='Filter parameters',
        description='Parameters for chosen filter')  # ,
    #        editor=synode.Util.lineedit_editor().value())
    parameters.set_string(
        'numerator_coeff', label='Numerator coefficient vector',
        description='Numerator coefficient vector for filter')  # ,
    #        editor=synode.Util.lineedit_editor().value())
    parameters.set_string(
        'denominator_coeff', label='Denominator coefficient vector',
        description='Denominator coefficient vector for filter')  # ,

    #        editor=synode.Util.lineedit_editor().value())

    def exec_parameter_view(self, node_context):
        return FilterADAFsWidget(node_context)

    def execute(self, node_context):
        input_list = node_context.input['port1']
        output_list = node_context.output['port1']
        number_of_items = len(input_list)

        for idx, adaffile in enumerate(input_list):
            outadaffile = output_list.create()
            filter_signals(adaffile, outadaffile, node_context.parameters)
            output_list.append(outadaffile)
            self.set_progress(100.0 * (idx + 1) / number_of_items)


class FilterADAFsWidget(QtGui.QWidget):
    def __init__(self, node_context, parent=None):
        super(FilterADAFsWidget, self).__init__(parent)
        self._node_context = node_context
        self._parameters = node_context.parameters
        self._init_gui()

    def _init_gui(self):
        self._fir_dict = get_fir_window_dict()
        # Init guis from parameter_root
        self._type_combo = self._parameters['filter_type'].gui()
        self._freq_combo = self._parameters['freq_type'].gui()
        self._filtering_combo = self._parameters['filtering'].gui()
        numerator_label = QtGui.QLabel('Numerator coefficient vector')
        self._numerator_edit = QtGui.QLineEdit()

        denominator_label = QtGui.QLabel('Denominator coefficient vector')
        self._denominator_edit = QtGui.QLineEdit()
        self._fir_windows_combo = self._parameters['fir_windows'].gui()
        self._iir_filters_combo = self._parameters['iir_filters'].gui()

        # Create radio button group
        self._custom_or_existing = QtGui.QButtonGroup()
        self._custom_or_existing.setExclusive(True)

        self._custom_filter_button = QtGui.QRadioButton(
            'Custom filter coefficients')
        self._predefined_filter_button = QtGui.QRadioButton(
            'Predefined filters')
        # Add buttons to group
        self._custom_or_existing.addButton(self._custom_filter_button)
        self._custom_or_existing.addButton(self._predefined_filter_button)

        # Create layouts
        layout = QtGui.QVBoxLayout()

        # filter and frequency type layout
        filt_freq_hlayout = QtGui.QHBoxLayout()
        filt_freq_hlayout.addWidget(self._type_combo)
        filt_freq_hlayout.addWidget(self._freq_combo)
        filt_freq_hlayout.addWidget(self._filtering_combo)

        # Custom parameters layout
        custom_hlayout = QtGui.QHBoxLayout()
        custom_hlayout.addWidget(numerator_label)
        custom_hlayout.addWidget(self._numerator_edit)
        custom_hlayout.addWidget(denominator_label)
        custom_hlayout.addWidget(self._denominator_edit)

        # Create filter parameter layouts
        # FIR filters
        self._fir_len_label = QtGui.QLabel('Filter length')
        self._fir_len = QtGui.QLineEdit()

        self._fir_cutoff_label = QtGui.QLabel('Cutoff frequency')
        self._fir_cutoff = QtGui.QLineEdit()

        self._fir_w1_label = QtGui.QLabel('Beta')
        self._fir_w1 = QtGui.QLineEdit()

        self._fir_w2_label = QtGui.QLabel('Sigma')
        self._fir_w2 = QtGui.QLineEdit()

        fir_gridlayout = QtGui.QGridLayout()
        fir_gridlayout.addWidget(self._fir_len_label, 0, 0)
        fir_gridlayout.addWidget(self._fir_len, 0, 1)
        fir_gridlayout.addWidget(self._fir_cutoff_label, 1, 0)
        fir_gridlayout.addWidget(self._fir_cutoff, 1, 1)
        fir_gridlayout.addWidget(self._fir_w1_label, 2, 0)
        fir_gridlayout.addWidget(self._fir_w1, 2, 1)
        fir_gridlayout.addWidget(self._fir_w2_label, 3, 0)
        fir_gridlayout.addWidget(self._fir_w2, 3, 1)

        # IIR filters
        self._iir_wp_label = QtGui.QLabel('Passband edge frequency')
        self._iir_wp = QtGui.QLineEdit()

        self._iir_ws_label = QtGui.QLabel('Stopband edge frequency')
        self._iir_ws = QtGui.QLineEdit()

        self._iir_gpass_label = QtGui.QLabel('Max loss in passband (dB)')
        self._iir_gpass = QtGui.QLineEdit()

        self._iir_gstop_label = QtGui.QLabel(
            'Min attenuation in stopband (dB)')
        self._iir_gstop = QtGui.QLineEdit()

        iir_gridlayout = QtGui.QGridLayout()
        iir_gridlayout.addWidget(self._iir_wp_label, 0, 0)
        iir_gridlayout.addWidget(self._iir_wp, 0, 1)
        iir_gridlayout.addWidget(self._iir_ws_label, 1, 0)
        iir_gridlayout.addWidget(self._iir_ws, 1, 1)
        iir_gridlayout.addWidget(self._iir_gpass_label, 2, 0)
        iir_gridlayout.addWidget(self._iir_gpass, 2, 1)
        iir_gridlayout.addWidget(self._iir_gstop_label, 3, 0)
        iir_gridlayout.addWidget(self._iir_gstop, 3, 1)

        # Filter spec grid layout
        filter_gridlayout = QtGui.QGridLayout()
        filter_gridlayout.addWidget(self._fir_windows_combo, 0, 0)
        filter_gridlayout.addWidget(self._iir_filters_combo, 0, 1)
        filter_gridlayout.addLayout(fir_gridlayout, 1, 0)
        filter_gridlayout.addLayout(iir_gridlayout, 1, 1)

        # Add to widgets/layouts to main layout
        layout.addLayout(filt_freq_hlayout)
        layout.addWidget(self._custom_filter_button)
        layout.addLayout(custom_hlayout)
        layout.addWidget(self._predefined_filter_button)
        layout.addLayout(filter_gridlayout)
        self.setLayout(layout)

        self._init_gui_from_parameters()

        self._type_combo.editor().currentIndexChanged[int].connect(
            self._type_changed)
        self._custom_or_existing.buttonClicked.connect(self._custom_changed)
        self._fir_windows_combo.editor().currentIndexChanged.connect(
            self._fir_window_changed)
        self._fir_len.textChanged[str].connect(self._fir_len_changed)
        self._fir_cutoff.textChanged[str].connect(
            self._fir_cutoff_changed)
        self._fir_w1.textChanged[str].connect(self._fir_w1_changed)
        self._fir_w2.textChanged[str].connect(self._fir_w2_changed)
        self._iir_wp.textChanged[str].connect(self._iir_wp_changed)
        self._iir_ws.textChanged[str].connect(self._iir_ws_changed)
        self._iir_gpass.textChanged[str].connect(self._iir_gpass_changed)
        self._iir_gstop.textChanged[str].connect(self._iir_gstop_changed)

    def _init_gui_from_parameters(self):
        try:
            self._parameters['custom_filter']
        except:
            self._parameters.set_boolean('custom_filter', value=True)

        if self._parameters['custom_filter'].value:
            self._custom_filter_button.setChecked(True)
        else:
            self._predefined_filter_button.setChecked(True)
        try:
            self._parameters['iir_wp']
        except:
            self._parameters.set_string('iir_wp')
        try:
            self._parameters['iir_ws']
        except:
            self._parameters.set_string('iir_ws')
        try:
            self._parameters['iir_gpass']
        except:
            self._parameters.set_string('iir_gpass')
        try:
            self._parameters['iir_gstop']
        except:
            self._parameters.set_string('iir_gstop')
        try:
            self._parameters['fir_len']
        except:
            self._parameters.set_string('fir_len')
        try:
            self._parameters['fir_cutoff']
        except:
            self._parameters.set_string('fir_cutoff')
        try:
            self._parameters['fir_w1']
        except:
            self._parameters.set_string('fir_w1')
        try:
            self._parameters['fir_w2']
        except:
            self._parameters.set_string('fir_w2')

        self._enable_custom_gui(self._parameters['custom_filter'].value)
        self._iir_wp.setText(self._parameters['iir_wp'].value)
        self._iir_ws.setText(self._parameters['iir_ws'].value)
        self._iir_gpass.setText(self._parameters['iir_gpass'].value)
        self._iir_gstop.setText(self._parameters['iir_gstop'].value)
        self._fir_len.setText(self._parameters['fir_len'].value)
        self._fir_cutoff.setText(self._parameters['fir_cutoff'].value)
        self._fir_w1.setText(self._parameters['fir_w1'].value)
        self._fir_w2.setText(self._parameters['fir_w2'].value)

    def _type_changed(self, index):
        self._enable_custom_gui(self._parameters['custom_filter'].value)

    def _enable_custom_gui(self, state):
        """
        Enable(state==True)/disable(state==False)custom filter parameter
        widgets and disable/enable predefined filter widgets.
        """
        if not state:
            self._numerator_edit.setEnabled(state)
            self._denominator_edit.setEnabled(state)
        elif self._parameters['filter_type'].selected == 'IIR':
            self._numerator_edit.setEnabled(state)
            self._denominator_edit.setEnabled(state)
        else:
            self._numerator_edit.setEnabled(state)
            self._denominator_edit.setEnabled(not state)
        self._freq_combo.setEnabled(not state)
        self._enable_predefined_filters(not state)

    def _enable_predefined_filters(self, state):
        """
        Enable/Disable fir/iir alternatives. If state=False, disable both.
        If state==True and IIR filter is chosen, enable IIR-widgets and
        disable FIR. Otherwise, disable IIR and enable FIR.
        """
        if not state:
            self._enable_fir(state)
            self._enable_iir(state)
        elif self._parameters['filter_type'].selected == 'IIR':
            self._enable_fir(not state)
            self._enable_iir(state)
        else:
            self._enable_fir(state)
            self._enable_iir(not state)

    def _enable_fir(self, state):
        """Enable/disable FIR combo and FIR parameter edits."""
        self._fir_windows_combo.setEnabled(state)
        self._fir_cutoff.setEnabled(state)
        self._fir_cutoff_label.setEnabled(state)
        self._fir_len_label.setEnabled(state)
        self._fir_len.setEnabled(state)
        params = (self._fir_dict[self._parameters['fir_windows'].selected]
                  ['param'])
        if not state or len(params) == 0:
            self._fir_w1_label.setEnabled(False)
            self._fir_w1.setEnabled(False)
            self._fir_w2_label.setEnabled(False)
            self._fir_w2.setEnabled(False)
        elif len(params) == 1:
            self._fir_w1_label.setEnabled(state)
            self._fir_w1.setEnabled(state)
            self._fir_w2_label.setEnabled(not state)
            self._fir_w2.setEnabled(not state)
        else:
            self._fir_w1_label.setEnabled(state)
            self._fir_w1.setEnabled(state)
            self._fir_w2_label.setEnabled(state)
            self._fir_w2.setEnabled(state)

    def _enable_iir(self, state):
        """Enable/disable iir filter combo and iir parameter edits."""
        self._iir_filters_combo.setEnabled(state)
        self._iir_wp_label.setEnabled(state)
        self._iir_wp.setEnabled(state)
        self._iir_ws_label.setEnabled(state)
        self._iir_ws.setEnabled(state)
        self._iir_gpass_label.setEnabled(state)
        self._iir_gpass.setEnabled(state)
        self._iir_gstop.setEnabled(state)
        self._iir_gstop_label.setEnabled(state)

    def _custom_changed(self, button):
        """
        Radiobuttton clicked. Enable/disable custom coefficient edits or
        predefined filter widgets depedning on which button that is
        pressed.
        """
        if button == self._custom_filter_button:
            self._enable_custom_gui(True)
            self._parameters['custom_filter'].value = True
        else:
            self._enable_custom_gui(False)
            self._parameters['custom_filter'].value = False

    def _fir_window_changed(self, index):
        """FIR window function changed."""
        self._enable_custom_gui(self._parameters['custom_filter'].value)
        # Change name on w1 and w2.
        selected_window = self._parameters['fir_windows'].selected
        params = self._fir_dict[selected_window]['param']
        len_param = len(params)
        if len_param == 1:
            self._fir_w1_label.setText(params[0])
        elif len_param == 2:
            self._fir_w1_label.setText(params[0])
            self._fir_w2_label.setText(params[1])
        self._fir_w1.setText('')
        self._fir_w2.setText('')

    def _fir_len_changed(self, text):
        self._parameters['fir_len'].value = str(text)

    def _fir_cutoff_changed(self, text):
        self._parameters['fir_cutoff'].value = str(text)

    def _fir_w1_changed(self, text):
        self._parameters['fir_w1'].value = str(text)

    def _fir_w2_changed(self, text):
        self._parameters['fir_w2'].value = str(text)

    def _iir_wp_changed(self, text):
        self._parameters['iir_wp'].value = str(text)

    def _iir_ws_changed(self, text):
        self._parameters['iir_ws'].value = str(text)

    def _iir_gpass_changed(self, text):
        self._parameters['iir_gpass'].value = str(text)

    def _iir_gstop_changed(self, text):
        self._parameters['iir_gstop'].value = str(text)


# New filter node

def map_adaf_to_signal_list(datafile):
    key_map = []
    if datafile.is_valid():
        for system_name, system in datafile.sys.items():
            for raster_name, raster in system.items():
                for signal_name in raster.keys():
                    key_map.append((system_name, raster_name, signal_name))
    return key_map


class FilterADAFsWithPlot(synode.Node):
    """
    Filter ADAFs with a specified filter.

    Both IIR filters and FIR filters can be selected. The filter
    can be a forward or forward-backward filter. The resulting filter
    design and an example of filtered data can be inspected
    in real-time within the node's GUI.

    The FIR filter windows that can be used are:
        - Bartlett-Hann_
        - Bartlett_
        - Blackman_
        - Blackman-Harris_
        - Bohman_
        - Boxcar_
        - Dolph-Chebyshev_
        - `Flat top`_
        - Gaussian_
        - `Generalized Gaussian`_
        - Hamming_
        - Hann_
        - Kaiser_
        - Nuttall_
        - Parzen_
        - Slepian_
        - Triangular_

    .. _Bartlett-Hann: http://en.wikipedia.org/wiki/Window_function#Bartlett.E2.80.93Hann_window
    .. _Bartlett: http://en.wikipedia.org/wiki/Window_function#Triangular_window
    .. _Blackman: http://en.wikipedia.org/wiki/Window_function#Blackman_windows
    .. _Blackman-Harris: http://en.wikipedia.org/wiki/Window_function#Blackman.E2.80.93Harris_window
    .. _Bohman: http://en.wikipedia.org/wiki/Window_function#Cosine_window
    .. _Boxcar: http://en.wikipedia.org/wiki/Window_function#Rectangular_window
    .. _Dolph-Chebyshev: http://en.wikipedia.org/wiki/Window_function#Dolph.E2.80.93Chebyshev_window
    .. _`Flat top`: http://en.wikipedia.org/wiki/Window_function#Flat_top_window
    .. _Gaussian: http://en.wikipedia.org/wiki/Window_function#Gaussian_window
    .. _`Generalized Gaussian`: http://en.wikipedia.org/wiki/Window_function#Gaussian_window
    .. _Hamming: http://en.wikipedia.org/wiki/Window_function#Hamming_window
    .. _Hann: http://en.wikipedia.org/wiki/Window_function#Hann_.28Hanning.29_window
    .. _Kaiser: http://en.wikipedia.org/wiki/Kaiser_window
    .. _Nuttall: http://en.wikipedia.org/wiki/Window_function#Nuttall_window.2C_continuous_first_derivative
    .. _Parzen: http://en.wikipedia.org/wiki/Window_function#Parzen_window
    .. _Slepian: http://en.wikipedia.org/wiki/Window_function#DPSS_or_Slepian_window
    .. _Triangular: http://en.wikipedia.org/wiki/Window_function#Triangular_window

    The IIR filter functions supported are:
        - Butterworth_
        - `Chebyshev 1`_
        - `Chebyshev 2`_
        - Elliptic_

    .. _Butterworth: http://en.wikipedia.org/wiki/Butterworth_filter
    .. _`Chebyshev 1`: http://en.wikipedia.org/wiki/Chebyshev_filter#Type_I_Chebyshev_filters
    .. _`Chebyshev 2`: http://en.wikipedia.org/wiki/Chebyshev_filter#Type_II_Chebyshev_filters
    .. _Elliptic: http://en.wikipedia.org/wiki/Elliptic_filter

    :Inputs:  ADAFs
    :Outputs: ADAFs
    :Configuration: Choose FIR or IIR filter and specify filter coefficients or
                    the function/window to calculate them.
    :Opposite node:
    :Ref. nodes:
    """

    author = ('Helena Olen <helena.olen@combine.se>, '
              'Benedikt Ziegler <benedikt.ziegler@combine.se>')
    copyright = '(c) 2013, 2016 Combine AB'
    description = 'Filter ADAF data.'
    name = 'Filter ADAFs'
    nodeid = 'org.sysess.sympathy.data.adaf.filteradafswithplot'
    version = '1.1'
    icon = 'filter_adaf.svg'
    tags = Tags(Tag.Analysis.SignalProcessing)

    inputs = Ports([Port.ADAFs('Input ADAFs', name='port1')])
    outputs = Ports([Port.ADAFs(
        'Output ADAFs with filter applied', name='port1')])

    parameters = synode.parameters()
    parameters.set_list(
        'filter_type',
        plist=['IIR', 'FIR'],
        label='Filter type',
        value=[0],
        description='Combo of filter types',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'freq_type',
        plist=['Lowpass', 'Highpass', 'Bandpass', 'Bandstop'],
        value=[0],
        label='Frequency pass type',
        description='Frequency pass type required for the FIR filter.',
        editor=synode.Util.combo_editor().value())

    # fir_page = parameters.create_page('fir_page', label='FIR')
    parameters.set_list(
        'fir_windows',
        plist=sorted(get_fir_window_dict().keys()),
        value=[9],
        label='Filter windows',
        description='Filter windows for FIR filter',
        editor=synode.Util.combo_editor().value())
    parameters.set_integer(
        'fir_len',
        value=11,
        label='Filter length',
        description='Length of the filter',
        editor=synode.Util.lineedit_editor(placeholder='11').value())
    parameters.set_string(
        'fir_cutoff',
        label='Cutoff frequency',
        value='0.2',
        description="Cutoff frequency of filter (expressed in the same units "
                    "as `nyq`) OR an array of cutoff frequencies (that is, "
                    "band edges). In the latter case, the frequencies in "
                    "`cutoff` should be positive and monotonically "
                    "increasing between 0 and `nyq`. The values 0 and `nyq` "
                    "must not be included in `cutoff`.",
        editor=synode.Util.lineedit_editor(placeholder='0.2, ..').value())

    parameters.set_float(
        'fir_w1',
        label='Beta',
        value=1.0,
        description='Filter specific parameter. Check the help.',
        editor=synode.Util.lineedit_editor(placeholder='1.0').value())
    parameters.set_float(
        'fir_w2',
        label='Sigma',
        value=1.0,
        description='Filter specific parameter. Check the help.',
        editor=synode.Util.lineedit_editor(placeholder='1.0').value())

    # iir_page = parameters.create_page('iir_page', label='IIR')
    parameters.set_list(
        'iir_filters',
        plist=sorted(get_iir_filter_dict().keys()),
        value=[0],
        label='Filter designs',
        description='IIR filters',
        editor=synode.Util.combo_editor().value())
    parameters.set_string(
        'iir_wp',
        label='Passband edge frequency',
        value='0.2',
        description='Passband edge frequency',
        editor=synode.Util.lineedit_editor(
            placeholder='0.2 or [0.2, 0.3]').value())
    parameters.set_string(
        'iir_ws',
        label='Stopband edge frequency',
        value='0.4',
        description='Stopband edge frequency',
        editor=synode.Util.lineedit_editor(
            placeholder='0.4 or [0.1, 0.4]').value())
    parameters.set_float(
        'iir_gpass',
        label='Max loss in passband (dB)',
        value=1.0,
        description='Max loss in the passband (dB)',
        editor=synode.Util.lineedit_editor(placeholder='2.0').value())
    parameters.set_float(
        'iir_gstop',
        label='Min attenuation in stopband (dB)',
        value=10.0,
        description='Min attenuation in the stopband (dB)',
        editor=synode.Util.lineedit_editor(placeholder='1.0').value())

    parameters.set_list(
        'filtering',
        plist=sorted(get_filtering_dict().keys()),
        value=[1],
        label='Filtering',
        description='Filtering types',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'signal_select',
        label='Select Signal',
        description='Select a signal',
        editor=synode.Util.combo_editor().value())
    parameters.set_boolean(
        'auto_plot',
        label='Auto refresh',
        description='Automatically refresh the plot')

    def exec_parameter_view(self, node_context):
        return FilterADAFsPlotWidget(node_context)

    def execute(self, node_context):
        input_list = node_context.input['port1']
        output_list = node_context.output['port1']
        number_of_items = len(input_list)

        for idx, adaffile in enumerate(input_list):
            outadaffile = output_list.create()
            filter_signals(adaffile, outadaffile, node_context.parameters)
            output_list.append(outadaffile)
            self.set_progress(100.0 * (idx + 1) / number_of_items)


def form_layout_factory(parameter_widgets, fixed_width=None,
                        add_stretch=False):
    """
    A factory creating a 2 column (label, editor) form layout.

    Parameters
    ----------
    parameter_widgets : [tuple]
        A list of tuples, where each tuple contains at least the widget.
        Optionally, a QLabel can be defined which would overwrite any existing
        label_widget of the main widget.
        If a label should be skipped but the editor should be aligned in the
        left column one can input an empty string.

    fixed_width : int, optional
        Define a fixed width for the editor column in pixels.

    add_stretch : bool, optional
        If a stretch should be added to the end of the layout.

    Returns
    -------
    layout : QtGui.QVBoxLayout
    """
    if fixed_width is not None and fixed_width < 0:
        fixed_width = None

    layout = QtGui.QGridLayout()
    for i, item in enumerate(parameter_widgets):
        # get label and editor widget
        widget = item[0]
        editor = getattr(widget, 'editor', None)
        label = getattr(widget, 'label_widget', None)

        # override label with a given label string or QLabel
        if len(item) > 1:
            given_label = item[1]
            if isinstance(given_label, six.string_types):
                label = QtGui.QLabel(six.text_type(label))
            elif isinstance(given_label, QtGui.QLabel):
                label = given_label
            # assign editor to the right column
            if editor is None:
                editor = widget

        if label and editor:
            # add the label and editor to the layout
            label_widget = label()
            editor_widget = editor()
            layout.addWidget(label_widget, i, 0)
            layout.addWidget(editor_widget, i, 1)
            if fixed_width:
                editor_widget.setMaximumWidth(fixed_width)
        else:
            # add the given widget to the layout
            hlayout = QtGui.QHBoxLayout()
            hlayout.setContentsMargins(0, 0, 0, 0)
            hlayout.addWidget(widget)
            layout.addLayout(hlayout, i, 0, 1, 2)

    outer_layout = QtGui.QVBoxLayout()
    outer_layout.addLayout(layout)
    if add_stretch:
        outer_layout.addStretch()
    return outer_layout


_scipy_filter_links = None


def scipy_filter_links():
    global _scipy_filter_links
    if _scipy_filter_links is None:
        from scipy import __version__ as scipy_version
        _scipy_filter_links = {
            'FIR': 'http://docs.scipy.org/doc/scipy-{}'
            '/reference/generated/scipy.signal.firwin.html'.format(
                scipy_version),
            'IIR': 'http://docs.scipy.org/doc/scipy-{}'
            '/reference/generated/scipy.signal.iirdesign.html'.format(
                scipy_version)}
    return _scipy_filter_links


class FilterADAFsPlotWidget(ParameterView):
    def __init__(self, node_context, parent=None):
        super(FilterADAFsPlotWidget, self).__init__(parent=parent)
        self._node_context = node_context
        self._parameters = node_context.parameters
        self._datafile = node_context.input['port1']

        self._status_message = ''
        self._is_valid = True

        self._init_gui()

    def resizeEvent(self, event):
        super(FilterADAFsPlotWidget, self).resizeEvent(event)
        self.figure.tight_layout()

    def _init_gui(self):
        self._fir_dict = get_fir_window_dict()

        # Init guis from parameter_root
        # global parameters
        self._filtering_combo = self._parameters['filtering'].gui()
        self._freq_combo = self._parameters['freq_type'].gui()

        # FIR specific parameters
        self._fir_windows_combo = self._parameters['fir_windows'].gui()
        # FIR filters
        self._fir_len = self._parameters['fir_len'].gui()
        self._fir_cutoff = self._parameters['fir_cutoff'].gui()
        self._fir_w1 = self._parameters['fir_w1'].gui()
        self._fir_w2 = self._parameters['fir_w2'].gui()

        # FIR layout
        fir_layout = form_layout_factory([(self._fir_windows_combo, ),
                                          (self._fir_len, ),
                                          (self._fir_cutoff, ),
                                          (self._fir_w1, ),
                                          (self._fir_w2, )],
                                         fixed_width=150,
                                         add_stretch=True)

        # IIR specific parameters
        self._iir_filters_combo = self._parameters['iir_filters'].gui()
        # IIR filters
        self._iir_wp = self._parameters['iir_wp'].gui()
        self._iir_ws = self._parameters['iir_ws'].gui()
        self._iir_gpass = self._parameters['iir_gpass'].gui()
        self._iir_gstop = self._parameters['iir_gstop'].gui()

        # IIR layout
        iir_layout = form_layout_factory([(self._iir_filters_combo, ),
                                          (self._iir_wp, ),
                                          (self._iir_ws, ),
                                          (self._iir_gpass, ),
                                          (self._iir_gstop, )],
                                         fixed_width=150,
                                         add_stretch=True)

        # Filter Tabs
        self._filter_tabs = QtGui.QTabWidget()
        iir_tab = QtGui.QWidget()
        iir_tab.setLayout(iir_layout)
        fir_tab = QtGui.QWidget()
        fir_tab.setLayout(fir_layout)

        value_names = self._parameters['filter_type'].list
        self._filter_tabs.addTab(iir_tab, value_names[0])
        self._filter_tabs.addTab(fir_tab, value_names[1])
        self._filter_tabs.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                                        QtGui.QSizePolicy.Minimum)

        # Filter type layout
        filter_type_groupbox = QtGui.QGroupBox('Filter Options')
        filter_type_layout = form_layout_factory([(self._filtering_combo, ),
                                                  (self._freq_combo, )],
                                                 fixed_width=150)
        filter_type_groupbox.setLayout(filter_type_layout)
        filter_type_groupbox.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                                           QtGui.QSizePolicy.Minimum)

        # Figure related parameters
        self._plot_update = self._parameters['auto_plot'].gui()
        self._plot_update_button = QtGui.QPushButton('Refresh')
        self.select_signal = self._parameters['signal_select'].gui()

        plot_button_layout = QtGui.QHBoxLayout()
        plot_button_layout.addWidget(self._plot_update)
        plot_button_layout.addWidget(self._plot_update_button)

        plot_group_layout = QtGui.QVBoxLayout()
        plot_group_layout.addLayout(plot_button_layout)
        plot_group_layout.addWidget(self.select_signal)

        plot_groupbox = QtGui.QGroupBox('Plot Options')
        plot_groupbox.setLayout(plot_group_layout)

        self.figure = Figure(
            facecolor=self.palette().color(QtGui.QPalette.Window).name())
        self.canvas = FigureCanvas(self.figure)
        policy = QtGui.QSizePolicy()
        policy.setHorizontalStretch(1)
        policy.setVerticalStretch(1)
        policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        policy.setVerticalPolicy(QtGui.QSizePolicy.Expanding)
        self.canvas.setSizePolicy(policy)
        self.canvas.setMinimumWidth(400)

        # Figure Layout
        plot_vlayout = QtGui.QVBoxLayout()
        plot_vlayout.addWidget(self.canvas)

        # Default navigation toolbar for matplotlib
        self.mpl_toolbar = NavigationToolbar(self.canvas, self)
        plot_vlayout.addWidget(self.mpl_toolbar)

        # Create parameter layout
        parameter_layout = QtGui.QVBoxLayout()
        parameter_layout.addWidget(self._filter_tabs)
        parameter_layout.addWidget(filter_type_groupbox)
        parameter_layout.addWidget(plot_groupbox)
        parameter_layout.addStretch()

        # Create global layout
        vline = QtGui.QFrame()
        vline.setFrameShape(QtGui.QFrame.VLine)
        vline.setFrameShadow(QtGui.QFrame.Sunken)

        layout = QtGui.QHBoxLayout()
        layout.addLayout(parameter_layout)
        layout.addWidget(vline)
        layout.addLayout(plot_vlayout)

        self.setLayout(layout)

        self._setup_plot()

        # Connect signals
        self._filter_tabs.currentChanged.connect(self._type_changed)

        self._fir_windows_combo.editor().currentIndexChanged.connect(
            self._fir_window_changed)
        self._fir_len.editor().valueChanged.connect(self._fir_len_changed)
        self._fir_cutoff.editor().valueChanged.connect(
            self._fir_cutoff_changed)
        self._fir_w1.editor().valueChanged.connect(self._fir_w1_changed)
        self._fir_w2.editor().valueChanged.connect(self._fir_w2_changed)

        self._iir_filters_combo.editor().currentIndexChanged.connect(
            self._irr_filter_changed)
        self._iir_wp.editor().valueChanged.connect(self._iir_wp_changed)
        self._iir_ws.editor().valueChanged.connect(self._iir_ws_changed)
        self._iir_gpass.editor().valueChanged.connect(self._irr_gpass_changed)
        self._iir_gstop.editor().valueChanged.connect(self._irr_gstop_changed)

        self._freq_combo.editor().valueChanged.connect(
            self._freq_type_changed)
        self._filtering_combo.editor().valueChanged.connect(self._plot)

        self._plot_update.valueChanged[bool].connect(self._enable_plot_button)
        self._plot_update_button.clicked[bool].connect(self.refresh_plot)
        self.select_signal.editor().currentIndexChanged.connect(
            self.refresh_plot)

        self._init_gui_from_parameters()

    def _init_gui_from_parameters(self):
        self._plot_update_button.setEnabled(
            not self._parameters['auto_plot'].value)
        self._populate_signal_combobox()
        self._filter_tabs.setCurrentIndex(
            self._parameters['filter_type'].value[0])
        self._freq_combo.editor().setEnabled(
            self._parameters['filter_type'].value[0])
        self._fir_window_changed()
        self._plot()

    def _populate_signal_combobox(self):
        if self._datafile.is_valid() and len(self._datafile) > 0:
            self.signal_map = map_adaf_to_signal_list(self._datafile[0])
        else:
            self.signal_map = []
        self.select_signal.editor().clear()
        items = ['{} ({}/{})'.format(
            line[2], line[0], line[1]) for line in self.signal_map]
        self.select_signal.editor().addItems(items)
        self.select_signal.editor().setCurrentIndex(0)

    @property
    def status(self):
        return self._status_message

    @property
    def valid(self):
        return self._is_valid

    def clean_status(self):
        self._is_valid = True
        self._status_message = ''

    def validate_parameters(self):
        """Cross validate parameters"""
        parameters = self._parameters
        filter_type = parameters['filter_type'].selected
        if filter_type == 'IIR':
            wp, ws, gpass, gstop, ftype = get_iir_filter_parameters(parameters)
            wp_is_seq = isinstance(wp, collections.Sequence)
            ws_is_seq = isinstance(ws, collections.Sequence)
            both_are_seq = wp_is_seq and ws_is_seq
            if (wp_is_seq and not ws_is_seq) or (ws_is_seq and not wp_is_seq):
                message = ('Both, <b>Passband</b> and <b>Stopband</b> need '
                           'to be either both floating point numbers or both '
                           'a sequence of <b>two</b> floating point '
                           'numbers.')
                self._is_valid = False
            elif both_are_seq and (len(wp) != 2 or len(ws) != 2):
                message = ('Both, <b>Passband</b> and <b>Stopband</b> need '
                           'to be length 2, e.g.: "0.2, 0.3" and "0.1, 0.4"')
                self._is_valid = False
            elif (both_are_seq and (len(wp) == 2 and len(ws) == 2) and not
                    ((min(ws) < min(wp) and max(wp) < max(ws)) or
                         (min(ws) > min(wp) and max(wp) > max(ws)))):
                message = ('Either the <b>Passband</b> has to lie within the '
                           '<b>Stopband</b> or vice versa.')
                self._is_valid = False
            elif (both_are_seq and (len(wp) == 2 and len(ws) == 2) and not
                    (ws[0] < ws[1])):
                message = ('The second <b>Stopband</b> value must be greater '
                           'than the first one! E.g. "0.1, 0.4"')
                self._is_valid = False
            elif (both_are_seq and (len(wp) == 2 and len(ws) == 2) and not
                    (wp[0] < wp[1])):
                message = ('The second <b>Passband</b> value must be greater '
                           'than the first one! E.g. "0.2, 0.3"')
                self._is_valid = False
            elif gpass >= gstop:
                message = ('The <b>Max loss ...</b> must be larger '
                           'than the <b>Min attenuation ..</b>!')
                self._is_valid = False
            else:
                message = None
            if not self._is_valid:
                if message is not None:
                    self._status_message = self.build_error_message(message)
                self.status_changed.emit()
        # currently no cross validation of FIR filter parameters
        return self._is_valid

    def _type_changed(self, index):
        idx = self._filter_tabs.currentIndex()
        self._parameters['filter_type'].value = [idx]
        self._freq_combo.editor().setEnabled(idx == 1)
        self._plot()

    def _freq_type_changed(self):
        self.clean_status()
        self._plot()

    def _fir_window_changed(self):
        """FIR window function changed."""
        def set_visibility_widgets(widgets, states):
            for widget, state in zip(widgets, states):
                widget.editor().setVisible(state)
                widget.label_widget().setVisible(state)

        # Change name on w1 and w2.
        selected_window = self._parameters['fir_windows'].selected
        params = self._fir_dict[selected_window]['param']
        len_param = len(params)
        fir_w1_label = self._fir_w1.label_widget()
        fir_w2_label = self._fir_w2.label_widget()
        if len_param == 0:
            fir_w1_label.setText('')
            fir_w2_label.setText('')
            set_visibility_widgets([self._fir_w1, self._fir_w2],
                                   [False, False])
        elif len_param == 1:
            fir_w1_label.setText(params[0])
            fir_w2_label.setText('')
            set_visibility_widgets([self._fir_w1, self._fir_w2],
                                   [True, False])
        elif len_param == 2:
            fir_w1_label.setText(params[0])
            fir_w2_label.setText(params[1])
            set_visibility_widgets([self._fir_w1, self._fir_w2],
                                   [True, True])
        self.clean_status()
        self._plot()

    def _fir_len_changed(self):
        editor = self._fir_len.editor()
        self.validate_parameter('fir_len', editor, func=int)

    def _fir_cutoff_changed(self):
        text = self._parameters['fir_cutoff'].value
        editor = self._fir_cutoff.editor()

        validated = True
        message = ''
        try:
            value = ast.literal_eval(text)
            if isinstance(value, (int, float)) and value <= 0:
                validated = False
                message = '<i>{}</i>!'.format(text)
            elif (isinstance(value, collections.Sequence) and
                      any(map(lambda i: i <= 0 or i >= 1, value))):
                validated = False
                message = 'Frequencies must be greater than 0 and less than 1!'
            elif (isinstance(value, collections.Sequence) and
                    np.any(np.diff(value) <= 0)):
                validated = False
                message = 'The frequencies must be strictly increasing!'
        except (SyntaxError, ValueError):
            validated = False
            message = ('Mal-formatted input. Please enter only comma '
                       'separated floats in the interval ]0, 1[!')
        except Exception as e:
            validated = False
            message = six.text_type(e)

        label = self._parameters['fir_cutoff'].label
        message = 'Invalid <b>{}</b>: {}'.format(label, message)
        self.handle_validation_state('fir_cutoff', validated, editor, message)
        if validated:
            self._plot()

    def _fir_w1_changed(self):
        editor = self._fir_w1.editor()
        self.validate_parameter('fir_w1', editor, func=float)

    def _fir_w2_changed(self):
        editor = self._fir_w2.editor()
        self.validate_parameter('fir_w2', editor, func=float)

    def _irr_filter_changed(self):
        self.clean_status()
        self._plot()

    def _iir_wp_changed(self):
        editor = self._iir_wp.editor()
        self.validate_irr_edge_frequencies('iir_wp', editor)

    def _iir_ws_changed(self):
        editor = self._iir_ws.editor()
        self.validate_irr_edge_frequencies('iir_ws', editor)

    def _irr_gpass_changed(self):
        editor = self._iir_gpass.editor()
        self.validate_parameter('iir_gpass', editor, func=float)

    def _irr_gstop_changed(self):
        editor = self._iir_gstop.editor()
        self.validate_parameter('iir_gstop', editor, func=float)

    def validate_irr_edge_frequencies(self, parameter, editor):
        text = self._parameters[parameter].value

        validated = True
        message = ''
        try:
            value = ast.literal_eval(text)
            if isinstance(value, (list, tuple)):
                out_of_limits = any([i <= 0 or i >= 1 for i in value])
                if len(value) != 2 or out_of_limits:
                    validated = False
            elif (isinstance(value, (int, float)) and
                    (value <= 0 or value >= 1.)):
                validated = False
        except (SyntaxError, ValueError):
            validated = False
            message = ('Mal-formatted input! Only floating point numbers or '
                       'comma separated floating point numbers are allowed!')
        except Exception as e:
            validated = False
            message = six.text_type(e)

        label = self._parameters['fir_cutoff'].label
        message = 'Invalid <b>{}</b>: {}'.format(label, message)
        self.handle_validation_state(parameter, validated, editor, message)

    def validate_parameter(self, parameter, editor, func=float):
        text = self._parameters[parameter].value

        validated = True
        message = ''
        try:
            value = func(text)
            if value <= 0.:
                validated = False
        except ValueError as e:
            validated = False
            message = six.text_type(e)

        self.handle_validation_state(parameter, validated, editor, message)

    def handle_validation_state(self, parameter, validated, editor,
                                message=''):
        text = self._parameters[parameter].value

        if not validated and message == '':
            label = self._parameters[parameter].label
            message = ('Invalid <b>{}</b>: <i>{}</i>!'
                       ''.format(label, text))

        self._status_message = self.build_error_message(message)
        self._is_valid = validated
        self.set_widgets_state_color(editor, validated)

        self.status_changed.emit()
        if validated:
            self._plot()

    @staticmethod
    def set_widgets_state_color(widget, state):
        color = QtGui.QColor(0, 0, 0, 0)
        if not state:
            color = QtCore.Qt.red
        if widget is not None:
            palette = widget.palette()
            palette.setColor(widget.backgroundRole(), color)
            widget.setPalette(palette)

    def _enable_plot_button(self, state):
        # disable refresh button
        self._plot_update_button.setEnabled(not state)
        self._plot()

    def refresh_plot(self):
        self.mpl_toolbar.update()
        self._plot(update_data=True)

    def _plot(self, update_data=False):
        if not self.validate_parameters():
            return

        b, a = None, None
        try:
            with warnings.catch_warnings(record=True) as w, capture_print() \
                    as cp:
                b, a = generate_filter(self._parameters)
                if len(w):
                    self._is_valid = False
                    message = six.text_type(w.pop(0).message)
                    self._status_message = self.build_error_message(message)
                elif len(cp):
                    self._is_valid = False
                    message = self.build_error_message(
                        '\n'.join([i for i in cp]))
                    self._status_message = message
                else:
                    self._is_valid = True
                    self._status_message = ''
        except OverflowError:
            self._is_valid = False
            message = 'The value is too large.'
            self._status_message = self.build_error_message(message)
        except ValueError as e:
            self._is_valid = False
            message = self.build_error_message(six.text_type(e))
            self._status_message = message
        except (SyntaxError, IndexError) as e:
            self._is_valid = False
            message = self.build_error_message(six.text_type(e))
            self._status_message = message

        self.status_changed.emit()

        if b is not None and a is not None:
            if self._parameters['auto_plot'].value or update_data:
                self._update_data_plot(b, a)
            self._update_filter_plot(b, a)
            self.figure.tight_layout()
            self.canvas.draw_idle()

    def build_error_message(self, base_message):
        filter_type = self._parameters['filter_type'].selected
        filter_link = scipy_filter_links()[filter_type]
        message = ('<p>{}</p>'
                   '<p>See the {} filter documentation for valid input '
                   'parameter: <a href={}>{}</a></p>'
                   ''.format(base_message, filter_type, filter_link,
                             filter_link))
        return message

    def _update_data_plot(self, b, a):
        self.filtered_signal_line.set_visible(self._is_valid)
        if not self._is_valid:
            return
        # get timeseries
        ts = self._get_current_signal()
        if ts is None:
            return
        filtering_dict = get_filtering_dict()
        selected_filter = self._parameters['filtering'].selected
        try:
            filtered_signal = filtering_dict[selected_filter](b, a, ts)
        except ValueError as e:
            self._is_valid = True
            message = self.build_error_message(six.text_type(e))
            self._status_message = message
            self.status_changed.emit()
            return

        x = np.arange(len(ts))

        self.original_signal_line.set_data(x, ts)
        self.filtered_signal_line.set_data(x, filtered_signal)

        self.data_axes.set_xlim(min(x), max(x))
        self.data_axes.set_ylim(min([min(ts), min(filtered_signal)]),
                                max([max(ts), max(filtered_signal)]))

        self.data_axes.autoscale_view(True, True, True)

    def _update_filter_plot(self, b, a):
        self.filter_magnitude_line.set_visible(self._is_valid)
        self.filter_phase_line.set_visible(self._is_valid)
        if self._is_valid:
            w, h = signal.freqz(b, a)  # possibly add worN here
            w /= w.max()
            angles = np.unwrap(np.arctan2(h.imag, h.real))

            with warnings.catch_warnings(record=True) as warn:
                self.filter_magnitude_line.set_data(w,
                                                    20 * np.log(np.abs(h)))

            if len(warn):
                self._status_message = six.text_type(warn[-1].message)
                self._is_valid = True
                self.status_changed.emit()

            self.filter_phase_line.set_data(w, angles)

        # following is need to update the data limits
        # and view after updating line data
        for ax in [self.filter_axes_magnitude, self.filter_axes_phase]:
            ax.relim()
            ax.autoscale_view(True, True, True)

    def _setup_plot(self):
        self.filter_axes_magnitude = self.figure.add_subplot(211)
        self.filter_axes_phase = self.filter_axes_magnitude.twinx()
        self.data_axes = self.figure.add_subplot(212)

        # setup filter subplot
        self.filter_axes_magnitude.set_ylabel('Amplitude [dB]', color='b')
        self.filter_axes_phase.set_ylabel('Phase', color='g')
        self.filter_axes_magnitude.set_xlabel('Normalized Frequency ['
                                              '$\\times \pi$ '
                                              'rad/sample]')

        # setup data subplot
        self.data_axes.set_ylabel('Data')

        self.original_signal_line, = self.data_axes.plot(
            [], 'ro', markersize=2, label='Data')
        self.filtered_signal_line, = self.data_axes.plot(
            [], 'b', label='Filtered Data')

        self.filter_magnitude_line, = self.filter_axes_magnitude.plot(
            [], [], 'b', label='Amplitude')
        self.filter_phase_line, = self.filter_axes_phase.plot(
            [], [], 'g', label='Phase')

    def _get_current_signal(self):
        # could possibly be simplified
        current_selected_idx = self._parameters['signal_select'].value[0]
        if self.signal_map:
            system, raster, signal = self.signal_map[current_selected_idx]
            try:
                raster = self._datafile[0].sys[system][raster].to_table()
                ts = raster.get_column_to_array(signal)
            except KeyError:
                ts = None
        else:
            ts = None
        return ts
