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
The operation of vertical join, or VJoin, stacks the columns from the incoming
:ref:`Tables` that have the same name vertically upon each other, under the
condition that they exist in all Tables. If the condition is fulfilled the
number of rows in the outgoing Table will be equal to the sum of the number
of rows in the incoming Tables. If there exist no overlap over all Tables the
output will be an empty Table.

In the GUI it is possible to override the overlap requirement and let the node
work in a state where the output will include all columns that exist the
incoming Tables. The columns that do not exist in all Tables are, where they
are missing, represented by dummy columns with the same length as the other
columns in the considered Table. The dummy for a column with numerical values
is filled with NaNs while for a column with strings the elements in the dummy
consist of empty strings. This state is regulated by the
"Complement missing columns"-checkbox.

An index column will be created in the outgoing Table if a name is specified
for the column in the GUI, by default the index column has the name
"VJoin-index". In the index column, elements in the joined output that
originate from the same incoming Table will be given the same index number.
If one wants to do the reversed operation, :ref:`VSplit Table`, the index
column is important. No index column will be created if the specified name
is an empty string.

In the GUI it is also possible to specify the name of an incoming index column,
a column with information about previous VJoin operations. If the specified
index column exists in the incoming Tables the information of the previous join
operations will be regarded when the new index column is constructed. The new
index column will replace the old ones in the output of the node.

An increment will be applied to the outgoing index column if there exist
incoming Tables with the number of rows equal to zero. The size of this
increment can be specified in the GUI of the node, where default value is 0.
The vertical join, or VJoin, is one of two operations that merge the
content of a number of :ref:`Tables` into a new Table. The other operation
in this category is the horizontal join, see :ref:`HJoin Table` to obtain more
information.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags

INDEX = 'VJoin-index'


class VJoinBase(synode.Node):
    parameters = synode.parameters()
    parameters.set_boolean(
        'fill', value=False, label='Complement missing columns',
        description='Select if columns that are not represented in all '
                    'Tables to be complemented with either NaNs or empty '
                    'strings.')
    parameters.set_integer(
        'minimum_increment',
        value=1,
        label='Increment in index column',
        description=('Specify the increment in the outgoing index column '
                     'at the existence of tables with the number of rows '
                     'equal to zero.'),
        editor=synode.Util.bounded_spinbox_editor(0, 1, 1).value())
    parameters.set_string(
        'output_index',
        label='Output index',
        value=INDEX,
        description='Specify name for output index column. Can be left empty.')
    tags = Tags(Tag.DataProcessing.TransformStructure)

    def extra_parameters(self, parameters):
        input_index = ''
        try:
            output_index = parameters['output_index'].value
        except:
            output_index = INDEX
        try:
            minimum_increment = parameters['minimum_increment'].value
        except:
            minimum_increment = 0
        return (input_index, output_index, minimum_increment)


class VJoinTableNode(VJoinBase):
    """
    Vertical join of two Tables.

    :Inputs:
        **port1** : Table
            Table with data to merge.
        **port2** : Table
            Table with data to merge.
    :Outputs:
        **port1** : Table
            Table with merged data.
    :Configuration:
        **Complement missing columns**
            Select if columns that do not exist in all incoming
            Tables are to be complemented or not.
        **Increment in index column**
            Select the size of the increment to the outgoing index
            column if the number of rows in a incoming Table is equal
            to zero. Possible values are 0 or 1.
        **Output index**
            Specify the names of outgoing index column, can be left empty.
    :Opposite node: :ref:`VSplit Table`
    :Ref. nodes: :ref:`VJoin Table Lists`, :ref:`VJoin Tables`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'vjoin_table.svg'

    name = 'VJoin Table'
    description = ('Vertical join of two Tables.')
    nodeid = 'org.sysess.sympathy.data.table.vjointablenode'

    inputs = Ports([
        Port.Table('Input Table 1', name='port1'),
        Port.Table('Input Table 2', name='port2')])
    outputs = Ports([Port.Table('Joined Table', name='port1')])

    def execute(self, node_context):
        """Execute"""
        input_table1 = node_context.input['port1']
        input_table2 = node_context.input['port2']
        output_table = node_context.output['port1']
        input_index, output_index, minimum_increment = self.extra_parameters(
            node_context.parameters)

        output_table.vjoin(
            [input_table1, input_table2],
            input_index,
            output_index,
            node_context.parameters['fill'].value,
            minimum_increment)


class VJoinTableMultipleNode(VJoinBase):
    """
    Pairwise vertical join of two list of Tables.

    :Inputs:
        **port1** : Tables
            Tables with data to merge.
        **port2** : Tables
            Tables with data to merge.
    :Outputs:
        **port1** : Tables
            Tables with merge data.
    :Configuration:
        **Complement missing columns**
            Select if columns that do not exist in all incoming
            Tables are to be complemented or not.
        **Increment in index column**
            Select the size of the increment to the outgoing index
            column if the number of rows in a incoming Table is equal
            to zero. Possible values are 0 or 1.
        **Output index**
            Specify the names of outgoing index column, can be left empty.
    :Opposite node: :ref:`VSplit Tables`
    :Ref. nodes: :ref:`VJoin Table`, :ref:`VJoin Tables`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'vjoin_table.svg'

    name = 'VJoin Table lists'
    description = ('Pairwise vertical join of two list of Tables.')
    nodeid = 'org.sysess.sympathy.data.table.vjointablenodelist'

    inputs = Ports([
        Port.Tables('Input Tables 1', name='port1'),
        Port.Tables('Input Tables 2', name='port2')])
    outputs = Ports([Port.Tables('Joined Tables', name='port1')])

    def execute(self, node_context):
        """Execute"""
        input_tables1 = node_context.input['port1']
        input_tables2 = node_context.input['port2']
        output_tables = node_context.output['port1']
        num_files = len(input_tables1)
        input_index, output_index, minimum_increment = self.extra_parameters(
            node_context.parameters)

        for ctr, (input_table1, input_table2) in enumerate(zip(input_tables1,
                                                           input_tables2)):
            table = output_tables.create()
            table.vjoin(
                [input_table1, input_table2],
                input_index,
                output_index,
                node_context.parameters['fill'].value,
                minimum_increment)
            output_tables.append(table)
            self.set_progress(100.0 * (ctr + 1) / num_files)


class VJoinTablesNode(VJoinBase):
    """
    Vertical join of Tables.

    :Inputs:
        **port1** : Tables
            Tables with data to merge.
    :Outputs:
        **port1** : Table
            Tables with merge data.
    :Configuration:
        **Complement missing columns**
            Select if columns that do not exist in all incoming
            Tables are to be complemented or not.
        **Increment in index column**
            Select the size of the increment to the outgoing index
            column if the number of rows in a incoming Table is equal
            to zero. Possible values are 0 or 1.
        **Output index**
            Specify the names of outgoing index column, can be left empty.
    :Opposite node: :ref:`VSplit Table`
    :Ref. nodes: :ref:`VJoin Table`, :ref:`VJoin Table Lists`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2012 System Engineering Software Society"
    version = '1.0'
    icon = 'vjoin_table.svg'

    name = 'VJoin Tables'
    description = ('Vertical join of Tables.')
    nodeid = 'org.sysess.sympathy.data.table.vjointablenodes'

    inputs = Ports([Port.Tables('Input Tables', name='port1')])
    outputs = Ports([Port.Table('Joined Tables', name='port1')])

    def execute(self, node_context):
        input_tables = node_context.input['port1']
        output_table = node_context.output['port1']
        input_index, output_index, minimum_increment = self.extra_parameters(
            node_context.parameters)

        output_table.vjoin(
            input_tables,
            input_index,
            output_index,
            node_context.parameters['fill'].value,
            minimum_increment)
