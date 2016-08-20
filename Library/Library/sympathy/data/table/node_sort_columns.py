# -*- coding: utf-8 -*-
# Copyright (c) 2015, System Engineering Software Society
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
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
from sympathy.api import node
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class SortColumnsInTable(node.Node):
    """
    Sort the columns in incoming table alphabetically. Output table will have
    the same columns with the same data but ordered differently.
    """

    name = 'Sort columns in Table'
    author = u'Magnus Sandén <magnus.sanden@gmail.com>'
    copyright = 'Copyright (c) 2015 Combine'
    version = '1.0'
    description = "Sort the columns in incoming table alphabeticaly."
    nodeid = 'org.sysess.sympathy.data.table.sortcolumns'
    tags = Tags(Tag.DataProcessing.TransformStructure)

    inputs = Ports([
        Port.Table('Table with columns in unsorted order', name='input')])
    outputs = Ports([
        Port.Table('Table with columns in sorted order', name='output')])

    def execute(self, node_context):
        input_table = node_context.input['input']
        output_table = node_context.output['output']
        for column in sorted(input_table.column_names()):
            output_table.set_column_from_array(
                column, input_table.get_column_to_array(column))
        output_table.set_attributes(input_table.get_attributes())
        output_table.set_name(input_table.get_name())
