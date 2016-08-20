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
Ensure the existence of one or several signals in :ref:`Tables` by either
getting an exception or adding a dummy signal to the dataset.
"""
import collections

import numpy as np

from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api import exceptions
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


def ensure_columns(in_table, out_table, selection_table, selection_col, mode):
    out_table.update(in_table)
    for column_name in selection_table.get_column_to_array(selection_col):
        if column_name not in out_table:
            exceptions.sywarn(
                "Column {} missing. Creating it with NaN.".format(column_name))
            if mode == 'Exception':
                raise Exception()
            else:
                attr = {'info': 'Missing column'}
                out_table.set_column_from_array(
                    column_name,
                    np.repeat(np.nan, out_table.number_of_rows()),
                    attr)


class EnsureColumnsOperation(synode.Node):
    """
    Ensure the existence of columns in Tables by using an additional
    Table with the name of the columns that must exist. Select to get
    the result of the check as the form of an exception or as an added
    dummy signal. The type of the dummy signal is by default float with
    all elements set to NaN.

    :Inputs:
    :Outputs:
    :Configuration:
    :Opposite node:
    :Ref. nodes: :ref:`Rename columns in Tables`
    """

    name = 'Ensure columns in Tables'
    author = 'Daniel Hedendahl <daniel.hedendahl@combine.se>'
    copyright = '(C) 2014 System Engineering Software Society'
    version = '1.0'
    description = 'Ensure the existence of column in Table.'
    nodeid = 'org.sysess.sympathy.data.table.ensuretablecolumns'
    tags = Tags(Tag.DataProcessing.TransformStructure)

    inputs = Ports([
        Port.Table('Selection', name='selection'),
        Port.Tables('Input Tables', name='tables')])
    outputs = Ports([Port.Tables('Output Table', name='tables')])

    parameters = collections.OrderedDict()
    parameter_group = synode.parameters(parameters)
    parameter_group.set_list(
        'columns', label='Column with column names',
        description=(
            'Name of column with names of the columns that must exist'),
        editor=synode.Util.combo_editor().value())

    parameter_group.set_list(
        'reporting', label='Action of missing columns:',
        plist=['Exception', 'Dummy Signal'], value=[0],
        description='Select action if columns are missing',
        editor=synode.Util.combo_editor().value())

    def adjust_parameters(self, node_context):
        try:
            dictionary = node_context.input['selection']
            parameter_group = synode.parameters(node_context.parameters)
            parameter_group['columns'].list = dictionary.column_names()
        except:
            pass
        return node_context

    def execute(self, node_context):
        parameter_group = synode.parameters(node_context.parameters)
        try:
            selection_col = parameter_group['columns'].selected
        except:
            selection_col = []

        input_files = node_context.input['tables']
        output_files = node_context.output['tables']
        for input_file in input_files:
            output_file = table.File()
            output_file.set_name(input_file.get_name())

            selection_table = node_context.input['selection']
            mode = parameter_group['reporting'].selected

            ensure_columns(input_file, output_file, selection_table,
                           selection_col, mode)

            output_files.append(output_file)
