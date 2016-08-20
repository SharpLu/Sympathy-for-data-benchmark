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
The operation of vertical split, or VSplit, performs a rowwise split of
:ref:`Tables`.

If an index column is specified in the configuration GUI the split will be
performed according to defined groups in this column. Otherwise the
node will place every row of the incoming Table into separate Tables in
the outgoing list. The index column, if present, needs to be grouped by index.

In the index column the elements of the rows, that belong to the same group,
will have the same integer value. An example of an index column is created
by the :ref:`VJoin Table` node, where the elements in the joined output that
originates from the same incoming Table will be given the same index number.
The default name of the index column is "VJoin-index", which also is the
default name given to the index column created by the :ref:`VJoin Table`
nodes.

If the specified index column does not exist in the incoming Table the node
will treat this as no index column has been specified. This default state
can be changed into a "Require Input Index"-state, which can be regulated by
a checkbox in the GUI. If an index colum is required and is not found, an
exception will be raised and the execution fails.

In the GUI it is possible to switch the node to a state where split columns
which contain only NaNs or empty strings are removed. This is the reversed
action of the creation of complements for missing columns preformed in the
:ref:`VJoin Table` node.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyDataError


INDEX = 'VJoin-index'


class VSplitBase(synode.Node):
    parameters = synode.parameters()
    parameters.set_boolean(
        'remove_fill', value=False, label='Remove complement columns',
        description=('Remove split columns which contain only '
                     'NaN or empty strings.'))
    parameters.set_string(
        'input_index',
        label='Input Index',
        value=INDEX,
        description='Choose name for grouped index column. Can be left empty.')
    parameters.set_boolean(
        'require_index', value=False, label='Require input index',
        description='Require Input Index vector to be present.')
    tags = Tags(Tag.DataProcessing.TransformStructure)

    def extra_parameters(self, parameters):
        try:
            input_index = parameters['input_index'].value
        except:
            input_index = INDEX
        return input_index


class VSplitTableNode(VSplitBase):
    """
    Vertical split of Table into Tables.

    :Inputs:
        **port1** : Table
            Table with data to split.
    :Outputs:
        **port1** : Tables
            Tables with split data.
    :Configuration:
        **Require input index**
            Turn on or off the requirement of an index column.
        **Remove fill**
            Turn on or off if split columns that contain only NaNs or
            empty strings are going to be removed or not.
        **Input index**
            Specify the name of the incoming index column, can be left empty.
            Needs to be grouped by index.
    :Opposite node: :ref:`VJoin Table`
    :Ref. nodes: :ref:`VSplit Tables`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'vsplit_table.svg'

    name = 'VSplit Table'
    description = 'Vertical split of Table into Tables.'
    nodeid = 'org.sysess.sympathy.data.table.vsplittablenode'

    inputs = Ports([Port.Table('Input Table', name='port1')])
    outputs = Ports([Port.Tables('Split Tables', name='port1')])

    def execute(self, node_context):
        """Execute"""
        input_table = node_context.input['port1']
        output_tables = node_context.output['port1']
        input_index = self.extra_parameters(node_context.parameters)
        require_index = node_context.parameters['require_index'].value

        if require_index and input_index not in input_table:
            raise SyDataError('Input: missing Input Index "{0}"'.format(
                input_index))

        input_table.vsplit(
            output_tables,
            input_index,
            node_context.parameters['remove_fill'].value)


class VSplitTablesNode(VSplitBase):
    """
    Vertical split of Tables into Tables.

    :Inputs:
        **port1** : Tables
            Table with data to split.
    :Outputs:
        **port1** : Tables
            Tables with split data.
    :Configuration:
        **Require input index**
            Turn on or off the requirement of an index column.
        **Remove fill**
            Turn on or off if split columns that contain only NaNs or
            empty strings are going to be removed or not.
        **Input index**
            Specify the name of the incoming index column, can be left empty.
            Needs to be grouped by index.
    :Opposite node: :ref:`VJoin Table Lists`
    :Ref. nodes: :ref:`VSplit Table`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'vsplit_table.svg'

    name = 'VSplit Tables'
    description = ('Vertical split of Tables into Tables.')
    nodeid = 'org.sysess.sympathy.data.table.vsplittablenodes'

    inputs = Ports([Port.Tables('Input Tables', name='port1')])
    outputs = Ports([Port.Tables('Split Tables', name='port1')])

    def execute(self, node_context):
        """Execute"""
        input_list = node_context.input['port1']
        output_tables = node_context.output['port1']
        input_index = self.extra_parameters(node_context.parameters)
        number_of_files = len(input_list)
        require_index = node_context.parameters['require_index'].value

        for i, table in enumerate(input_list):
            if require_index and input_index not in table:
                raise SyDataError(
                    'Input[{0}]: missing Input Index "{1}"'.format(
                        i, input_index))

        for i, table in enumerate(input_list):
            table.vsplit(
                output_tables,
                input_index,
                node_context.parameters['remove_fill'].value)
            self.set_progress(100.0 * (i + 1) / number_of_files)
