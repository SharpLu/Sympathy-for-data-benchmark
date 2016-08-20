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
In the standard library there exist four nodes which exports data from
:ref:`ADAF` to :ref:`Table`. Together with nodes for exportation in the
reversed direction, :ref:`Table to ADAF`, one can make transitions back and
forth between the two internal data types.

For all four nodes one has to specify which container in the incoming
ADAF/ADAFs that is going to be exported. Selectable containers are metadata,
results and timeseries, see :ref:`ADAF` for further information.

For two of the nodes, :ref:`ADAF to Tables` and
:ref:`Elementwise ADAFs to Tables`, the full content of the specified container
in the ADAF/ADAFs is exported. At selection of the timeseries container all
raster are exported and each raster will generate an outgoing Table.

While for the other two nodes, :ref:`ADAF to Table`
and :ref:`ADAFs to Tables`, the full content of the container is only exported
if the metadata or the results container is selected. For the time-resolved
data one has to select a specific raster that is going to be exported.

The exported timebases will, in the Tables, be given the name of their
corrspondning rasters. It is important to know that if the name of the
timebases already exists among the names of the timeseries signals,
the timebases will not be exported to the Table.
"""
import warnings

from sylib.widget_library import FilterListView
from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui') # noqa
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.platform.exceptions import SyDataError


def write_adaf_to_table(export_group, adaffile, tablefile, tb_name=None,
                        tb_col_name=''):
    """Write the selected export group to a table."""
    if export_group == 'Meta':
        tablefile.update(adaffile.meta.to_table())
    elif export_group == 'Result':
        tablefile.update(adaffile.res.to_table())
    elif export_group == 'Time series':
        system_name, raster_name = get_system_raster_names(tb_name)
        if system_name in adaffile.sys:
            system = adaffile.sys[system_name]
            if raster_name in system:
                raster = system[raster_name]
            else:
                raise SyDataError(
                    'The selected raster does not exist in incoming ADAF')
        else:
            raise SyDataError(
                'The selected system does not exist in incoming ADAF')

        if not tb_col_name:
            tb_col_name = raster_name
        # Check if tb_col_name already exists in Table
        if tb_col_name in raster.keys():
            message = ('A column with the entered time basis column name '
                       'do already exist. Time basis will not be included '
                       'in the outgoing Table.')
            warnings.warn(message)

        tablefile.update(raster.to_table(tb_col_name))

    source = adaffile.source_id()
    if source:
        tablefile.set_name(source)


def get_system_raster_names(tb_path):
    """Split time basis path, system_name/raster_name/ and the return the
    system_name and the raster_name.
    """
    return tuple(tb_path.split('/')[:2])


def get_raster_name(tb_path):
    """Return the raster name from given time basis path."""
    system_name, raster_name = get_system_raster_names(tb_path)
    return raster_name


def get_rasters_from_adaf(adafdata):
    """Return a list with the paths to all rasters in an adaf,
    system_name/raster_name/
    """
    if not adafdata:
        return []
    return ['{0}/{1}/'.format(system, raster)
            for system, rastergroup in adafdata.sys.items()
            for raster in rastergroup.keys()]


def check_tb_consistence_and_clear(adafdata, parameter_root):
    """Check whether timeseries and timebasis have changed since parameter
    view last was executed. If yes, clear lists.
    """
    rasters_file = get_rasters_from_adaf(adafdata)
    parameter_root['tb'].list = rasters_file


class ADAF2TableSuperNode(object):
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'adaf2table.svg'
    tags = Tags(Tag.DataProcessing.Convert)


def base_parameters():
    parameters = synode.parameters()
    parameters.set_list(
        'export_group', ['Meta', 'Result', 'Time series'],
        label='Export group', description='Group to export.', value=[0],
        editor=synode.Util.combo_editor().value())

    tb_editor = synode.Util.list_editor()
    tb_editor.set_attribute('filter', True)
    ts_editor = synode.Util.list_editor()
    ts_editor.set_attribute('filter', True)
    ts_editor.set_attribute('selection', 'multi')
    parameters.set_list('tb',
                        label="Time basis raster",
                        value=[],
                        editor=tb_editor.value())

    parameters.set_string('tb_col_name',
                          label='Time basis column name',
                          description="What column name should the time basis "
                                      "have in the resulting table? Leave "
                                      "blank to use the raster's name.",
                          value='')
    return parameters


def simple_base_parameters():
    parameters = synode.parameters()
    parameters.set_list(
        'export_group', ['Meta', 'Result', 'Time series'],
        label='Export group', description='Group to export.', value=[0],
        editor=synode.Util.combo_editor().value())
    return parameters


class ADAF2Table(ADAF2TableSuperNode, synode.Node):
    """
    Exportation of specified data in ADAF to Table. The data can either be
    the a raster from the timeseries container or the full content of either
    the metadata or the results containers.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : Table
            Table with the content of a specified group in the incoming ADAF.
    :Configuration:
        **Export group**
            Specify group in the incoming ADAF which will
            be exported.
        **Time basis raster**
            Specify the raster among the time resolved data which
            will be exported.
        **Time basis column name**
            Specify the name for the time basis column in the
            outgoing Table. The default name is the name of the
            elected raster.
    :Opposite node: :ref:`Table to ADAF`
    :Ref. nodes: :ref:`ADAFs to Tables`
    """

    name = 'ADAF to Table'
    description = ('Export of data from an ADAF to a Table.')
    nodeid = 'org.sysess.sympathy.data.adaf.adaf2table'

    inputs = Ports([Port.ADAF('Input ADAF', name='port1')])
    outputs = Ports([Port.Table(
        'Data from incoming ADAF converted to Table', name='port1')])

    parameters = base_parameters()

    def adjust_parameters(self, node_context):
        if node_context.input['port1'].is_valid():
            adafdata = node_context.input['port1']
        else:
            adafdata = None
        check_tb_consistence_and_clear(adafdata, node_context.parameters)

        return node_context

    def exec_parameter_view(self, node_context):
        if node_context.input['port1'].is_valid():
            adafdata = node_context.input['port1']
        else:
            adafdata = None
        return ADAF2TableWidget(node_context.parameters, adafdata)

    def execute(self, node_context):
        group_name = node_context.parameters['export_group'].selected

        adaffile = node_context.input['port1']
        tablefile = node_context.output['port1']
        try:
            tb_name = node_context.parameters['tb'].selected
        except:
            tb_name = None
        try:
            tb_col_name = node_context.parameters['tb_col_name'].value
        except:
            tb_col_name = ''

        write_adaf_to_table(
            group_name, adaffile, tablefile, tb_name, tb_col_name)


class ADAFs2Tables(ADAF2TableSuperNode, synode.Node):
    """
    Elementwise exportation of specified data from ADAFs to Tables.
    The data can either be the a raster from the timeseries
    container or the full content of either the metadata or the results
    containers.

    :Inputs:
        **port1** : ADAFs
            ADAFs with data.
    :Outputs:
        **port1** : Tables
            Tables with the content of a specified group in the incoming ADAFs.
    :Configuration:
        **Export group**
            Specify group in the incoming ADAFs which will
            be exported.
        **Time basis raster**
            Specify the raster among the time resolved data which
            will be exported.
        **Time basis column name**
            Specify the name for the time basis column in the
            outgoing Table. The default name is the name of the
            elected raster.
    :Opposite node: :ref:`Tables to ADAFs`
    :Ref. nodes: :ref:`ADAF to Table`
    """

    name = 'ADAFs to Tables'
    description = ('Elementwise export of data from list of ADAFs to a '
                   'list of Tables.')
    nodeid = 'org.sysess.sympathy.data.adaf.adafs2tables'

    inputs = Ports([Port.ADAFs('Input ADAF', name='port1')])
    outputs = Ports([Port.Tables(
        'Data from incoming ADAFs converted to Tables', name='port1')])

    parameters = base_parameters()

    def adjust_parameters(self, node_context):
        port1 = node_context.input['port1']
        if port1.is_valid() and len(port1):
            adafdata = port1[0]
        else:
            adafdata = None
        check_tb_consistence_and_clear(adafdata, node_context.parameters)

        return node_context

    def exec_parameter_view(self, node_context):
        port1 = node_context.input['port1']
        if port1.is_valid() and len(port1):
            adafdata = port1[0]
        else:
            adafdata = None
        return ADAF2TableWidget(node_context.parameters, adafdata)

    def execute(self, node_context):
        group_name = node_context.parameters['export_group'].selected

        input_list = node_context.input['port1']
        output_list = node_context.output['port1']
        for i, adaffile in enumerate(input_list):
            tablefile = output_list.create()
            try:
                tb_name = node_context.parameters['tb'].selected
            except:
                tb_name = None
            try:
                tb_col_name = node_context.parameters['tb_col_name'].value
            except:
                tb_col_name = ''

            write_adaf_to_table(
                group_name, adaffile, tablefile, tb_name, tb_col_name)
            output_list.append(tablefile)
            self.set_progress(100.0 * i / len(input_list))


class ADAF2Tables(ADAF2TableSuperNode, synode.Node):
    """
    Exportation of specified data from ADAF to Tables. The data can
    be the full content of either the metadata, the results or the timeseries
    containers.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : Tables
            Tables with the full content of a specified container in the
            incoming ADAF.
    :Configuration:
        **Export group**
            Specify container in the incoming ADAF which will be exported.
    :Opposite node:
    :Ref. nodes: :ref:`ADAFs to Tables`
    """

    name = 'ADAF to Tables'
    description = ('Export of data from an ADAF to a list of Tables.')
    nodeid = 'org.sysess.sympathy.data.adaf.adaf2tables'
    icon = 'adaf2tables.svg'

    inputs = Ports([Port.ADAF('Input ADAF', name='port1')])
    outputs = Ports([Port.Tables(
        'All data from an ADAF group as a Tables list', name='port1')])

    parameters = simple_base_parameters()

    def exec_parameter_view(self, node_context):
        return ADAF2TableWidgetSimple(node_context)

    def execute(self, node_context):
        group_name = node_context.parameters['export_group'].selected

        adaffile = node_context.input['port1']
        output_list = node_context.output['port1']
        if group_name == 'Time series':
            tb_names = get_rasters_from_adaf(adaffile)
        else:
            tb_names = [None]
        for tb_name in tb_names:
            tablefile = output_list.create()
            write_adaf_to_table(
                group_name, adaffile, tablefile, tb_name)
            output_list.append(tablefile)


class ADAFs2TablesList(ADAF2TableSuperNode, synode.Node):
    """
    Exportation of specified data from ADAFs to Tables. The data can be the
    full content of either the metadata, the results or the timeseries
    containers.

    :Inputs:
        **port1** : ADAFs
            ADAFs with data.
    :Outputs:
        **port1** : Tables
            Tables with the full content of the specified container in the
            incoming ADAFs.
    :Configuration:
        **Export group**
            Specify container in the incoming ADAF which will
            be exported.
    :Opposite node:
    :Ref. nodes: :ref:`ADAFs to Tables`
    """

    name = 'Elementwise ADAFs to Tables'
    description = ('Elementwise export of data from a list of ADAFs to a'
                   'list of Tables.')
    nodeid = 'org.sysess.sympathy.data.adaf.adafs2tableslist'
    icon = 'adaf2table.svg'

    inputs = Ports([Port.ADAFs('Input ADAF', name='port1')])
    outputs = Ports([Port.Tables(
        'All data from a group from the input ADAFs as a Tables list',
        name='port1')])

    parameters = simple_base_parameters()

    def exec_parameter_view(self, node_context):
        return ADAF2TableWidgetSimple(node_context)

    def execute(self, node_context):
        group_name = node_context.parameters['export_group'].selected
        input_list = node_context.input['port1']
        output_list = node_context.output['port1']
        for adaffile in input_list:
            if group_name == 'Time series':
                tb_names = get_rasters_from_adaf(adaffile)
            else:
                tb_names = [None]
            for tb_name in tb_names:
                tablefile = output_list.create()
                write_adaf_to_table(
                    group_name, adaffile, tablefile, tb_name)
                output_list.append(tablefile)


class ADAF2TableWidget(QtGui.QWidget):

    def __init__(self, parameter_root, adafdata, parent=None):
        super(ADAF2TableWidget, self).__init__(parent)
        self._adafdata = adafdata
        self._parameter_root = parameter_root
        self._init_gui()

    def _init_gui(self):
        self._group_target = self._parameter_root['export_group'].gui()
        self._tb_selection = self._parameter_root['tb'].gui()

        self._ts_display = FilterListView(
            header='Time series in selected raster')

        self._tb_col_name_edit = self._parameter_root['tb_col_name'].gui()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self._group_target)

        layout.addWidget(self._tb_col_name_edit)
        layout.addWidget(self._tb_selection)
        layout.addWidget(self._ts_display)
        self.setLayout(layout)

        self._target_changed(self._parameter_root['export_group'].value[0])
        self._update_signals()
        self._group_target.editor().currentIndexChanged[int].connect(
            self._target_changed)
        self._tb_selection.editor().itemChanged.connect(
            self._update_signals)

    def _update_signals(self):
        self._ts_display.clear()
        selected = self._parameter_root['tb'].selected
        if selected and self._adafdata:
            system_name, raster_name = get_system_raster_names(selected)
            if (system_name in self._adafdata.sys.keys() and
                    raster_name in self._adafdata.sys[system_name].keys()):
                signals = (
                    self._adafdata.sys[system_name][raster_name].keys())
            else:
                signals = []
            self._ts_display.add_items(signals)

    def _target_changed(self, index):
        if index in (0, 1):
            self._ts_display.setEnabled(False)
            self._tb_selection.setEnabled(False)
            self._tb_col_name_edit.setEnabled(False)
        else:
            self._ts_display.setEnabled(True)
            self._tb_selection.setEnabled(True)
            self._tb_col_name_edit.setEnabled(True)


class ADAF2TableWidgetSimple(QtGui.QWidget):

    def __init__(self, node_context, parent=None):
        super(ADAF2TableWidgetSimple, self).__init__(parent)
        self._node_context = node_context
        self._parameters = node_context.parameters
        self._init_gui()

    def _init_gui(self):
        self._group_target = self._parameters['export_group'].gui()
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self._group_target)
        self.setLayout(layout)
