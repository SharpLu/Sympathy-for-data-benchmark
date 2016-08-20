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
In the standard library there exist two nodes which exports data from
:ref:`Datasource` to :ref:`Table`. The outgoing :ref:`Table` will consist
of a single column with filepaths. The length of the column will be equal
to the incoming number of datasources.

In the configuration GUI it is possible to select if one wants to convert
the paths in the Datasources to absolute filepaths.
"""
import os.path

import numpy as np

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class SuperNode(object):
    """Shared metadata between the two nodes in this file."""

    author = "Magnus Sanden <magnus.sanden@combine.se>"
    copyright = "(C)2013 System Engineering Software Society"
    version = "1.0"
    icon = "dsrc2table.svg"
    tags = Tags(Tag.DataProcessing.Convert)

    parameters = synode.ParameterRoot()
    parameters.set_boolean(
        "abspath", value=False,
        label="Force absolute paths",
        description="If ticked, an attempt will be made to convert all the "
                    "paths in the Datasources to absolute paths.")


class DsrcToTable(SuperNode, synode.Node):
    """
    Exportation of data from Datasource to Table.

    :Inputs:
        **in** : Datasource
            Datasource with filepaths.
    :Outputs:
        **out** : Table
            Table with a single column with a filepath.
    :Configuration:
        **Force absolute paths**
            If ticked, an attempt will be made to convert all the paths in the
            Datasources to absolute paths.
    :Opposite node:
    :Ref. nodes: :ref:`Datasources to table`
    """

    name = "Datasource to Table"
    description = ("Convert a single data source into a table containing that "
                   "filename.")
    nodeid = "org.sysess.sympathy.data.table.dsrctotable"

    inputs = Ports([Port.Datasource("Datasource", name="in")])
    outputs = Ports([Port.Table("Table with filenames", name="out")])

    def execute(self, node_context):
        outfile = node_context.output['out']
        infile = node_context.input['in']

        if node_context.parameters['abspath'].value:
            filepath = os.path.abspath(infile.decode_path())
        else:
            filepath = infile.decode_path()
        outfile.set_column_from_array('filepaths', np.array([filepath]))


class DsrcsToTable(SuperNode, synode.Node):
    """
    Exportation of data from Datasources to Tables.

    :Inputs:
        **in** : Datasources
            Datasources with filepaths.
    :Outputs:
        **out** : Table
            Table with a single column with a filepath.
    :Configuration:
        **Force absolute paths**
            If ticked, an attempt will be made to convert all the paths in the
            Datasources to absolute paths.
    :Opposite node:
    :Ref. nodes: :ref:`Datasource to table`
    """

    name = "Datasources to Table"
    description = "Converts a list of data sources into a table of filenames."
    nodeid = "org.sysess.sympathy.data.table.dsrcstotable"

    inputs = Ports([Port.Datasources("Datasources", name="in")])
    outputs = Ports([Port.Table("Table with filenames", name="out")])

    def execute(self, node_context):
        outfile = node_context.output['out']

        filepaths = []
        for infile in node_context.input['in']:
            if node_context.parameters['abspath'].value:
                filepath = os.path.abspath(infile.decode_path())
            else:
                filepath = infile.decode_path()
            filepaths.append(filepath)
        outfile.set_column_from_array('filepaths', np.array(filepaths))
