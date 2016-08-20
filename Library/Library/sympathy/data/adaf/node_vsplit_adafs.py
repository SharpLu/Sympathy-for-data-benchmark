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
The node performs a vertical, rowwise, split of :ref:`ADAF`. The vertical
split, or VSplit, is the inverse operation compared to the vertical join,
see :ref:`VJoin ADAF`.

The vertical split operation is only applied on the content of the metadata
and result containers. The timeseries container is not included, since the
inverse operation, VJoin, is not defined for this container. The content of
the metadata and the result containers are tables and the vertical split of
these containers follows the procedure described in :ref:`VSplit Table`.
For the split to be well defined, the Input Index column is required in
metadata and result containers.
"""
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


INDEX = 'VJoin-index'


class VSplitBase(synode.Node):
    parameters = synode.parameters()
    parameters.set_boolean(
        'remove_fill', value=False, label='Remove fill',
        description='Remove split columns which contain only NaN.')
    parameters.set_string(
        'input_index',
        label='Input Index',
        value=INDEX,
        description='Choose name for grouped index column. '
                    'Required in both metadata and results.')
    parameters.set_boolean(
        'include_rasters', value=True, label='Include rasters in the result',
        description='Include rasters in the result.')
    parameters.set_list(
        'ungrouped_elements', ['Belong to first group',
                               'Belong to separate group',
                               'Belong to all groups'],
        label='Ungrouped elements',
        description='Ungrouped elements.', value=[0],
        editor=synode.Util.combo_editor().value())
    tags = Tags(Tag.DataProcessing.TransformStructure)

    def extra_parameters(self, parameters):
        try:
            input_index = parameters['input_index'].value
        except:
            input_index = INDEX
        try:
            include_rasters = parameters['include_rasters'].value
        except:
            include_rasters = False

        try:
            ungrouped_elements = parameters['ungrouped_elements'].value[0]
        except:
            ungrouped_elements = False

        if int(ungrouped_elements) != 0:
            raise NotImplementedError

        return (input_index, include_rasters)


class VSplitADAFNode(VSplitBase):
    """
    Vertical split of ADAF into ADAFs.

    :Inputs:
        **port1** : ADAF
            Incoming ADAF with data.
    :Outputs:
        **port1** : ADAFs
            ADAFs with splitted data.
    :Configuration:
        **Remove fill**
            Turn on or off if split columns that contain only NaNs or
            empty strings are going to be removed or not.
        **Input index**
            Specify the name of the incoming index column, can be left empty.
            Needs to be grouped by index.
    :Opposite node: :ref:`VJoin ADAF`
    :Ref. nodes:
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'

    name = 'VSplit ADAF'
    description = 'Split an ADAF into multiple ADAFs.'
    nodeid = 'org.sysess.sympathy.data.adaf.vsplitadafnode'

    inputs = Ports([Port.ADAF('Input ADAF', name='port1')])
    outputs = Ports([Port.ADAFs('Split ADAFs', name='port1')])

    def execute(self, node_context):
        """Execute"""
        input_adaf = node_context.input['port1']
        output_adafs = node_context.output['port1']
        input_index, include_rasters = self.extra_parameters(
            node_context.parameters)

        input_adaf.vsplit(
            output_adafs,
            input_index,
            node_context.parameters['remove_fill'].value,
            True,
            include_rasters)
