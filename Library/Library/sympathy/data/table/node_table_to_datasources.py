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
Convert a table with file paths to a list of data sources. The list will
contain one element for each row of the incoming table.

In the configuration GUI it is possible to select the column that contains the
file paths.
"""
from sympathy.api import node as synode
from sympathy.api import datasource as dsrc
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import sywarn


class TableToDsrc(synode.Node):
    """
    Exportation of data from Table to Datasources.

    :Ref. nodes: :ref:`Datasources to table`
    """

    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    icon = 'table2dsrc.svg'

    name = 'Table to Datasources'
    description = ('Convert a table with file paths into a list of data '
                   'sources pointing to those files.')
    nodeid = 'org.sysess.sympathy.data.table.tabletodsrcs'
    tags = Tags(Tag.DataProcessing.Convert)

    inputs = Ports([Port.Table('Table containing a column of filepaths.')])
    outputs = Ports([Port.Datasources('Datasources')])

    parameters = synode.ParameterRoot()
    parameters.set_list(
        'files', label='File names',
        description='Column containing the filenames',
        editor=synode.Util.combo_editor().value())

    def adjust_parameters(self, node_context):
        if node_context.input[0].is_valid():
            node_context.parameters['files'].list = (
                node_context.input[0].column_names())
        else:
            node_context.parameters['files'].list = (
                node_context.parameters['files'].value_names)
        return node_context

    def execute(self, node_context):
        filenames_col = node_context.parameters['files'].selected
        infile = node_context.input[0]
        outfile_list = node_context.output[0]
        if filenames_col in infile:
            filenames = infile.get_column_to_array(filenames_col)
        else:
            sywarn('The selected column does not seem to exist. '
                   'Assuming empty input.')
            filenames = []

        for f in filenames:
            outfile = dsrc.File()
            outfile.encode_path(f)
            outfile_list.append(outfile)


class TablesToDsrc(synode.Node):
    """
    Exportation of data from Table to Datasources.

    :Ref. nodes: :ref:`Datasources to table`
    """

    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    icon = 'table2dsrc.svg'

    name = 'Tables to Datasources'

    description = ('Convert a list of tables with file paths into a list of '
                   'data sources pointing to those files.')

    nodeid = 'org.sysess.sympathy.data.table.tablestodsrcs'
    tags = Tags(Tag.DataProcessing.Convert)

    inputs = Ports([Port.Tables('Tables containing a column of filepaths.')])
    outputs = Ports([Port.Datasources('Datasources')])

    parameters = synode.ParameterRoot()
    parameters.set_list(
        'files', label='File names',
        description='Column containing the filenames',
        editor=synode.Util.combo_editor().value())

    def adjust_parameters(self, node_context):
        input_list = node_context.input[0]

        if input_list.is_valid():
            node_context.parameters['files'].list = []
            if len(input_list):
                node_context.parameters['files'].list = (
                    input_list[0].column_names())
        else:
            node_context.parameters['files'].list = (
                node_context.parameters['files'].value_names)
        return node_context

    def execute(self, node_context):
        filenames_col = node_context.parameters['files'].selected
        outfile_list = node_context.output[0]
        for infile in node_context.input[0]:
            filenames = infile.get_column_to_array(filenames_col)
            for f in filenames:
                outfile = dsrc.File()
                outfile.encode_path(f)
                outfile_list.append(outfile)
