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
Create and HJoin a column containing a group index given an index column.For
example, with an input table with 15 rows and an index column with values
[4, 7, 11] a group index column with values
[0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3] is created and added to the
output table.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
import numpy as np
from sympathy.api import table, adaf
from sympathy.api import node_helper
from sympathy.api.exceptions import sywarn

INDEX = 'VJoin-index'


def deprecationwarn():
    sywarn(
        "This node is being deprecated in an upcoming release of Sympathy. "
        "Please remove the node from your workflow.")


def create_index_column(indices, length):
    """
    Create the index column. indices is a numpy array.
    """
    i1 = np.append([0], indices)
    i2 = np.append(indices, [length])
    index = np.zeros(length, dtype=np.int)
    for group_number, (start, end) in enumerate(zip(i1, i2)):
        index[start:end] = group_number
    return index


class CreateTableIndexBase(synode.Node):
    author = 'Greger Cronquist <greger.cronquist@sysess.org'
    copyright = '(c) 2013 System Engineering Software Society'
    description = (
        'Create and HJoin a column containing a group index given an index '
        'column.')
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    parameters = synode.parameters()
    parameters.set_list(
        'index_column', label='Input Index Column',
        description='Column that contains indices',
        editor=synode.Util.combo_editor().value())
    parameters.set_string(
        'output_index', label='Output Index',
        description='Choose a name for the created index column',
        value=INDEX)


class CreateTableIndex(CreateTableIndexBase):
    """
    EXPERIMENTAL Create Table Index from Indices
    """
    name = 'Create Table Index From Indices (deprecated)'
    nodeid = 'org.sysess.sympathy.data.table.createtableindex'

    inputs = Ports([Port.Table('Indices', name='indices'),
                    Port.Table('Input Table', name='input')])
    outputs = Ports([Port.Table('Output Table')])

    def adjust_parameters(self, node_context):
        deprecationwarn()
        if node_context.input['indices'].is_valid():
            column_names = node_context.input['indices'].column_names()
            node_context.parameters['index_column'].list = column_names
        return node_context

    def execute(self, node_context):
        deprecationwarn()
        index_column = node_context.parameters['index_column'].selected
        created_column = node_context.parameters['output_index'].value
        length = node_context.input['input'].number_of_rows()
        if length != 0:
            input_indices_data = node_context.input[
                'indices'].get_column_to_array(index_column)
            node_context.output[0].update(node_context.input['input'])
            node_context.output[0].set_column_from_array(
                created_column,
                create_index_column(input_indices_data, length))


class CreateTablesIndex(CreateTableIndexBase):
    """
    EXPERIMENTAL Create Table Index from Indices
    Tables are handled pairwise.
    """
    name = 'Create Tables Index From Indices (deprecated)'
    nodeid = 'org.sysess.sympathy.data.table.createtablesindex'

    inputs = Ports([Port.Tables('Indices', name='indices'),
                    Port.Tables('Input Tables', name='input')])
    outputs = Ports([Port.Tables('Output Tables')])

    def adjust_parameters(self, node_context):
        deprecationwarn()
        inport = node_context.input['indices']
        if inport.is_valid() and len(inport):
            column_names = inport[0].column_names()
            node_context.parameters['index_column'].list = column_names
        return node_context

    def execute(self, node_context):
        deprecationwarn()
        index_column = node_context.parameters['index_column'].selected
        created_column = node_context.parameters['output_index'].value
        for indices, input_table in zip(node_context.input['indices'],
                                        node_context.input['input']):

            input_indices_data = indices.get_column_to_array(index_column)
            length = input_table.number_of_rows()
            output = table.File(source=input_table)
            output.set_column_from_array(
                created_column,
                create_index_column(input_indices_data, length))
            node_context.output[0].append(output)


class CreateADAFsIndex(synode.Node):
    author = 'Greger Cronquist <greger.cronquist@sysess.org'
    copyright = '(c) 2013 System Engineering Software Society'
    description = (
        'Create and HJoin a column containing a group index given an index '
        'column.')
    version = '1.0'
    name = 'Create ADAFs Index From Indices (deprecated)'
    nodeid = 'org.sysess.sympathy.data.table.createadafsindex'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.Tables('Indices', name='indices'),
                    Port.ADAFs('Input ADAFs', name='input')])
    outputs = Ports([Port.ADAFs('Output ADAFs')])

    parameters = synode.parameters()
    has_custom_widget = False
    parameter_group = parameters.create_group(node_helper.ADAF_GROUP)
    node_group = parameters.create_group(node_helper.CHILD_GROUP)
    parameter_group.set_list(
        'system', label='System',
        values=[0],
        description='System',
        editor=synode.Util.combo_editor().value())
    parameter_group.set_list(
        'raster', label='Raster',
        values=[0],
        description='Raster',
        editor=synode.Util.combo_editor().value())

    node_group.set_list(
        'index_column', label='Input Index Column',
        description='Column that contains indices',
        editor=synode.Util.combo_editor().value())
    node_group.set_string(
        'output_index', label='Output Index',
        description='Choose a name for the created index column',
        value=INDEX)

    def exec_parameter_view(self, node_context):
        return node_helper.ADAFSelection(node_context, self)

    def adjust_parameters(self, node_context):
        deprecationwarn()
        parameters = node_context.parameters
        inport0 = node_context.input[0]
        inport1 = node_context.input[1]
        if inport1.is_valid() and len(inport1):
            first_file = inport1[0]
            systems = sorted(first_file.sys.keys())
            first_system = first_file.sys[systems[0]]
            rasters = sorted(first_system.keys())
            parameters[node_helper.ADAF_GROUP]['system'].list = systems
            parameters[node_helper.ADAF_GROUP]['raster'].list = rasters
            if inport0.is_valid() and len(inport0):
                parameters[node_helper.CHILD_GROUP]['index_column'].list = (
                    inport0[0].column_names())
        return node_context

    def execute(self, node_context):
        deprecationwarn()
        if ((len(node_context.input['indices']) == 0) or
                len(node_context.input['input']) == 0):
            return
        parameters = node_context.parameters
        index_column = parameters[
            node_helper.CHILD_GROUP]['index_column'].selected
        created_column = parameters[
            node_helper.CHILD_GROUP]['output_index'].value
        raster = parameters[node_helper.ADAF_GROUP]['raster'].selected
        system = parameters[node_helper.ADAF_GROUP]['system'].selected
        factor = 100.0 / len(node_context.input['indices'])
        for idx, (indices, input_adaf) in enumerate(
                zip(node_context.input['indices'],
                    node_context.input['input'])):

            input_indices_data = indices.get_column_to_array(index_column)
            out_adaf = adaf.File(source=input_adaf)
            length = out_adaf.sys[system][raster].number_of_rows()
            out_adaf.sys[system][raster].create_signal(
                created_column,
                create_index_column(input_indices_data, length))
            node_context.output[0].append(out_adaf)
            self.set_progress((idx + 1) * factor)
