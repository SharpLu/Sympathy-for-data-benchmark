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
The internal dataformat :ref:`Table` can either be represented with a single
Table or with a list of Tables. Most of the nodes that operates upon Tables can
handle both representations, but there exist nodes which only can handle
one of the two. With the considered node it is possible to make a transition
from a single Table into a list of Tables. There do also exist a node
for the opposite transition, :ref:`Get Item Table`. These two simple operations
widen the spectrum of available Table operations in the standard library.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class Table2Tables(synode.Node):
    """
    Convert Table into Tables. The incoming Table will be
    the only element in the output.

    :Inputs:
        **port0** : Table
            Table with data
    :Outputs:
        **port1** : Tables
            Tables with the incoming Table as its only element.
    :Configuration: No configuration
    :Opposite node: :ref:`Get Item Table`
    :Ref. nodes:
    """

    name = 'Table to Tables'
    description = 'Convert a single Table item to a list of Tables.'
    inputs = Ports([Port.Table('Input Table', name='port0')])
    outputs = Ports([Port.Tables(
        'Tables with the input Table as the only element', name='port1')])

    author = 'Alexander Busck <alexander.busck@sysess.org>'
    copyright = '(c) 2013 Combine AB'
    nodeid = 'org.sysess.sympathy.data.table.table2tables'
    version = '0.1'
    icon = 'table2tables.svg'
    tags = Tags(Tag.Hidden.Deprecated)

    def execute(self, node_context):
        """Execute"""
        in_tablefile = node_context.input['port0']
        out_tablelist = node_context.output['port1']
        out_tablelist.append(in_tablefile)
