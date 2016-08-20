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
There are many situations where you may want to throw away some of the columns
of a table. Perhaps the amount of data is large and you want to trim it to
increase performance, or perhaps some column was just needed as an intermediary
step in some analysis.

Whatever the reason, if you want to remove some of the columns of a Table the
standard libray offers two types of nodes which provide this functionality. The
nodes :ref:`Select columns in Table` and :ref:`Select columns in Tables` will
let you select what columns to keep (if *complement* is disabled) or which
columns to throw away (if *complement* is enabled) in their GUI. The nodes
:ref:`Select columns in Table with Table` and
:ref:`Select columns in Tables with Table` instead take a second input table
with a filter column containing the names of all the columns that should be
kept (if *complement* is disabled) or all the columns that should be thrown
away (if *complement* is enabled). The configuration for the latter nodes also
allows you to choose the column that should be used as a filter.
"""
from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import sywarn


def select_columns(input_table, output_table, column_names, complement=False):
    if complement:
        input_column_names = input_table.column_names()
        for column in column_names:
            try:
                input_column_names.remove(column)
            except ValueError:
                pass
        for column in input_column_names:
            output_table.update_column(column, input_table, column)
    else:
        for column in input_table.column_names():
            if column in column_names:
                output_table.update_column(column, input_table, column)


class SelectTableColumns(synode.Node):
    """
    :Inputs:
        **TableInput** : Table
            Table with many column.
    :Outputs:
        **TableOutput** : Table
            Table with fewer columns.
    :Configuration:
        **Remove selected columns**
            When enabled, the selected columns will be removed. When disabled,
            the non-selected columns will be removed.
        **Select columns** :
            Select the columns which will proceed.
        **All** : button
            Select all listed columns.
        **Clear** : button
            Deselect all listed columns.
        **Invert** : button
            Invert the selection of columns.
    :Ref. nodes: :ref:`Select columns in Table with Table`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(c) 2013 System Engineering Software Society"
    version = '1.0'

    name = 'Select columns in Table'
    description = 'Select columns in Table by using the configuration GUI.'
    nodeid = 'org.sysess.sympathy.data.table.selecttablecolumns'
    icon = 'select_table_columns.svg'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([Port.Table('Input Table', name='port1')])
    outputs = Ports([Port.Table(
        'Table with selected columns removed', name='port2')])

    parameters = synode.parameters()
    parameters.set_boolean(
        'complement', value=False,
        label="Remove selected columns",
        description=(
            'When enabled, the selected columns will be removed. '
            'When disabled, the non-selected columns will be removed.'))
    editor = synode.Util.selectionlist_editor('multi').value()
    editor['filter'] = True
    editor['buttons'] = True
    editor['invertbutton'] = True
    parameters.set_list(
        'columns', label='Select columns',
        description='Select the columns which will proceed.', value=[],
        editor=editor)

    def adjust_parameters(self, node_context):
        """Adjust parameters"""
        parameters = node_context.parameters
        tablefile = node_context.input['port1']
        if tablefile.is_valid():
            parameters['columns'].list = sorted(
                set(parameters['columns'].value_names) |
                set(tablefile.column_names()))
        else:
            parameters['columns'].list = sorted(
                parameters['columns'].value_names)

        return node_context

    def execute(self, node_context):
        """Execute"""
        parameters = node_context.parameters
        column_names = parameters['columns'].value_names
        complement = parameters['complement'].value
        input_table = node_context.input['port1']
        output_table = node_context.output['port2']
        output_table.set_name(input_table.get_name())
        output_table.set_attributes(input_table.get_attributes())
        select_columns(input_table, output_table, column_names,
                       complement=complement)


class SelectTablesColumns(synode.Node):
    """
    :Inputs:
        **TablesInput** : Tables
            Table with column to select.
    :Outputs:
        **TablesOutput** : Tables
            Table with selected columns.
    :Configuration:
        **Remove selected columns**
            When enabled, the selected columns will be removed. When disabled,
            the non-selected columns will be removed.
        **Select columns** :
            Select the columns which will proceed.
        **All** : button
            Select all listed columns.
        **Clear** : button
            Deselect all listed columns.
        **Invert** : button
            Invert the selection of columns.
    :Ref. nodes: :ref:`Select columns in Table with Table`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(c) 2013 System Engineering Software Society"
    version = '1.0'

    name = 'Select columns in Tables'
    description = 'Select columns in Tables by using the configuration GUI.'
    nodeid = 'org.sysess.sympathy.data.table.selecttablescolumns'
    icon = 'select_table_columns.svg'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([Port.Tables('Input Tables')])
    outputs = Ports([Port.Tables('Tables with selected columns removed')])

    parameters = synode.parameters()
    parameters.set_boolean(
        'complement', value=False,
        label="Remove selected columns",
        description=(
            'When enabled, the selected columns will be removed. '
            'When disabled, the non-selected columns will be removed.'))
    editor = synode.Util.selectionlist_editor('multi').value()
    editor['filter'] = True
    editor['buttons'] = True
    editor['invertbutton'] = True
    parameters.set_list(
        'columns', label='Select columns',
        description='Select the columns which will proceed.', value=[],
        editor=editor)

    def adjust_parameters(self, node_context):
        input_table = node_context.input[0]
        if input_table.is_valid() and len(input_table):
            node_context.parameters['columns'].list = sorted(
                input_table[0].column_names())
        return node_context

    def execute(self, node_context):
        parameters = node_context.parameters
        column_names = parameters['columns'].value_names
        complement = parameters['complement'].value
        otables = node_context.output[0]
        for itable in node_context.input[0]:
            otable = table.File()
            otable.set_name(itable.get_name())
            otable.set_attributes(itable.get_attributes())
            select_columns(itable, otable, column_names, complement=complement)
            otables.append(otable)


class SelectTableColumnsFromTable(synode.Node):
    """
    :Inputs:
        **Selection** : Table
            Table with filter column.
        **TableInput** : Table
            Table with columns to select.
    :Outputs:
        **TableOutput** : Table
            Table with selected columns.
    :Configuration:
        **Remove selected columns**
            When enabled, the selected columns will be removed. When disabled,
            the non-selected columns will be removed.
        **Column with column names** :
            Specify column in the selection Table, upper port, to use
            as a filter to select columns in the TableInput, lower port.
    :Ref. nodes: :ref:`Select columns in Table`
    """

    name = 'Select columns in Table with Table'
    description = ('Select columns in Table by using column '
                   'in selection Table.')

    icon = 'select_table_columns.svg'

    nodeid = 'org.sysess.sympathy.data.table.selecttablecolumnsfromtable'
    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([
        Port.Table('Selection', name='port1', requiresdata=True),
        Port.Table('Input Table', name='port2', requiresdata=True)])
    outputs = Ports([
        Port.Table('Table with columns in Selection removed', name='port1')])

    parameters = synode.parameters()
    parameters.set_boolean(
        'complement', value=False, label="Remove selected columns",
        description=(
            'When enabled, the selected columns will be removed. '
            'When disabled, the non-selected columns will be '
            'removed.'))
    parameters.set_list(
        'selection_column', label="Column with column names",
        description=('Select column in Selection Table '
                     'used for column name filtration.'),
        value=[0],
        editor=synode.Util.combo_editor().value())

    def adjust_parameters(self, node_context):
        if node_context.input['port1'].is_valid():
            node_context.parameters['selection_column'].list = sorted(
                node_context.input['port1'].column_names())
        return node_context

    def execute(self, node_context):
        """Execute"""
        selection_column_name = (
            node_context.parameters['selection_column'].selected)
        select_complement = node_context.parameters['complement'].value

        selection_table = node_context.input['port1']
        input_table = node_context.input['port2']
        output_table = node_context.output['port1']
        output_table.set_name(input_table.get_name())
        output_table.set_attributes(input_table.get_attributes())

        if input_table.is_empty():
            return

        if selection_column_name in selection_table.column_names():
            column_names = [unicode(column_name) for column_name in
                            selection_table.get_column_to_array(
                                selection_column_name)]
        else:
            sywarn('The selected column does not seem to exist. '
                   'Assuming empty input.')
            column_names = []

        select_columns(input_table, output_table, column_names,
                       complement=select_complement)


class SelectTableColumnsFromTables(synode.Node):
    """
    :Inputs:
        **Selection** : Table
            Table with filter column.
        **TableInput** : Tables
            Table with columns to select.
    :Outputs:
        **TableOutput** : Tables
            Tables with selected columns.
    :Configuration:
        **Remove selected columns**
            When enabled, the selected columns will be removed. When disabled,
            the non-selected columns will be removed.
        **Column with column names** :
            Specify column in the selection Table, upper port, to use
            as a filter to select columns in the TableInput, lower port.
    :Ref. nodes: :ref:`Select columns in Table`
    """

    name = 'Select columns in Tables with Table'
    description = ('Select columns in Tables by using column '
                   'in selection Table.')

    icon = 'select_table_columns.svg'

    nodeid = 'org.sysess.sympathy.data.table.selecttablecolumnsfromtables'
    author = ('Greger Cronquist <greger.cronquist@sysess.org>, '
              'Erik der Hagopian <erik.hagopian@sysess.org>')
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([
        Port.Table('Selection', name='port1', requiresdata=True),
        Port.Tables('Input Tables', name='port2', requiresdata=True)])
    outputs = Ports([
        Port.Tables('Tables with columns in Selection removed', name='port1')])

    parameters = synode.parameters()
    parameters.set_boolean(
        'complement', value=False, label="Remove selected columns",
        description=(
            'When enabled, the selected columns will be removed. '
            'When disabled, the non-selected columns will be '
            'removed.'))
    parameters.set_list(
        'selection_column', label="Column with column names",
        description=('Select column in Selection Table '
                     'used for column name filtration.'),
        value=[0],
        editor=synode.Util.combo_editor().value())

    def adjust_parameters(self, node_context):
        if node_context.input['port1'].is_valid():
            node_context.parameters['selection_column'].list = sorted(
                node_context.input['port1'].column_names())
        return node_context

    def execute(self, node_context):
        """Execute"""
        selection_column_name = (
            node_context.parameters['selection_column'].selected)
        select_complement = node_context.parameters['complement'].value

        selection_table = node_context.input['port1']
        input_tables = node_context.input['port2']
        output_tables = node_context.output['port1']

        if len(input_tables) == 0:
            return

        if selection_column_name in selection_table.column_names():
            column_names = [unicode(column_name) for column_name in
                            selection_table.get_column_to_array(
                                selection_column_name)]
        else:
            sywarn('The selected column does not seem to exist. '
                   'Assuming empty input.')
            column_names = []

        for input_table in input_tables:
            output_table = table.File()
            output_table.set_name(input_table.get_name())
            output_table.set_attributes(input_table.get_attributes())
            select_columns(input_table, output_table, column_names,
                           complement=select_complement)
            output_tables.append(output_table)
