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
The considered node sorts the order of the ADAFs in the incoming list
according to a compare function. The outgoing ADAFs are in the new order.

The compare function can be defined as a lamda function or an ordinary
function starting with def. The function should compare two elements and
return  -1, 0 or 1. If element1 < element2, then return -1, if they are
equal return 0 and otherwise return 1.

A preview is available if one wants to preview the sorting. Then the indices
of the sorted list is shown in a table together with the indices of the
original unsorted list.
"""
from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui') # noqa

from sylib import sort as sort_util

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class SortADAFsNode(synode.Node):
    """
    .. deprecated:: 1.3.0
       Use :ref:`Sort List` instead.

    Sort ADAF list by using a compare function.

    :Inputs:
        **port1** : ADAFs
            ADAFs with data.
    :Outputs:
        **port1** : ADAFs
            Sorted ADAFs.
    :Configuration:
        **Compare function for sorting**
            Write the sort function.
    """

    name = 'Sort ADAFs (deprecated)'
    description = 'Sort ADAF list.'
    inputs = Ports([Port.ADAFs('Input ADAF', name='port1', requiresdata=True)])
    outputs = Ports([Port.ADAFs('Sorted ADAF', name='port1')])

    author = 'Helena Olen <helena.olen@combine.se>'
    copyright = '(c) 2013 Combine AB'
    nodeid = 'org.sysess.sympathy.data.adaf.sortadafsnode'
    version = '1.0'
    parameters = synode.parameters()
    parameters.set_string(
        'sort_function',
        description='Python key function that determines order.',
        value='lambda item: item  # Arbitrary key example.')

    parameters.set_boolean(
        'reverse',
        label='Reverse order',
        description='Use descending (reverse) order.',
        value=False)

    tags = Tags(Tag.Hidden.Deprecated)

    def exec_parameter_view(self, node_context):
        return sort_util.SortWidget(node_context.input['port1'],
                                    node_context)

    def execute(self, node_context):
        output_list = node_context.output['port1']
        for item in sort_util.sorted_list(
                node_context.parameters['sort_function'].value,
                node_context.input['port1'],
                reverse=node_context.parameters['reverse'].value):
            output_list.append(item)
