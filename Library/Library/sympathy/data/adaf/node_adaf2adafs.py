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
The internal dataformat :ref:`ADAF` can either be represented with a single
ADAF or with a list of ADAFs. Most of the nodes that operates upon ADAFs can
handle both representations, but there exist nodes which only can handle
one of the two. With the considered node it is possible to make a transition
from a single ADAF into a list of ADAFs. There do also exist a node
for the opposite transition, :ref:`Get Item ADAF`. These two simple operations
extend the spectrum of available ADAF operations in the node library.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class ADAF2ADAFs(synode.Node):
    """
    Convert a single ADAF into a list of ADAFs. The incoming ADAF will be the
    only element in the outgoing list.

    :Inputs:
        **port1** : ADAF
            ADAF with data
    :Outputs:
        **port1** : ADAFs
            ADAFs with the incoming ADAF as its only element.
    :Configuration: No configuration.
    :Opposite node: :ref:`Get Item ADAF`
    :Ref. nodes:
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'adaf2adafs.svg'

    name = 'ADAF to ADAFs'
    description = 'Converts a single ADAF to a list.'
    nodeid = 'org.sysess.sympathy.data.adaf.adaf2adafs'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.ADAF('Input ADAF', name='port1')])
    outputs = Ports([Port.ADAFs(
        'ADAFs list with input ADAF as only element', name='port1')])

    def __init__(self):
        super(ADAF2ADAFs, self).__init__()

    def execute(self, node_context):
        in_tablefile = node_context.input['port1']
        out_tablelist = node_context.output['port1']
        out_tablelist.append(in_tablefile)
