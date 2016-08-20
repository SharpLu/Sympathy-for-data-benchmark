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
Nodes with operations on truth tables, i.e. tables with a boolean column named
*filter*.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api import table
from sympathy.api.exceptions import SyDataError, sywarn


def deprecationwarn():
    sywarn(
        "This node is being deprecated in an upcoming release of Sympathy. "
        "Please remove the node from your workflow.")


class RestoreFiltersTableSuper(synode.Node):
    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 Sysem Engineering Society'
    version = '1.0'
    icon = 'restore_filter.svg'
    tags = Tags(Tag.Hidden.Deprecated)


class RestoreTruthTable(RestoreFiltersTableSuper):
    """
    Given Two Truth Table (with columns called 'filter'), calculate a new
    filter table as First[First['filter'] == True] = Second['filter'].
    Note the largest Table is the First.
    """
    name = 'Restore Truth Table (deprecated)'
    description = (
        "Given Two Truth Table (with columns called 'filter'), calculate "
        "a new filter table as "
        "First[First['filter'] == True] = Second['filter']. "
        "Note the largest Table is the First.")
    nodeid = 'org.sysess.sympathy.data.table.restoretruthtable'

    inputs = Ports([Port.Table('Second'), Port.Table('First')])
    outputs = Ports([Port.Table('Output')])

    def validate_data(self, node_context):
        return (
            node_context.input[0].number_of_rows() <=
            node_context.input[1].number_of_rows())

    def execute(self, node_context):
        deprecationwarn()
        if not self.validate_data(node_context):
            raise SyDataError('Largest table must be first.')
        try:
            first = node_context.input[1].get_column_to_array('filter')
        except KeyError:
            raise SyDataError('Filter column must be in First table.')
        try:
            second = node_context.input[0].get_column_to_array('filter')
        except KeyError:
            raise SyDataError('Filter column must be in Second table.')

        first[first == True] = second
        node_context.output[0].set_column_from_array('filter', first)


class RestoreListFromTruthTable(RestoreFiltersTableSuper):
    """
    Given the the output of Filter Tables Predicate this node creates a list of
    Tables as long as the Output Index Table with empty tables where it has
    False values.
    """
    name = 'Restore List from truth Table (deprecated)'
    description = (
        'Given the the output of Filter Tables Predicate this node '
        'creates a list of Tables as long as the Output Index Table '
        'with empty tables where it has False values.')
    nodeid = 'org.sysess.sympathy.data.table.restorelistfromtruthtable'

    inputs = Ports([Port.Table('Index Table'), Port.Tables('Input')])
    outputs = Ports([Port.Tables('Output')])

    def validate_data(self, node_context):
        list_length = len(node_context.input[1])
        try:
            filter_column = node_context.input[0].get_column_to_array('filter')
        except KeyError:
            raise SyDataError('Filter column must be in Index table.')
        to_include = len(filter_column[filter_column == True])
        return list_length == to_include

    def execute(self, node_context):
        deprecationwarn()
        if not self.validate_data(node_context):
            raise SyDataError('Filter must match list length.')

        input_list = node_context.input[1]
        output_list = node_context.output[0]
        filter_column = node_context.input[0].get_column_to_array('filter')
        input_index = 0
        for include in filter_column:
            output = table.File()
            if include:
                output.update(input_list[input_index])
                input_index += 1
            output_list.append(output)


class RestoreListFromTruthTableDefault(RestoreFiltersTableSuper):
    """
    Given the the output of Filter Tables Predicate this node creates a list of
    Tables as long as the Output Index Table with a default Table where it has
    False values.
    """
    name = 'Restore List from truth Table with Default Table (deprecated)'
    description = (
        'Given the the output of Filter Tables Predicate this node '
        'creates a list of Tables as long as the Output Index Table '
        'with a default Table where it has False values.')
    nodeid = 'org.sysess.sympathy.data.table.restorelistfromtruthtabledefault'

    inputs = Ports([
        Port.Table('Index Table'),
        Port.Table('Default'),
        Port.Tables('Input')])
    outputs = Ports([Port.Tables('Output')])

    def validate_data(self, node_context):
        list_length = len(node_context.input[2])
        try:
            filter_column = node_context.input[0].get_column_to_array('filter')
        except KeyError:
            raise SyDataError('Filter column must be in Index table.')
        to_include = len(filter_column[filter_column == True])
        return list_length == to_include

    def execute(self, node_context):
        deprecationwarn()
        if not self.validate_data(node_context):
            raise SyDataError('Filter must match list length.')

        input_list = node_context.input[2]
        default = node_context.input[1]
        output_list = node_context.output[0]
        filter_column = node_context.input[0].get_column_to_array('filter')
        input_index = 0
        for include in filter_column:
            output = table.File()
            if include:
                output.update(input_list[input_index])
                input_index += 1
            else:
                output.update(default)
            output_list.append(output)
