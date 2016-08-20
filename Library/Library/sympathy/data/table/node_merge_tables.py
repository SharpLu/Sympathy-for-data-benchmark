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
Merge two tables or two lists of tables using these nodes:
    - :ref:`Merge Table`
    - :ref:`Merge Tables`
"""
from sympathy.api import node
from sympathy.api import node_helper
from sympathy.api import table
from sympathy.api.nodeconfig import Tag, Tags
import pandas
import collections


MERGE_OPERATIONS = collections.OrderedDict([
    ('Union', 'outer'),
    ('Intersection', 'inner'),
    ('Index from A', 'left'),
    ('Index from B', 'right')])


class MergeTableOperation(node_helper.TableOperation):
    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2014 System Engineering Software Society'
    version = '1.0'
    description = 'Merge Tables while matching an Index'
    tags = Tags(Tag.DataProcessing.TransformStructure)
    inputs = ['Input A', 'Input B']
    outputs = ['Output']
    update_using = None

    @staticmethod
    def get_parameters(parameter_group):
        parameter_group.set_list(
            'index', label='Index column',
            values=[0],
            description='Column with indices to match',
            editor=node.Util.combo_editor().value())
        parameter_group.set_list(
            'operation', label='Join operation',
            description='Column with y values.',
            list=MERGE_OPERATIONS.keys(),
            value=[0],
            editor=node.Util.combo_editor().value())

    def adjust_table_parameters(self, in_table, parameter_root):
        column_names = []
        if in_table['Input A'].is_valid():
            column_names = sorted(in_table['Input A'].column_names())
        parameter_root['index'].list = column_names

    def execute_table(self, in_table, out_table, parameter_root):
        index_column = parameter_root['index'].selected
        operation = parameter_root['operation'].selected
        if (in_table['Input A'].is_empty() and not
                in_table['Input B'].is_empty()):
            out_table['Output'].source(in_table['Input B'])
        elif (in_table['Input B'].is_empty() and not
                in_table['Input A'].is_empty()):
            out_table['Output'].source(in_table['Input A'])
        elif (in_table['Input B'].is_empty() and
                in_table['Input A'].is_empty()):
            return
        else:
            table_a = in_table['Input A'].to_dataframe()
            table_b = in_table['Input B'].to_dataframe()

            new_table = pandas.merge(
                table_a, table_b, how=MERGE_OPERATIONS[operation],
                on=index_column)

            out_table['Output'].source(table.File.from_dataframe(new_table))

            attributes_a = in_table['Input A'].get_attributes()
            attributes_b = in_table['Input B'].get_attributes()
            attributes_c = tuple(dict(attributes_a[i].items() +
                                      attributes_b[i].items())
                                 for i in range(2))
            out_table['Output'].set_attributes(attributes_c)


MergeTable = node_helper.table_node_factory(
    'MergeTable', MergeTableOperation,
    'Merge Table', 'org.sysess.data.table.mergetable')

MergeTables = node_helper.tables_node_factory(
    'MergeTables', MergeTableOperation,
    'Merge Tables', 'org.sysess.data.table.mergetables')
