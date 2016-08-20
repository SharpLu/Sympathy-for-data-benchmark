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
The operation of horizontal join, or HJoin, stacks the columns in the incoming
:ref:`Tables` horizontally beside each other. The outgoing Table will have all
the columns from all the incoming Tables. Note that all Tables that should be
hjoined must have the same number of rows.

If a column name exists in both inputs the latter Table (or lower port) will
take precedence and the corresponding column from the former Table (or upper
port) will be lost.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyDataError


def merge_attributes(in_list):
    table_attr = {}
    for elem in in_list:
        table_attr.update(elem.get_table_attributes())

    names = [
        elem.get_name() for elem in in_list if elem.get_name() is not None]
    if names:
        table_name = names[-1]
    else:
        table_name = None

    return table_attr, table_name


class HJoinTable(synode.Node):
    """
    Horizontal join of two Tables into a single Table.

    :Inputs:
        **port1** : Table
            Table with data.
        **port2** : Table
            Table with data.
    :Outputs:
        **port1** : Table
            Table with horizontally joined data.
    :Configuration: No configuration.
    :Opposite node: :ref:`HSplit Table`
    :Ref. nodes: :ref:`HJoin Tables`,
                 :ref:`HJoin list of Tables`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'hjoin_table.svg'

    name = 'HJoin Table'
    description = 'Horizontal join of two Tables'
    nodeid = 'org.sysess.sympathy.data.table.hjointable'
    tags = Tags(Tag.DataProcessing.TransformStructure)

    inputs = Ports([
        Port.Table('Input Table 1', name='port1'),
        Port.Table('Input Table 2', name='port2')])
    outputs = Ports([Port.Table('Joined Table', name='port1')])

    def execute(self, node_context):
        """Execute"""
        tablefile1 = node_context.input['port1']
        tablefile2 = node_context.input['port2']
        if ((tablefile1.number_of_rows() !=
                tablefile2.number_of_rows()) and
            (tablefile1.number_of_columns() and
                tablefile2.number_of_columns())):
            raise SyDataError(
                'Number of rows mismatch in tables ({} vs {})'.format(
                    tablefile1.number_of_rows(),
                    tablefile2.number_of_rows()))
        out_tablefile = node_context.output['port1']
        out_tablefile.hjoin(tablefile1)
        out_tablefile.hjoin(tablefile2)

        table_attr, table_name = merge_attributes(
            [tablefile1, tablefile2])
        out_tablefile.set_table_attributes(table_attr)
        out_tablefile.set_name(table_name)


class HJoinTables(synode.Node):
    """
    Pairwise horizontal join of two lists of Tables into a single list of
    Tables. I.e. The first Table on the upper port is hjoined with the first
    Table on the lower port and so on.

    :Inputs:
        **port1** : Tables
            List of Tables with data.
        **port2** : Tables
            List of Tables with data.
    :Outputs:
        **port1** : Tables
            List of Tables with pairwise horizontally joined data from the
            incoming lists of Tables.
    :Configuration: No configuration
    :Opposite node: :ref:`HSplit Tables`
    :Ref. nodes: :ref:`HJoin Table`,
                 :ref:`HJoin list of Tables`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'hjoin_table.svg'

    name = 'HJoin Tables'
    description = 'Pairwise horizontal join of two list of Tables.'
    nodeid = 'org.sysess.sympathy.data.table.hjointables'
    tags = Tags(Tag.DataProcessing.TransformStructure)

    inputs = Ports([
        Port.Tables('Input Tables 1', name='port1'),
        Port.Tables('Input Tables 2', name='port2')])
    outputs = Ports([Port.Tables('Joined Tables', name='port1')])

    def execute(self, node_context):
        """Execute"""
        in_files1 = node_context.input['port1']
        in_files2 = node_context.input['port2']
        out_tablefiles = node_context.output['port1']

        for file1_item, file2_item in zip(in_files1,
                                          in_files2):
            out_tablefile = out_tablefiles.create()
            out_tablefile.hjoin(file1_item)
            out_tablefile.hjoin(file2_item)

            table_attr, table_name = merge_attributes(
                [file1_item, file2_item])
            out_tablefile.set_table_attributes(table_attr)
            out_tablefile.set_name(table_name)

            out_tablefiles.append(out_tablefile)


class HJoinTablesSingle(synode.Node):
    """
    Horizontal join of all incoming Tables into a single outgoing Table.
    Columns from Tables later in the list will take precedence in the case when
    a certain column name exists in two or more Tables.

    :Inputs:
        **port1** : Tables.
            List of Tables with data.
    :Outputs:
        **port1** : Table
            Table with horizontally joined data from the incoming
            list of Tables.
    :Configuration: No configuration
    :Opposite node: :ref:`HSplit Table`
    :Ref. nodes: :ref:`HJoin Table`, :ref:`HJoin Tables`
    """

    author = "Greger Cronquist <greger.cronquist@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'hjoin_table.svg'

    name = 'HJoin list of Tables'
    description = 'HJoin Tables to Table'
    nodeid = 'org.sysess.sympathy.data.table.hjointablessingle'
    tags = Tags(Tag.DataProcessing.TransformStructure)

    inputs = Ports([Port.Tables('Input Tables', name='port1')])
    outputs = Ports([Port.Table('Joined Table', name='port1')])

    def execute(self, node_context):
        """Execute"""
        in_files = node_context.input['port1']
        out_tablefile = node_context.output['port1']

        for item in in_files:
            out_tablefile.hjoin(item)

        table_attr, table_name = merge_attributes(in_files)
        out_tablefile.set_table_attributes(table_attr)
        out_tablefile.set_name(table_name)
