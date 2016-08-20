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
To compare the number of rows in two :ref:`Tables` and resize one of them,
in order to have two Tables with equal numbers of rows, is the functionality
of the nodes in the considered category. For example, this may be helpful if
one would like to horisontal join two Tables with different number of rows,
which is not possible according to the definition of a Table,
see :ref:`Tables` and :ref:`HJoin Table`.

In the procedure of the node, the Table connected to the upper of the two
inputs is used as reference while the Table coming in through the lower port
is the one that is going to be modified. The modification can either be a
contraction or an extension of the Table depending if it is longer or shorter
than the reference Table, respectively.

The extension will be preformed according to one of the following strategies:
    - Use last value
    - Fill with zeroes (or empty strings/dates or similar)
    - Fill with NaNs (or None or similar)

"""
from sympathy.api import table
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class MatchTablesBase(object):
    author = 'Greger Cronquist <greger.cronquist@sysess.org'
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    icon = 'match_tables.svg'
    tags = Tags(Tag.DataProcessing.TransformStructure)

    parameters = synode.parameters()
    parameters.set_list(
        'fill', value=[0], label='Extend values',
        desciption=(
            'Specify the values to use if the input has to be extended.'),
        plist=['Last value', '0.0 or empty string', 'np.NaN or empty string'],
        editor=synode.Util.combo_editor().value())

    def _match_table(self, parameters, guide, intable):
        guide_length = guide.number_of_rows()
        table_length = intable.number_of_rows()
        output = intable.to_dataframe()
        if guide_length < table_length:
            output = output[:guide_length]
        elif guide_length > table_length:
            fill_method = parameters['fill'].value[0]
            if fill_method == 0:
                # Repeat last value
                output = output.reindex(range(guide_length), method='ffill')
            elif fill_method == 1:
                # Fill with zeroes
                output = output.reindex(range(guide_length), fill_value=0)
            elif fill_method == 2:
                # Fill with NaN
                output = output.reindex(range(guide_length))

        output_table = table.File.from_dataframe(output)
        output_table.set_attributes(intable.get_attributes())
        output_table.set_name(intable.get_name())
        return output_table


class MatchTwoTables(MatchTablesBase, synode.Node):
    """
    Match column lengths in Table with column lengths of reference Table.

    :Inputs:
        **Guide** : Table
            Table to match with
        **Input** : Table
            Table to cut or extend
    :Outputs:
        **Output** : Table
            Updated Table
    :Configuration:
        **Extend values** :
            Specify the values to use if the input has to be extended.
    """

    name = 'Match Table lengths'
    nodeid = 'org.sysess.sympathy.data.table.matchtwotables'
    description = 'Match the column lengths of two Tables.'
    inputs = Ports([
        Port.Table('Guide', name='guide'),
        Port.Table('Input Table', name='input')])
    outputs = Ports([Port.Table('Length matched Table', name='output')])

    def __init__(self):
        super(MatchTwoTables, self).__init__()

    def execute(self, node_context):
        output = self._match_table(node_context.parameters,
                                   node_context.input['guide'],
                                   node_context.input['input'])
        node_context.output['output'].update(output)


class MatchTwoTablesMultiple(MatchTablesBase, synode.Node):
    """
    Pairwise match of column lengths in Tables with column lengths of reference
    Tables.

    :Inputs:
        **Guide** : Tables
            List of Tables to match with
        **Input** : Tables
            List of Tables to cut or extend
    :Outputs:
        **Output** : Tables
            List of updated Tables
    :Configuration:
        **Extend values** :
            Specify the values to use if the input has to be extended.
    """

    name = 'Match Tables lengths'
    nodeid = 'org.sysess.sympathy.data.table.matchtwotablesmultiple'
    description = ('Pairwise match the column lengths of the elements '
                   'in two lists of Tables.')

    inputs = Ports([
        Port.Tables('Guide', name='guide'),
        Port.Tables('Input Tables', name='input')])
    outputs = Ports([Port.Tables('Length matched Tables', name='output')])

    def __init__(self):
        super(MatchTwoTablesMultiple, self).__init__()

    def execute(self, node_context):
        number_of_tables = len(node_context.input['guide'])
        for idx, (guide, table_) in enumerate(zip(
                node_context.input['guide'], node_context.input['input'])):
            output_table = self._match_table(
                node_context.parameters, guide, table_)
            node_context.output['output'].append(output_table)
            self.set_progress(100.0 * (idx + 1.0) / number_of_tables)
