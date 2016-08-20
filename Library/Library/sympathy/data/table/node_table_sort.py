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
In various programs, like file managers or spreadsheet programs, there do
often exist a functionality, where the data is sorted according to
some specified order of a specific part of the data. This functionality
do also exist in the standard library of Sympathy for Data and is represented
by the two nodes in this category.

The rows in the Tables are sorted according to the ascending/descending order
of a specified sort column. Both the sort column and the sort order have to
be specified in configuration GUI.
"""

from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api import node_helper
from sympathy.api.nodeconfig import Tag, Tags
import numpy as np


class SortOperation(node_helper.TableOperation):
    """Sort table rows according to ascending/descending order of a sort
    column.
    """

    author = 'Greger Cronquist <greger.cronquist@combine.se>'
    copyright = '(c) 2013 Volvo Car Corporation'
    version = '1.1'
    tags = Tags(Tag.DataProcessing.TransformStructure)
    inputs = ['Input']
    outputs = ['Output']
    update_using = None

    @staticmethod
    def get_parameters(parameter_group):
            editor = synode.Util.selectionlist_editor('single').value()
            editor['filter'] = True
            parameter_group.set_list(
                'column', label='Sort column',
                description='Column to sort',
                editor=editor)
            parameter_group.set_list(
                'sort_order', label='Sort order',
                list=['Ascending', 'Descending'], value=[0],
                description='Sort order',
                editor=synode.Util.combo_editor().value())

    def adjust_table_parameters(self, in_table, parameter_root):
        if in_table['Input'].is_valid():
            column_names = sorted(in_table['Input'].column_names())
        else:
            column_names = parameter_root['column'].value_names
        parameter_root['column'].list = column_names

    def execute_table(self, in_table, out_table, parameter_root):
        if in_table['Input'].is_empty():
            return

        column = parameter_root['column'].selected
        data = in_table['Input'].to_recarray()
        idx = np.argsort(data[column], kind='mergesort')
        if parameter_root['sort_order'].selected == 'Descending':
            idx = idx[::-1]

        out_table['Output'].update(table.File.from_recarray(data[idx]))

        out_table['Output'].set_attributes(in_table['Input'].get_attributes())
        out_table['Output'].set_name(in_table['Input'].get_name())


SortTable = node_helper.table_node_factory(
    'SortTable', SortOperation,
    'Sort rows in Table', 'org.sysess.sympathy.data.table.sorttable')


SortTables = node_helper.tables_node_factory(
    'SortTables', SortOperation,
    'Sort rows in Tables', 'org.sysess.sympathy.data.table.sorttables')
