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
The internal dataformat :ref:`Text` can either be represented with a single
Text or with a list of Texts. Most of the nodes that operates upon Texts can
handle both representations, but there exist nodes which only can handle
one of the two. With the considered node it is possible to make a transition
from a single Text into a list of Texts. There do also exist a node
for the opposite transition, :ref:`Get Item Text`. These two simple operations
widen the spectrum of available Text operations in the standard library.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class Text2Texts(synode.Node):
    """
    Convert Text into Texts. The incoming Text will be
    the only element in the output.

    :Inputs:
        **port0** : Text
            Text with data
    :Outputs:
        **port1** : Texts
            Texts with the incoming Text as its only element.
    :Configuration: No configuration
    :Opposite node: :ref:`Get Item Text`
    :Ref. nodes:
    """

    name = 'Text to Texts'
    description = 'Convert a single Text item to a list of Texts.'
    inputs = Ports([Port.Text('Input Text', name='port0')])
    outputs = Ports([Port.Texts(
        'Texts with the input Text as the only element', name='port1')])
    tags = Tags(Tag.Hidden.Deprecated)

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2013 System Engineering Software Society'
    nodeid = 'org.sysess.sympathy.data.text.text2texts'
    version = '0.1'
    icon = 'text2texts.svg'

    def __init__(self):
        super(Text2Texts, self).__init__()

    def execute(self, node_context):
        """Execute"""
        in_textfile = node_context.input['port0']
        out_textlist = node_context.output['port1']
        out_textlist.append(in_textfile)
