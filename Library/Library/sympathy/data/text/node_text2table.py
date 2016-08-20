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
Convert Text(s) into Table(s). The rows of the incoming Text will be rows in
the resulting output Table.
"""
import numpy as np
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags

NAME = 'Text'


class Texts2Tables(synode.Node):
    """
    :Inputs:
        **texts** : Texts
            Texts with data
    :Outputs:
        **tables** : Tables
            Tables with data
    :Configuration:
        **Output name**
            Specify the name of the output column. Must be a legal name.
    :Opposite node: :ref:`Get Item Text`
    :Ref. nodes:
    """

    parameters = synode.parameters()
    parameters.set_string(
        'name',
        label='Output name',
        value=NAME,
        description='Specify name for output column. Must be a legal name.')

    name = 'Texts to Tables'
    description = 'Convert Texts of Tables.'
    inputs = Ports([Port.Texts('Input Texts', name='texts')])
    outputs = Ports([Port.Tables('Tables with input Texts', name='tables')])

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2013 System Engineering Software Society'
    nodeid = 'org.sysess.sympathy.data.text.texts2tables'
    version = '0.1'
    icon = 'text2table.svg'
    tags = Tags(Tag.DataProcessing.Convert)

    def __init__(self):
        super(Texts2Tables, self).__init__()

    def execute(self, node_context):
        name = node_context.parameters['name'].value
        output = node_context.output['tables']
        for text in node_context.input['texts']:
            table = output.create()
            Text2Table.fill_table_with_text(text, table, name)
            output.append(table)


class Text2Table(synode.Node):
    """
    :Inputs:
        **text** : Text
            Text with data
    :Outputs:
        **table** : Table
            Table with data
    :Configuration:
        **Output name**
            Specify the name of the output column. Must be a legal name.
    :Opposite node: :ref:`Get Item Text`
    :Ref. nodes:
    """

    parameters = synode.parameters()
    parameters.set_string(
        'name',
        label='Output name',
        value=NAME,
        description='Specify name for output column. Must be a legal name.')

    name = 'Text to Table'
    description = 'Convert Text of Table.'
    inputs = Ports([Port.Text('Input Text', name='text')])
    outputs = Ports([Port.Table('Table with input Text', name='table')])

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2013 System Engineering Software Society'
    nodeid = 'org.sysess.sympathy.data.text.text2table'
    version = '0.1'
    icon = 'text2table.svg'
    tags = Tags(Tag.DataProcessing.Convert)

    def __init__(self):
        super(Text2Table, self).__init__()

    def execute(self, node_context):
        name = node_context.parameters['name'].value
        table = node_context.output['table']
        text = node_context.input['text']
        self.fill_table_with_text(text, table, name)

    @staticmethod
    def fill_table_with_text(text, table, name):
        table.set_column_from_array(
            name,
            np.array(text.get().splitlines()))
