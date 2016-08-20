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
To collect tabulated values in a lookup table with help of keywords, or
keyvalues, is a commonly known database operation. The considered node
adds this functionality to Sympathy for Data.

Into the node a lookup table and a control table are distributed through
the upper and the lower input ports, respectively. The control table must
include a number of columns with keyswords/keyvalues for the lookup operation.
Each of these control columns has to be paired with a corresponding column
in the lookup table. The definition of pairs is controlled from in the
configuration GUI of the node.

During execution of the node, the routine steps through the rows of the
selected subset of control columns and try to find a match among the all
rows in the corresponding subset in the lookup table. If there is a match,
the current row in the lookup table, all columns included, is copied to
the matching row in the control table. If no match is found an exception
will be raised and the execution of the node is stoped, i.e. all rows in
the control table subset must be matched.

In the configuration GUI one can choose to treat a defined column pair as
event columns. The event columns will typically consist of date or time data
when something happend. But in theory can include any other sortable data.

When an event column pair has been defined, each row of in this control table
column will be matched with the latest preceding event in the lookup table
column. For all other columns the lookup is performed as described above.
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api import table

from sylib.lookup_gui import LookupWidget
from sylib.lookup import apply_index_datacolumn_and_write_to_file


class LookupDefinition(object):
    description = "Lookup and match data."
    author = ("Alexander Busck <alexander.busck@sysess.org>, "
              "Magnus Sanden <magnus.sanden@combine.se>")
    copyright = "(C)2013 System Engineering Software Society"
    version = "1.0"

    parameters = synode.ParameterRoot()
    parameters.set_list('template_columns', value=[])
    parameters.set_list('lookupee_columns', value=[])
    parameters.set_integer('event_column', value=-1)
    parameters.set_boolean(
        'perfect_match', value=True, label='Require perfect match',
        description=("If checked, each row in the lookupee table has "
                     "to match exactly one row in the lookup table."))


def get_files(node_context):
    try:
        lookup_file = node_context.input['lookup']
    except KeyError:
        lookup_file = None
    try:
        lookupee_file = node_context.input['lookupee']
    except KeyError:
        lookupee_file = None
    try:
        out_file = node_context.output['out']
    except KeyError:
        out_file = None
    return lookup_file, lookupee_file, out_file


class LookupTableNode(synode.Node, LookupDefinition):
    """
    Collect datavalues in a lookup table with help of a control table. The
    output includes the collected data togther with content of the control
    table.

    :Inputs:
        **loookup** : Table
            Table with data stored as a lookup table.
        **lookupee** : Table
            Table with a number of columns with keywords, or keyvalues.
    :Outputs:
        *out* : Table
            Table with the collected data from the lookup table together with
            content of the lookupee table.
    :Configuration:
        **Lookup columns**
            A list with all the columns in the lookup table. Select a column
            from the lookup table that should be pair with a column from
            the lookupee column.
        **Lookupee columns**
            A list with all the columns in the control table. Select a column
            from the lookupee table that should be paired with a column from
            the lookup table.
        **Add lookup**
            Press add lookup to register a pair of the two selected columns
            among the lookup columns and the lookupee columns.
        **Remove lookup**
            Remove the selected pair in the locked columns table.
        **Locked columns table**
            Lists all the registered lookup pairs. Use the checkboxes under
            event column to define a pair as event columns.
    :Opposite node: None
    :Ref. nodes: None
    """

    name = "Lookup Table"
    nodeid = "org.sysess.sympathy.data.table.lookuptable"
    tags = Tags(Tag.DataProcessing.TransformStructure)

    inputs = Ports([Port.Table("Lookup table", name="lookup"),
                    Port.Table("Lookupee", name="lookupee")])
    outputs = Ports([Port.Table("Output Table", name="out")])

    def exec_parameter_view(self, node_context):
        lookup_file, lookupee_file, out_file = get_files(node_context)
        return LookupWidget(
            node_context.parameters, lookup_file, lookupee_file, out_file)

    def execute(self, node_context):
        lookup_file, lookupee_file, out_file = get_files(node_context)

        apply_index_datacolumn_and_write_to_file(
            node_context.parameters, lookup_file, lookupee_file, out_file)
        out_file.set_attributes(lookup_file.get_attributes())


class LookupTablesNode(synode.Node, LookupDefinition):
    """
    Collect datavalues in a lookup table with help of a control table. The
    output includes the collected data togther with content of the control
    table.

    :Inputs:
        **loookup** : Table
            Table with data stored as a lookup table.
        **lookupee** : Table
            Table with a number of columns with keywords, or keyvalues.
    :Outputs:
        *out* : Table
            Table with the collected data from the lookup table together with
            content of the lookupee table.
    :Configuration:
        **Lookup columns**
            A list with all the columns in the lookup table. Select a column
            from the lookup table that should be pair with a column from
            the lookupee column.
        **Lookupee columns**
            A list with all the columns in the control table. Select a column
            from the lookupee table that should be paired with a column from
            the lookup table.
        **Add lookup**
            Press add lookup to register a pair of the two selected columns
            among the lookup columns and the lookupee columns.
        **Remove lookup**
            Remove the selected pair in the locked columns table.
        **Locked columns table**
            Lists all the registered lookup pairs. Use the checkboxes under
            event column to define a pair as event columns.
    :Opposite node: None
    :Ref. nodes: None
    """

    name = "Lookup Tables"
    nodeid = "org.sysess.sympathy.data.table.lookuptables"
    tags = Tags(Tag.DataProcessing.TransformStructure)

    inputs = Ports([Port.Table("Lookup table", name="lookup"),
                    Port.Tables("Lookupee", name="lookupee")])
    outputs = Ports([Port.Tables("Output Table", name="out")])

    def exec_parameter_view(self, node_context):
        lookup_file, lookupee_file, out_file = get_files(node_context)
        if lookupee_file.is_valid() and len(lookupee_file):
            lookupee_file = lookupee_file[0]
        else:
            lookupee_file = table.File()
        if out_file:
            out_file = out_file[0]

        return LookupWidget(
            node_context.parameters, lookup_file, lookupee_file, out_file)

    def execute(self, node_context):
        for lookupee_file in node_context.input['lookupee']:
            out_file = node_context.output['out'].create()
            apply_index_datacolumn_and_write_to_file(
                node_context.parameters, node_context.input['lookup'],
                lookupee_file, out_file)
            node_context.output['out'].append(out_file)
