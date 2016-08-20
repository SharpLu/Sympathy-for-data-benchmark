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
In the standard libray there exist two nodes which exports the data from the
:ref:`Table` format to the :ref:`ADAF` format. Together with the existing
nodes in the reversed transiton, :ref:`ADAF to Table`, there exists a wide
spectrum of nodes which gives the possibility to, in different ways, change
between the two internal data types.

A container in the ADAF is specified in the configuration GUI as a target
for the exportation. If the time series container is choosen it is necessary
to specify the column in the Table which will be the time basis signal in
the ADAF. There do also exist an opportunity to specify both the name of the
system and raster containers, see :ref:`ADAF` for explanations of containers.
"""
import random

from itertools import izip
from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui') # noqa
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.platform.exceptions import SyDataError


def write_table_timeseries_to_adaf(system_name, raster_name, tb_column,
                                   tabledata, adaffile):
    if tb_column in tabledata:
        tb_group = adaffile.sys
        if system_name in tb_group:
            system = tb_group[system_name]
        else:
            system = tb_group.create(system_name)

        if raster_name in system:
            raster = system[raster_name]
        else:
            raster = system.create(raster_name)

        # Move the table into the raster and remove tb_column from raster
        raster.from_table(tabledata, tb_column)
    else:
        raise SyDataError('The selected time basis column does not exist in '
                          'the incoming Table')


def write_tabledata_to_adaf(export_to_meta, tablefile, adaffile):
    if export_to_meta:
        adaffile.meta.from_table(tablefile)
    else:
        adaffile.res.from_table(tablefile)


def check_table_columns_consistence_and_clear(
        table_name, columns_table, parameter_root):
    """Check whether table columns have changed since parameter
    view last was executed. If yes, clear lists.
    """
    selected_tb = parameter_root['tb'].selected
    parameter_root['tb'].list = columns_table

    if parameter_root['system'].value == '':
        parameter_root['system'].value = (
            'system_%d' % random.randrange(0, 100000))

    if selected_tb is None:
        if table_name in parameter_root['tb'].list:
            parameter_root['tb'].selected = table_name

        parameter_root['raster'].value = parameter_root['tb'].selected


class TableConvertWidget(QtGui.QWidget):
    def __init__(self, node_context, parent=None):
        super(TableConvertWidget, self).__init__(parent)
        self._parameters = node_context.parameters
        self._init_gui()

    def _init_gui(self):
        self._group_target = self._parameters['export_to_group'].gui()
        self._system_edit = self._parameters['system'].gui()
        self._raster_edit = self._parameters['raster'].gui()
        self._tb_selection = self._parameters['tb'].gui()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self._group_target)
        layout.addWidget(self._system_edit)
        layout.addWidget(self._raster_edit)
        tb_group = QtGui.QGroupBox()
        tb_group_layout = QtGui.QVBoxLayout()
        tb_group_layout.addWidget(self._tb_selection)
        tb_group.setLayout(tb_group_layout)
        layout.addWidget(tb_group)
        self.setLayout(layout)
        self._target_changed(self._parameters['export_to_group'].value[0])
        self._group_target.editor().currentIndexChanged[int].connect(
            self._target_changed)
        self._tb_selection.editor().itemChanged.connect(
            self._tb_column_changed)

    def _target_changed(self, index):
        if index in (0, 1):
            self._tb_selection.setEnabled(False)
            self._system_edit.setEnabled(False)
            self._raster_edit.setEnabled(False)
        else:
            self._tb_selection.setEnabled(True)
            self._system_edit.setEnabled(True)
            self._raster_edit.setEnabled(True)

    def _tb_column_changed(self, item):
        self._raster_edit.set_value(unicode(item.text()))


class Table2ADAFSuperNode(object):
    tags = Tags(Tag.DataProcessing.Convert)
    parameters = synode.parameters()
    parameters.set_list(
        'export_to_group', plist=['Meta', 'Result', 'Time series'],
        label='Export to group',
        description='Group to put table data.',
        editor=synode.Util.combo_editor().value())

    tb_editor = synode.Util.list_editor()
    tb_editor.set_attribute('filter', True)
    ts_editor = synode.Util.list_editor()
    ts_editor.set_attribute('filter', True)
    ts_editor.set_attribute('selection', 'multi')
    parameters.set_string('system', label='Time series system name',
                          value='')
    parameters.set_string('raster', label='Time series raster name',
                          value='')
    parameters.set_list('tb',
                        label="Time basis column",
                        editor=tb_editor.value())


class Table2ADAF(Table2ADAFSuperNode, synode.Node):
    """
    Export the full content of a Table to a specified container in an ADAF.

    :Inputs:
        **port1** : Table
            Table to export.
    :Outputs:
        **port1** : ADAF
            ADAF with the exported Table data
    :Configuration:
        **Export to Group**
            Choose a container in the ADAF as target for the
            exportation.
        **Time basis column** :
            Select a column in the Table which will be the
            time basis signal in the ADAF.
        **Time series system name** : optional
            Specify name of the created system in ADAF.
        **Time series raster name** : optional
            Specify name of the created raster in ADAF.
    :Opposite node: :ref:`ADAF to Table`
    :Ref. nodes: :ref:`Tables to ADAFs`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    name = 'Table to ADAF'
    description = 'Export content of Table to specified container in ADAF.'
    nodeid = 'org.sysess.sympathy.data.table.table2adaf'
    icon = 'import_table.svg'

    inputs = Ports([Port.Table('Input Table', name='port1')])
    outputs = Ports([Port.ADAF('ADAF with data in input Table', name='port1')])

    def adjust_parameters(self, node_context):
        if node_context.input['port1'].is_valid():
            column_names = node_context.input['port1'].column_names()
            table_name = node_context.input['port1'].get_name()
        else:
            column_names = []
            table_name = ''

        check_table_columns_consistence_and_clear(
            table_name, column_names, node_context.parameters)

        return node_context

    def exec_parameter_view(self, node_context):
        return TableConvertWidget(node_context)

    def execute(self, node_context):
        parameters = node_context.parameters
        group_name = parameters['export_to_group'].selected
        tb_column = parameters['tb'].value_names
        system_name = parameters['system'].value
        raster_name = parameters['raster'].value

        export_to = group_name.lower()
        tablefile = node_context.input['port1']
        adaffile = node_context.output['port1']
        if export_to in ('meta', 'result'):
            write_tabledata_to_adaf(export_to == 'meta', tablefile,
                                    adaffile)
        else:
            write_table_timeseries_to_adaf(system_name, raster_name,
                                           tb_column[0], tablefile,
                                           adaffile)


class Tables2ADAFs(Table2ADAFSuperNode, synode.Node):
    """
    Export the full content of Tables to specified container in ADAFs.

    :Inputs:
        **port1** : Tables
            Tables to export
    :Outputs:
        **port1** : ADAFs
            ADAFs with the exported Table data
    :Configuration:
        **Export to Group**
            Choose a container in the ADAF as target for the
            exportation.
        **Time basis column**
            Select a column in the Table which will be the
            time basis signal in the ADAF.
        **Time series system name** : optional
            Specify name of the created system in ADAF.
        **Time series raster name** : optional
            Specify name of the created raster in ADAF.
    :Opposite node: :ref:`ADAFs to Tables`
    :Ref. nodes: :ref:`Table to ADAF`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    name = 'Tables to ADAFs'
    description = 'Convert Tables to ADAFs'
    nodeid = 'org.sysess.sympathy.data.table.tables2adafs'
    icon = 'import_table.svg'

    inputs = Ports([Port.Tables('Input Tables', name='port1')])
    outputs = Ports([Port.ADAFs(
        'ADAFs with data in input Tables', name='port1')])

    def adjust_parameters(self, node_context):
        port1 = node_context.input['port1']
        if port1.is_valid() and len(port1):
            column_names = port1[0].column_names()
            table_name = port1[0].get_name()
        else:
            column_names = []
            table_name = ''

        check_table_columns_consistence_and_clear(
            table_name, column_names, node_context.parameters)
        return node_context

    def exec_parameter_view(self, node_context):
        return TableConvertWidget(node_context)

    def execute(self, node_context):
        parameters = node_context.parameters
        group_name = parameters['export_to_group'].selected
        tb_column = parameters['tb'].value_names
        system_name = parameters['system'].value
        raster_name = parameters['raster'].value

        export_to = group_name.lower()
        input_list = node_context.input['port1']
        number_of_objects = len(input_list)
        output_list = node_context.output['port1']

        for count, in_datafile in enumerate(input_list):
            adaffile = output_list.create()
            if export_to in ('meta', 'result'):
                write_tabledata_to_adaf(
                    export_to == 'meta', in_datafile, adaffile)
            else:
                write_table_timeseries_to_adaf(system_name, raster_name,
                                               tb_column[0], in_datafile,
                                               adaffile)

            output_list.append(adaffile)
            self.set_progress(100.0 * (count + 1) / number_of_objects)


class UpdateADAFWithTable(Table2ADAF):
    """
    Update ADAF with the full content of a Table to a specified container in
    the ADAF. Existing container will be replaced completely.

    :Inputs:
        **port1** : Table
            Table to update with.
        **port2** : ADAF
            ADAF to be updated.
    :Outputs:
        **port1** : ADAF
            ADAF with the exported Table data
    :Configuration:
        **Export to Group**
            Choose a container in the ADAF as target for the
            exportation.
        **Time basis column** :
            Select a column in the Table which will be the
            time basis signal in the ADAF.
        **Time series system name** : optional
            Specify name of the created system in ADAF.
        **Time series raster name** : optional
            Specify name of the created raster in ADAF.
    :Opposite node: :ref:`ADAF to Table`
    :Ref. nodes: :ref:`Tables to ADAFs`
    """

    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    name = 'Update ADAF with Table'
    description = 'Export content of Table to specified container in ADAF.'
    nodeid = 'org.sysess.sympathy.data.table.updateadafwithtable'
    icon = 'import_table.svg'
    tags = Tags(Tag.DataProcessing.Convert)

    inputs = Ports([Port.Table('Input Table', name='port1'),
                    Port.ADAF('Input ADAF', name='port2')])
    outputs = Ports([Port.ADAF(
        'ADAF updated with data in input Table', name='port1')])

    def execute(self, node_context):
        node_context.output['port1'].source(node_context.input['port2'])
        super(UpdateADAFWithTable, self).execute(node_context)


class UpdateADAFsWithTables(Tables2ADAFs):
    """
    Update ADAFS with the full content of Tables to specified container in
    ADAFs. Existing container will be replaced completely.

    :Inputs:
        **port1** : Tables
            Tables to update with
        **port2** : ADAFs
            ADAFs to be updated
    :Outputs:
        **port1** : ADAFs
            ADAFs with the exported Table data
    :Configuration:
        **Export to Group**
            Choose a container in the ADAF as target for the
            exportation.
        **Time basis column**
            Select a column in the Table which will be the
            time basis signal in the ADAF.
        **Time series system name** : optional
            Specify name of the created system in ADAF.
        **Time series raster name** : optional
            Specify name of the created raster in ADAF.
    :Opposite node: :ref:`ADAFs to Tables`
    :Ref. nodes: :ref:`Table to ADAF`
    """

    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    name = 'Update ADAFs with Tables'
    description = 'Export content of Table to specified container in ADAF.'
    nodeid = 'org.sysess.sympathy.data.table.updateadafswithtables'
    icon = 'import_table.svg'
    tags = Tags(Tag.DataProcessing.Convert)

    inputs = Ports([Port.Tables('Input Tables', name='port1'),
                    Port.ADAFs('Input ADAFs', name='port2')])
    outputs = Ports([Port.ADAFs(
        'ADAFs with data in input Tables', name='port1')])

    def execute(self, node_context):
        parameters = node_context.parameters
        group_name = parameters['export_to_group'].selected
        tb_column = parameters['tb'].value_names
        system_name = parameters['system'].value
        raster_name = parameters['raster'].value

        export_to = group_name.lower()
        input_table_list = node_context.input['port1']
        input_adaf_list = node_context.input['port2']
        number_of_objects = len(input_table_list)
        output_list = node_context.output['port1']

        for count, (in_table, in_adaf) in enumerate(
                izip(input_table_list, input_adaf_list)):
            if export_to in ('meta', 'result'):
                write_tabledata_to_adaf(
                    export_to == 'meta', in_table, in_adaf)
            else:
                write_table_timeseries_to_adaf(system_name, raster_name,
                                               tb_column[0], in_table,
                                               in_adaf)

            output_list.append(in_adaf)
            self.set_progress(100.0 * (count + 1) / number_of_objects)
