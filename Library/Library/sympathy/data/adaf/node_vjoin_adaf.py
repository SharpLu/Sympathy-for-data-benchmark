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
The vertical join, or the VJoin, of :ref:`ADAF` objects has the purpose
to merge data from tests performed at different occasions, where the data
from the occasions have been imported into different ADAFs. This opens up
for the possibility to perform analysis of tests/events over the course of
time.

The output of the operation is a new ADAF, where each data container is the
result of a vertical join performed between the corresponding data containers
of the incoming ADAFs. At the moment the output will only include the result
the vertical join of the metadata and the result containers. The timeseries
container will be empty in the outgoing ADAF.

The content of the metadata and the result containers are tables and the
vertical join of these containers follows the procedure described in
:ref:`VJoin Table`.
"""
from itertools import izip

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags

INDEX = 'VJoin-index'


class VJoinBase(synode.Node):
    parameters = synode.parameters()
    parameters.set_boolean(
        'fill', value=False, label='Fill missing with NaN',
        description='Fill missing columns with Nan when joining.')
    parameters.set_integer(
        'minimum_increment',
        value=1,
        label='Increment used when number of rows = 0',
        description='Increment used for tables with number of rows = 0')
    parameters.set_string(
        'output_index',
        label='Output Index',
        value=INDEX,
        description='Choose name for output index column. Can be left empty.')
    parameters.set_boolean(
        'include_rasters', value=True, label='Include rasters in the result',
        description='Include rasters in the result.')
    parameters.set_boolean(
        'use_reference_time', value=False, label='Use raster reference time',
        description='Use raster reference time.')
    tags = Tags(Tag.DataProcessing.TransformStructure)

    def extra_parameters(self, parameters):
        input_index = ''
        try:
            output_index = parameters['output_index'].value
        except:
            output_index = INDEX
        try:
            minimum_increment = parameters['minimum_increment'].value
        except:
            minimum_increment = 0
        try:
            include_rasters = parameters['include_rasters'].value
        except:
            include_rasters = False
        try:
            use_reference_time = parameters['use_reference_time'].value
        except:
            use_reference_time = False

        return (input_index, output_index, minimum_increment, include_rasters,
                use_reference_time)


class VJoinADAF(VJoinBase):
    """
    Sympathy node for vertical join of two ADAF files. The output of node
    is a new ADAF.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
        **port2** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : ADAF
            ADAF with vertical merged data.
    :Configuration:
        **Complement missing columns**
            Select if columns that do not exist in all incoming
            Tables are to be complemented or not.
        **Increment in index column**
            Select the size of the increment to the outgoing index
            column if the number of rows in a incoming Table is equal
            to zero. Possible values are 0 or 1.
        **Include rasters**
            Include rasters in the result of the operation.
        **Output index**
            Specify the names of outgoing index column, can be left empty.
    :Opposite node: :ref:`VSplit ADAF`
    :Ref. nodes: :ref:`VJoin ADAFs`, :ref:`VJoin Table`
    """

    name = "VJoin ADAF"
    description = "VJoin two ADAF files."
    nodeid = "org.sysess.sympathy.data.adaf.vjoinadaf"
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C)2013 System Engineering Software Society"
    version = '1.0'
    inputs = Ports([
        Port.ADAF('ADAF 1', name='port1'),
        Port.ADAF('ADAF 2', name='port2')])
    outputs = Ports([Port.ADAF('Joined ADAF', name='port1')])

    def execute(self, node_context):
        """Execute"""
        input_adaf1 = node_context.input['port1']
        input_adaf2 = node_context.input['port2']
        output_adaf = node_context.output['port1']
        (input_index, output_index, minimum_increment,
         include_rasters,
         use_reference_time) = self.extra_parameters(node_context.parameters)

        output_adaf.vjoin(
            [input_adaf1, input_adaf2],
            input_index,
            output_index,
            node_context.parameters['fill'].value,
            minimum_increment,
            include_rasters,
            use_reference_time)


class VJoinADAFs(VJoinBase):
    """
    Sympathy node for vertical join of the ADAFs in the incoming list.
    The output of node is a new ADAF.

    VJoin multiple ADAF files.

    :Inputs:
        **port0** : ADAFs
            ADAFs with data.
    :Outputs:
        **port0** : ADAF
            ADAF with vertically merged data.
    :Configuration:
        **Complement missing columns**
            Select if columns that do not exist in all incoming
            Tables are to be complemented or not.
        **Increment in index column**
            Select the size of the increment to the outgoing index
            column if the number of rows in a incoming Table is equal
            to zero. Possible values are 0 or 1.
        **Include rasters**
            Include rasters in the result of the operation.
        **Output index**
            Specify the names of outgoing index column, can be left empty.
    :Opposite node: :ref:`VSplit ADAF`
    :Ref. nodes: :ref:`VJoin ADAF`, :ref:`VJoin Tables`
    """

    name = "VJoin ADAFs"
    description = "VJoin multiple ADAF files."
    nodeid = "org.sysess.sympathy.data.adaf.vjoinadafs"
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C)2013 System Engineering Software Society"
    version = '1.0'
    inputs = Ports([Port.ADAFs('Input ADAFs', name='port0')])
    outputs = Ports([Port.ADAF('Joined ADAFs', name='port0')])

    def execute(self, node_context):
        """Execute"""
        input_adafs = node_context.input['port0']
        output_adaf = node_context.output['port0']
        (input_index, output_index, minimum_increment,
         include_rasters,
         use_reference_time) = self.extra_parameters(node_context.parameters)

        output_adaf.vjoin(
            input_adafs,
            input_index,
            output_index,
            node_context.parameters['fill'].value,
            minimum_increment,
            include_rasters,
            use_reference_time)


class VJoinADAFLists(VJoinBase):
    """
    Sympathy node for pairwise vertical join of two lists of ADAFs. The output
    is a new list of ADAFs.

    :Inputs:
        **port1** : ADAF
            ADAFs with data.
        **port2** : ADAF
            ADAFs with data.
    :Outputs:
        **port1** : ADAF
            ADAFs with vertical merged data.
    :Configuration:
        **Complement missing columns**
            Select if columns that do not exist in all incoming
            Tables are to be complemented or not.
        **Increment in index column**
            Select the size of the increment to the outgoing index
            column if the number of rows in a incoming Table is equal
            to zero. Possible values are 0 or 1.
        **Include rasters**
            Include rasters in the result of the operation.
        **Output index**
            Specify the names of outgoing index column, can be left empty.
    :Opposite node:
    :Ref. nodes: :ref:`VJoin ADAFs`, :ref:`VJoin Table lists`
    """

    name = "VJoin ADAF lists"
    description = "Pairwise VJoin two ADAFs lists."
    nodeid = "org.sysess.sympathy.data.adaf.vjoinadaflists"
    author = "Magnus Sanden <magnus.sanden@combine.se>"
    copyright = "(C)2014 System Engineering Software Society"
    version = '1.0'
    inputs = Ports([
        Port.ADAFs('ADAFs 1', name='port1'),
        Port.ADAFs('ADAFs 2', name='port2')])
    outputs = Ports([Port.ADAFs('Joined ADAFs', name='port1')])

    def execute(self, node_context):
        """Execute"""
        input_adafs1 = node_context.input['port1']
        input_adafs2 = node_context.input['port2']
        output_adafs = node_context.output['port1']
        (input_index, output_index, minimum_increment,
         include_rasters,
         use_reference_time) = self.extra_parameters(node_context.parameters)

        for input_adaf1, input_adaf2 in izip(input_adafs1, input_adafs2):
            output_adaf = output_adafs.create()
            output_adaf.vjoin(
                [input_adaf1, input_adaf2],
                input_index,
                output_index,
                node_context.parameters['fill'].value,
                minimum_increment,
                include_rasters,
                use_reference_time)
            output_adafs.append(output_adaf)
