# -*- coding: utf-8 -*-
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
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api import table
from sympathy.api import node_helper
from sympathy.api.exceptions import NoDataError
import pandas
import numpy as np


class PivotOperation(node_helper.TableOperation):
    """Pivot a Table, spreadsheet-style."""

    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    icon = 'pivot_table.svg'
    inputs = ['Input']
    outputs = ['Output']
    tags = Tags(Tag.DataProcessing.TransformStructure)

    @staticmethod
    def get_parameters(parameter_root):
        parameter_root.set_list(
            'index', label='Index column',
            description='Column that contains a unique identifier for each '
                        'new row',
            editor=synode.Util.combo_editor().value())
        parameter_root.set_list(
            'columns', label='Column names column',
            description='Column that contains the new column names',
            editor=synode.Util.combo_editor().value())
        parameter_root.set_list(
            'values', label='Value column',
            description='Column that contains the new values',
            editor=synode.Util.combo_editor().value())

    def adjust_table_parameters(self, in_table, parameter_root):
        if in_table['Input'].is_valid():
            column_names = in_table['Input'].column_names()
            for p in ('index', 'columns', 'values'):
                parameter_root[p].list = column_names
        else:
            for p in ('index', 'columns', 'values'):
                parameter_root[p].list = parameter_root[p].value_names

    def execute_table(self, in_table, out_table, parameter_root):
        if in_table['Input'].is_empty():
            return

        data_frame = in_table['Input'].to_dataframe()
        index = parameter_root['index'].selected
        columns = parameter_root['columns'].selected
        values = parameter_root['values'].selected
        output = data_frame.pivot(index, columns, values)
        output.columns = [unicode(d) for d in output.columns.tolist()]
        out_table['Output'].update(table.File.from_dataframe(output))


PivotTable = node_helper.table_node_factory(
    'PivotTable', PivotOperation,
    'Pivot Table', 'org.sysess.sympathy.data.table.pivottablenode')


PivotTables = node_helper.tables_node_factory(
    'PivotTables', PivotOperation,
    'Pivot Tables', 'org.sysess.sympathy.data.table.pivottablesnode')


class TransposeOperation(node_helper.TableOperation):
    """
    EXPERIMENTAL Simple table transpose.

    Given a table with two columns, A and B, create a new table with A as
    column names and B as values.

    :Inputs:
        **Input** : Table
            Table with column and value information.

    :Outputs:
        **Output** : Table
            Transposed table
    """

    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    icon = 'pivot_table.svg'
    inputs = ['Input']
    outputs = ['Output']
    tags = Tags(Tag.Hidden.Deprecated)

    @staticmethod
    def get_parameters(parameter_root):
        parameter_root.set_list(
            'columns', label='Column names column',
            description='Column that contains the new column names',
            editor=synode.Util.combo_editor().value())
        parameter_root.set_list(
            'values', label='Values column',
            description='Column that contains the new values',
            editor=synode.Util.combo_editor().value())

    def adjust_table_parameters(self, in_table, parameter_root):
        column_names = []
        if in_table['Input'].is_valid():
            column_names = in_table['Input'].column_names()
        for p in ('columns', 'values'):
            parameter_root[p].list = column_names

    def execute_table(self, in_table, out_table, parameter_root):
        in_table_ = in_table['Input']

        if in_table_.is_empty():
            return

        columns = in_table_.get_column_to_array(
            parameter_root['columns'].selected)
        values = in_table_.get_column_to_array(
            parameter_root['values'].selected)
        out_table['Output'].update(table.File.from_dataframe(
            pandas.DataFrame(dict(zip(columns, values)), index=[0])))


TransposeTableDeprecated = node_helper.table_node_factory(
    'TransposeTableDeprecated', TransposeOperation,
    'Transpose Table (deprecated)',
    'org.sysess.sympathy.data.table.transposetable')


TransposeTablesDeprecated = node_helper.tables_node_factory(
    'TransposeTablesDeprecated', TransposeOperation,
    'Transpose Tables (deprecated)',
    'org.sysess.sympathy.data.table.transposetables')


class TransposeTableNewSuper(synode.Node):

    author = 'Andreas Tagerud <andreas.tagerud@combine.se>'
    copyright = '(c) 2016 SSystem Engineering Software Society'
    version = '1.0'
    icon = 'pivot_table.svg'
    tags = Tags(Tag.DataProcessing.TransformStructure)

    parameters = synode.parameters()
    parameters.set_boolean(
        'use_col_names',
        label='Column names as first column',
        description=('Set column names from the input table as the first '
                     'column in the transposed table'),
        dvalue=False)
    parameters.set_boolean(
        'reverse_col_names',
        label='Use selected column as column names',
        description=('Use the selected column from input table as column '
                     'names in the transposed table, and discarding the '
                     'selected column from the transpose.'),
        dvalue=False)
    parameters.set_list(
        'columns', label='Column names column',
        description='Column that contains the new column names',
        editor=synode.Util.combo_editor().value())

    controllers = synode.controller(
        when=synode.field('reverse_col_names', 'checked'),
        action=synode.field('columns', 'enabled'))

    def adjust_parameters(self, node_context):
        try:
            columns = node_context.input['input'].column_names()
        except AttributeError:
            columns = node_context.input['input'][0].column_names()
        except NoDataError:
            columns = []
        node_context.parameters['columns'].list = columns

    def execute_table(
            self, in_table, names_to_column, column_to_names, name_column):
        column_names = in_table.column_names()
        out_table = table.File()

        if column_to_names and name_column:
            columns = in_table.get_column_to_array(name_column)
            columns = np.array([unicode(name) for name in columns])
            out_matrix = []
            for column in column_names:
                if column == name_column:
                    continue
                out_matrix.append(in_table.get_column_to_array(column))
        else:
            columns = np.array([unicode(i) for i in range(len(column_names))])
            out_matrix = []
            for column in column_names:
                data_column = in_table.get_column_to_array(column)
                if len(data_column):
                    out_matrix.append(data_column)
        out_matrix = np.ma.asarray(out_matrix).transpose()

        if names_to_column and name_column:
            out_table.set_column_from_array(
                'Column names', np.array(column_names))

        try:
            nbr_of_cols = out_matrix.shape[0]
        except IndexError:
            nbr_of_cols = 0
        for i in range(nbr_of_cols):
            name = str(columns[i]) if i < len(
                columns) else 'No name column ' + str(i + 1)
            try:
                out_table.set_column_from_array(name, out_matrix[i, :])
            except IndexError:
                out_table.set_column_from_array(
                    name, np.ma.masked_all((len(column_names))))
            except ValueError:
                column = np.ma.array(out_matrix[i, :])
                masked = np.ma.masked_all((len(column_names) - len(column)))
                column = np.ma.concatenate([column, masked])
                out_table.set_column_from_array(name, column)
        return out_table

    def _get_column_name(self, table, index):
        columns = table.column_names()
        if len(columns):
            return str(columns[index])
        return None


class TransposeTableNew(TransposeTableNewSuper):
    """
    This node performs a standard transpose of tables. Bear in mind, since
    a column can only contain one type, if the rows contain different types
    the transposed columns will be converted to the closest matching type. The
    worst case is therefore strings.

    An exception to this behaviour is when the first column contains strings.
    Using the option 'Use selected column as column names' the selected column
    will replace the column names in the new table. The rest of the input table
    will be transposed, discarding the name column.

    The other option is 'Column names as first column' which will take the
    table's column names and put them in the first column in the output table.
    This is convenient if you simply want to extract column names from a table.
    """

    name = 'Transpose Table'
    nodeid = 'org.sysess.sympathy.data.table.transposetablenew'
    inputs = Ports([Port.Table('The Table to transpose', name='input')])
    outputs = Ports([Port.Table('The transposed Table', name='output')])

    def execute(self, node_context):
        column = self._get_column_name(
            node_context.input['input'],
            node_context.parameters['columns'].value[0])
        node_context.output['output'].source(self.execute_table(
            node_context.input['input'],
            node_context.parameters['use_col_names'].value,
            node_context.parameters['reverse_col_names'].value,
            column))


class TransposeTablesNew(TransposeTableNewSuper):
    """
    This node performs a standard transpose of tables. Bear in mind, since
    a column can only contain one type, if the rows contain different types
    the transposed columns will be converted to the closest matching type. The
    worst case is therefore strings.

    An exception to this behaviour is when the first column contains strings.
    Using the option 'Use selected column as column names' the selected column
    will replace the column names in the new table. The rest of the input table
    will be transposed, discarding the name column.

    The other option is 'Column names as first column' which will take the
    table's column names and put them in the first column in the output table.
    This is convenient if you simply want to extract column names from a table.
    """

    name = 'Transpose Tables'
    nodeid = 'org.sysess.sympathy.data.table.transposetablesnew'
    inputs = Ports([Port.Tables('The Tables to transpose', name='input')])
    outputs = Ports([Port.Tables('The transposed Tables', name='output')])

    def execute(self, node_context):
        for in_table in node_context.input['input']:
            column = self._get_column_name(
                in_table, node_context.parameters['columns'].value[0])
            node_context.output['output'].append((self.execute_table(
                in_table,
                node_context.parameters['use_col_names'].value,
                node_context.parameters['reverse_col_names'].value,
                column)))
