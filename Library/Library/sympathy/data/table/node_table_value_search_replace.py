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
In the standard library there exist two nodes which perform a search and
replace of values among the elements in Tables. Of the two nodes, one
operates on single Table while the other operates on multiple Tables.

In the configuration of the nodes one has to specify the columns in the Tables
which will be regarded during the execution of the node. At the moment the node
is restricted to string and unicode columns.

For string and unicode columns the search and replace expressions may be regular
expressions. Here, it is possible to use ()-grouping in the search expression
to reuse the match of the expression within the parentheses in the replacement
expression. In the regular expression for the replacement use ``\\1`` (or
higher numbers) to insert matches.

As an example let's say that you have an input table with a column containing
the strings ``x``, ``y``, and ``z``. If you enter the search expression
``(.*)`` and the replacement expression ``\\1_new`` the output will be the
strings ``x_new``, ``y_new``, and ``z_new``.

"""
from sympathy.api import node as synode
from sympathy.api import table
import re
import numpy as np
import pandas
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyConfigurationError


def replace_table_values(find, replace, input_table, columns, use_default,
                         default):
    input_frame = input_table.to_dataframe()

    for column_name in set(columns) & set(input_table.column_names()):
        column = input_frame[column_name]
        # FIX! (Daniel), different versions of pandas handle the replace
        # operation on empty Series in different mannors. E.g. an exception
        # is raised when using Pandas version 0.10.1, this is not the case
        # for version 0.12. This if-statement may be removed in the future.
        if len(column) > 0:
            # For numerical types we use pandas replace. O is for object
            if not use_default:
                if column.dtype.kind != 'O':
                    column.replace(find, replace, inplace=True)
                else:
                    new_values = [re.sub(find, replace, value)
                                  for value in column.tolist()]
                    input_frame[column_name] = np.array(new_values)
            else:
                # Convert value to type in column.
                column_type = type(column.get(0, default))
                default = column_type(default)
                find = column_type(find)

                if column.dtype.kind != 'O':
                    new_values = [replace if find == value else default
                                  for value in column.tolist()]
                else:
                    new_values = [re.sub(find, replace, value)
                                  if re.search(find, value) else default
                                  for value in column.tolist()]
                input_frame[column_name] = np.array(new_values)
    return input_frame


class TableSearchBase(synode.Node):
    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    icon = 'search_replace.svg'
    tags = Tags(Tag.DataProcessing.TransformData)

    parameters = synode.parameters()
    editor = synode.Util.selectionlist_editor('multi').value()
    editor['filter'] = True
    parameters.set_list(
        'columns', label='Select columns',
        description='Select the columns to use perform replacement on',
        value=[], editor=editor)

    parameters.set_string('find', label='Search expression',
                          value='',
                          description='Specify search expression.')
    parameters.set_string('replace', label='Replacement expression',
                          value='',
                          description='Specify replace expression.')
    parameters.set_boolean('use_default', label='Use default',
                           value=False,
                           description='Use default value when not found.')
    parameters.set_string('default', label='Default value',
                          value='',
                          description='Specify default value')


class TableValueSearchReplaceMultiple(TableSearchBase):
    """
    Search and replace string and unicode values in Tables.

    :Inputs:
        **tables** : Tables
            Tables with values to replace
    :Outputs:
        **tables** : Tables
            Tables with replaced values
    :Configuration:
        **Select columns**
            Select the columns which to apply the search and
            replace routine to.
        **Search expression**
            Specify search expression *If selected columns are
            of string type, regex can be used.*
        **Replacement expression**
            Specify replacement expression. *If selected columns
            are of string type, regex can be used.*
    :Ref. nodes: :ref:`Replace values in Table`
    """

    name = 'Replace values in Tables'
    description = 'Search and replace values in Tables.'
    nodeid = 'org.sysess.sympathy.data.table.tablevaluesearchreplacemultiple'
    inputs = Ports([Port.Tables('Input Tables', name='tables')])
    outputs = Ports([Port.Tables(
        'Tables with replaced values', name='tables')])

    def adjust_parameters(self, node_context):
        input_tables = node_context.input['tables']
        if input_tables.is_valid() and len(input_tables):
            columns = input_tables[0].column_names()
        else:
            columns = []
        node_context.parameters['columns'].list = columns
        return node_context

    def execute(self, node_context):
        parameters = node_context.parameters
        find = parameters['find'].value
        replace = parameters['replace'].value
        try:
            use_default = parameters['use_default'].value
            default = parameters['default'].value
        except KeyError:
            use_default = False
            default = ''

        number_of_tables = len(node_context.input['tables'])
        for ctr, input_table in enumerate(node_context.input['tables']):
            output_frame = replace_table_values(
                find, replace, input_table,
                parameters['columns'].value_names, use_default, default)

            output_table = table.File()
            output_table.update(table.File.from_dataframe(output_frame))
            output_table.set_attributes(input_table.get_attributes())
            output_table.set_name(input_table.get_name())
            node_context.output['tables'].append(output_table)
            self.set_progress(100.0 * (ctr + 1.0) / number_of_tables)


class TableValueSearchReplace(TableSearchBase):
    """
    Search and replace string and unicode values in Table.

    :Inputs:
        **tables** : Tables
            Tables with values to replace
    :Outputs:
        **tables** : Tables
            Tables with replaced values
    :Configuration:
        **Select columns**
            Select the columns which to apply the search and
            replace routine to.
        **Search expression**
            Specify search expression *If selected columns are
            of string type, regex can be used.*
        **Replacement expression**
            Specify replacement expression. *If selected columns
            are of string type, regex can be used.*
    :Ref. nodes: :ref:`Replace values in Tables`
    """

    name = 'Replace values in Table'
    description = 'Search and replace values in Table.'
    nodeid = 'org.sysess.sympathy.data.table.tablevaluesearchreplace'
    inputs = Ports([Port.Table('Input Table', name='table')])
    outputs = Ports([Port.Table('Table with replaced values', name='table')])

    def adjust_parameters(self, node_context):
        input_table = node_context.input['table']
        if input_table.is_valid():
            columns = input_table.column_names()
        else:
            columns = []
        node_context.parameters['columns'].list = columns
        return node_context

    def execute(self, node_context):
        parameters = node_context.parameters
        find = parameters['find'].value
        replace = parameters['replace'].value
        try:
            use_default = parameters['use_default'].value
            default = parameters['default'].value
        except KeyError:
            use_default = False
            default = ''
        input_table = node_context.input['table']
        output_frame = replace_table_values(
            find, replace, input_table,
            parameters['columns'].value_names, use_default, default)

        output_table = node_context.output['table']
        output_table.update(table.File.from_dataframe(output_frame))
        output_table.set_attributes(input_table.get_attributes())
        output_table.set_name(input_table.get_name())


class TableSearchReplaceFromTable(synode.Node):
    """
    :Inputs: Two tables
    :Outputs: (List of ?) table with result calculations
    :Configuration:
    """

    name = 'Table Search and Replace'
    description = 'Searches for and replaces values in specified columns'
    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 System Engineering Society'
    nodeid = 'org.sysess.sympathy.data.table.tablevaluesearchreplacefromtable'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.TransformData)

    inputs = Ports([
        Port.Table('Expressions', name='expressions', requiresdata=True),
        Port.Table('Table Data', name='data', requiresdata=True)])
    outputs = Ports([Port.Table('Table with replaced values', name='data')])

    parameters = synode.parameters()
    editor = synode.Util.selectionlist_editor('').value()
    editor['filter'] = True
    parameters.set_list(
        'column', label='Column to replace values in',
        description='Select in which to perform replacement', value=[],
        editor=editor)
    parameters.set_list(
        'src', label='Column with search expressions',
        description='Select which column contains search expressions',
        value=[], editor=editor)
    parameters.set_list(
        'dst', label='Column with replace expressions',
        description='Select which column contains replacements', value=[],
        editor=editor)
    parameters.set_boolean(
        'regex', label='Enable regular expressions',
        description='Enable regular expressions in the search and replace '
                    'expressions', value=False)
    parameters.set_boolean(
        'ignore_case', label='Ignore case',
        description='Ignore case when searching', value=False)

    def adjust_parameters(self, node_context):
        parameters = node_context.parameters
        expr_table = node_context.input['expressions']
        if expr_table.is_valid():
            file_columns = expr_table.column_names()
        else:
            file_columns = []
        data_table = node_context.input['data']
        if data_table.is_valid():
            data_columns = data_table.column_names()
        else:
            data_columns = []

        for parameter in ('src', 'dst'):
            if set(parameters[parameter].list) != set(file_columns):
                parameters[parameter].list = file_columns
                parameters[parameter].value_names = []
                parameters[parameter].value = []
        if set(parameters['column'].list) != set(data_columns):
            parameters['column'].list = data_columns
            parameters['column'].value_names = []
            parameters['column'].value = []
        return node_context

    def execute(self, node_context):
        parameters = node_context.parameters
        in_expr = node_context.input['expressions']
        input_table = node_context.input['data']
        output_table = node_context.output['data']
        if in_expr.is_empty():
            output_table.source(input_table)
            return

        try:
            src_values = pandas.Series(
                in_expr.get_column_to_array(parameters['src'].selected))
            dst_values = pandas.Series(
                in_expr.get_column_to_array(parameters['dst'].selected))
        except KeyError:
            raise SyConfigurationError(
                'One or more of the selected columns do not seem to exist')

        data = input_table.to_dataframe()
        col = parameters['column'].selected
        to_replace = data[col]
        if parameters['ignore_case'].value:
            src_values = src_values.str.lower()
            to_replace = data[col].str.lower()

        subset = to_replace.isin(src_values)
        match = to_replace.replace(src_values.tolist(), dst_values.tolist())
        data[col][subset] = match

        output_table.set_attributes(input_table.get_attributes())
        output_table.set_name(input_table.get_name())
        output_table.update(table.File.from_dataframe(data))
