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
"""
The Table data type includes an additional container, besides the data
container, for storing attributes. An attribute is stored as a scalar value
together with a header.

The standard library contains two nodes for setting and getting Table
attributes.
"""
import numpy as np

from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


def get_table_attributes(in_table, out_table):
    """Add table attribute in in_table as column in out_table."""
    for key, value in in_table.get_table_attributes().items():
        out_table.set_column_from_array(key, np.array([value]))


def set_table_attributes(attr_table, out_table):
    """Update table attributes in out_table with the content of attr_table."""
    new_attr = {}
    for key in attr_table.column_names():
        new_attr[key] = attr_table.get_column_to_array(key)[0]

    out_attr = out_table.get_table_attributes()
    out_attr.update(new_attr)
    out_table.set_table_attributes(out_attr)


def set_column_attributes(attr_table, out_table, parameters):
    """Update column attributes in out_table with the content of attr_table."""
    names = attr_table.get_column_to_array(
        parameters['columns'].list[parameters['columns'].value[0]])
    attrs = attr_table.get_column_to_array(
        parameters['attributes'].list[parameters['attributes'].value[0]])
    values = attr_table.get_column_to_array(
        parameters['values'].list[parameters['values'].value[0]])

    for name in set(names):
        if out_table.has_column(name):
            mask = names == name
            data_attributes = out_table.get_column_attributes(name)

            new_attributes = {
                attr: value for attr, value in zip(
                    attrs[mask], values[mask])}

            data_attributes.update(new_attributes)
            out_table.set_column_attributes(name, data_attributes)


def get_column_attributes(in_table, out_table):
    """Add column attributes in in_table as data in out_table."""
    part_tables = []
    for column in in_table.column_names():
        part_table = table.File()
        part_table.set_column_from_array(
            'Column names', np.array([column]))
        for key, value in in_table.get_column_attributes(column).items():
            part_table.set_column_from_array(
                'Attribute names', np.array([key]))
            part_table.set_column_from_array(
                'Attribute values', np.array([value]))

        part_tables.append(part_table)

    out_table.vjoin(part_tables)


class SuperNodeAttributes(synode.Node):
    author = 'Daniel Hedendahl <daniel.hedendahl@combine.se>'
    copyright = '(C) 2016 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.TransformMeta)


class GetColumnAttributesTable(SuperNodeAttributes):
    name = 'Get column attributes in Table'
    description = 'Get column attributes in Table.'
    nodeid = 'org.sysess.sympathy_course.getcolumnattributestable'

    inputs = Ports([
        Port.Table('Input Data', name='data')])
    outputs = Ports([
        Port.Table('Attributes', name='attributes')])

    def execute(self, node_context):
        in_table = node_context.input[0]
        out_table = node_context.output[0]
        get_column_attributes(in_table, out_table)


class GetColumnAttributesTables(SuperNodeAttributes):
    name = 'Get column attributes in Tables'
    description = 'Get column attributes in Tables.'
    nodeid = 'org.sysess.sympathy_course.getcolumnattributestables'

    inputs = Ports([
        Port.Tables('Input Data', name='data')])
    outputs = Ports([
        Port.Tables('Attributes', name='attributes')])

    def execute(self, node_context):
        in_tables = node_context.input[0]
        out_tables = node_context.output[0]

        for in_table in in_tables:
            out_table = table.File()
            get_column_attributes(in_table, out_table)
            out_tables.append(out_table)


class SuperNodeSetColAttributes(SuperNodeAttributes):
    parameters = synode.parameters()
    parameters.set_list(
        'columns', label='Column names', value=[0],
        description='Select column with column names',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'attributes', label='Attribute names', value=[0],
        description='Select column with attributes',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'values', label='Attribute values', value=[0],
        description='Select column with values',
        editor=synode.Util.combo_editor().value())


class SetColumnAttributesTable(SuperNodeSetColAttributes):
    """
    :Ref. nodes :ref:`Set column attributes in Tables`
    """
    name = 'Set column attributes in Table'
    description = 'Set column attributes in Table.'
    nodeid = 'org.sysess.sympathy_course.setcolumnattributestable'

    inputs = Ports([
        Port.Table(
            'Table with, at least, three column, one for column '
            'names, another for attribute names and a third for '
            'attribute values', name='attributes'),
        Port.Table('Table with data columns', name='in_data')])
    outputs = Ports([
        Port.Table('Table with updated columns attributes', name='out_data')])

    def adjust_parameters(self, node_context):
        columns = []
        parameters = node_context.parameters
        tablefile = node_context.input['attributes']
        if tablefile.is_valid():
            columns = tablefile.column_names()
        parameters['columns'].list = sorted(columns)
        parameters['attributes'].list = sorted(columns)
        parameters['values'].list = sorted(columns)

    def execute(self, node_context):
        parameters = node_context.parameters
        attr_table = node_context.input['attributes']
        data_table = node_context.input['in_data']
        out_table = node_context.output['out_data']
        out_table.update(data_table)
        set_column_attributes(attr_table, out_table, parameters)


class SetColumnAttributesTables(SuperNodeSetColAttributes):
    """
    :Ref. nodes :ref:`Set column attributes in Table`
    """
    name = 'Set column attributes in Tables'
    description = 'Set column attributes in Tables.'
    nodeid = 'org.sysess.sympathy_course.setcolumnattributestables'

    inputs = Ports([
        Port.Tables('Table with, at least, three column, one for column '
                   'names, another for attribute names and a third for '
                   'attribute values', name='attributes'),
        Port.Tables('List of Tables with data columns', name='in_data')])
    outputs = Ports([
        Port.Tables('List of Tables with updated columns attributes',
                    name='out_data')])

    def adjust_parameters(self, node_context):
        columns = []
        parameters = node_context.parameters
        tablefiles = node_context.input['attributes']
        if tablefiles.is_valid():
            if len(tablefiles) > 0:
                columns = tablefiles[0].column_names()

        parameters['columns'].list = sorted(columns)
        parameters['attributes'].list = sorted(columns)
        parameters['values'].list = sorted(columns)

    def execute(self, node_context):
        parameters = node_context.parameters
        attr_tables = node_context.input['attributes']
        data_tables = node_context.input['in_data']
        out_tables = node_context.output['out_data']

        for attr_table, data_table in zip(attr_tables, data_tables):
            out_table = table.File()
            out_table.update(data_table)
            set_column_attributes(attr_table, out_table, parameters)
            out_tables.append(out_table)


class GetTableAttributes(SuperNodeAttributes):
    name = 'Get Table attributes'
    description = 'Get Table attributes.'
    nodeid = 'org.sysess.sympathy_course.gettableattributes'

    inputs = Ports([
        Port.Table('Table with data.', name='in_data')])
    outputs = Ports([
        Port.Table(
            'Table with a single row where the columns are representing '
            'the exported attributes', name='attributes')])

    def execute(self, node_context):
        in_table = node_context.input[0]
        out_table = node_context.output[0]
        get_table_attributes(in_table, out_table)


class GetTablesAttributes(SuperNodeAttributes):

    name = 'Get Tables attributes'
    description = 'Get Tables attributes.'
    nodeid = 'org.sysess.sympathy_course.gettablesattributes'

    inputs = Ports([
        Port.Tables('Table with data', name='in_data')])
    outputs = Ports([
        Port.Tables(
            'Table with a single row where the columns are representing '
            'the exported attributes', name='attributes')])

    def execute(self, node_context):
        in_tables = node_context.input[0]
        out_tables = node_context.output[0]

        for in_table in in_tables:
            out_table = table.File()
            get_table_attributes(in_table, out_table)
            out_tables.append(out_table)


class SetTableAttributes(SuperNodeAttributes):
    """
    Set the attributes in Table with the headers and values in another Table,
    only the values on the first row.
    """
    name = 'Set Table attributes'
    description = 'Set Table attributes.'
    nodeid = 'org.sysess.sympathy_course.settableattributes'

    inputs = Ports([
        Port.Table(
            'A Table with attributes along the columns. Only the first row of '
            'the Table will be imported as attributes, due to that an '
            'attribute is defined to be a scalar value', name='attributes'),
        Port.Table('Table with data', name='in_data')])
    outputs = Ports([
        Port.Table('Table with updated attribute container', name='out_data')])

    def execute(self, node_context):
        attr_table = node_context.input['attributes']
        data_table = node_context.input['in_data']
        out_table = node_context.output['out_data']
        out_table.update(data_table)

        set_table_attributes(attr_table, out_table)


class SetTablesAttributes(SuperNodeAttributes):
    """
    Set the attributes in Tables with the headers and values in
    attribute Tables, only the values on the first row.
    """
    name = 'Set Tables attributes'
    description = 'Set Tables attributes.'
    nodeid = 'org.sysess.sympathy_course.settablesattributes'

    inputs = Ports([
        Port.Tables(
            'Table with attributes along the columns. Only the first row of '
            'the Table will be imported as attributes, due to that an '
            'attribute is defined to be a scalar value', name='attributes'),
        Port.Tables('Table with data', name='in_data')])
    outputs = Ports([
        Port.Tables(
            'Table with updated attribute container', name='out_data')])

    def execute(self, node_context):
        attr_tables = node_context.input[0]
        data_tables = node_context.input[1]
        out_tables = node_context.output[0]

        for data_table, attr_table in zip(data_tables, attr_tables):
            out_table = table.File()
            out_table.update(data_table)
            set_table_attributes(attr_table, out_table)
            out_tables.append(out_table)
