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
The horisontal join, or the HJoin, of :ref:`ADAF` objects has the purpose
to merge data that has been simultaneously collected by different measurement
systems and been imported into different ADAFs. The output of the
operation is a new ADAF, where each data container is the result of a
horisontal join between the two corresponding data containers of the
incoming ADAFs.

The content of the metadata and the result containers are tables and
the horisontal join of these containers follows the procedure described
in :ref:`HJoin Table`.

The timeseries container has the structure of a dictionary, where the keys
at the first instance/level are the names of the systems from which the
time resolved data is collected from. The result of a horisontal join
operation upon two timeseries containers will become a new
container to which the content of the initial containers have been added.
In this process it is important to remember that a system in the outgoing
container will be overwritten if one adds a new system with the same name.

"""

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class HJoinADAFDefinition(object):
    name = "HJoin ADAF"
    description = "HJoin two ADAF files."
    nodeid = "org.sysess.sympathy.data.adaf.hjoinadaf"
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(c) 2013 Combine AB"
    version = '1.0'
    tags = Tags(Tag.DataProcessing.TransformStructure)
    inputs = Ports([
        Port.ADAF('ADAF 1', name='port1'),
        Port.ADAF('ADAF 2', name='port2')])
    outputs = Ports([Port.ADAF('Joined ADAF', name='port1')])


class HJoinADAFsDefinition(object):
    name = "HJoin ADAFs"
    description = "HJoin two lists with ADAF files."
    nodeid = "org.sysess.sympathy.data.adaf.hjoinadafs"
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(c) 2013 Combine AB"
    version = '0.1'
    tags = Tags(Tag.DataProcessing.TransformStructure)
    inputs = Ports([
        Port.ADAFs('ADAFs 1', name='port1'),
        Port.ADAFs('ADAFs 2', name='port2')])
    outputs = Ports([Port.ADAFs('Joined ADAFs', name='port1')])


class HJoinADAF(synode.Node, HJoinADAFDefinition):

    """
    Horistonal join, or HJoin, of two ADAFs into an ADAF.

    :Inputs:
        **port1** : ADAF
            ADAF with data.
        **port2** : ADAF
            ADAF with data.
    :Outputs:
        **port1** : ADAF
            ADAF with horisontally joined data.
    :Configuration: No configuration.
    :Opposite node:
    :Ref. nodes: :ref:`HJoin ADAFs`, :ref:`HJoin Table`
    """

    def __init__(self):
        super(HJoinADAF, self).__init__()

    def execute(self, node_context):
        """ Execute """
        adaffile1 = node_context.input['port1']
        adaffile2 = node_context.input['port2']
        out_adaffile = node_context.output['port1']
        out_adaffile.hjoin(adaffile1)
        out_adaffile.hjoin(adaffile2)


class HJoinADAFs(synode.Node, HJoinADAFsDefinition):

    """
    Pairwise horisontal join, or HJoin, of the two list of Tables
    into a list of Table.

    :Inputs:
        **port1** : ADAFs
            ADAFs with data.
        **port2** : ADAF
            ADAFs with data.
    :Outputs:
        **port1** : ADAFs
            ADAFs with horisontally joined data.
    :Configuration: None
    :Opposite node:
    :Ref. nodes: :ref:`HJoin ADAF`, :ref:`HJoin Tables`
    """

    def __init__(self):
        super(HJoinADAFs, self).__init__()

    def execute(self, node_context):
        """ Execute """
        in_files1 = node_context.input['port1']
        in_files2 = node_context.input['port2']
        out_adaffiles = node_context.output['port1']
        for file1_item, file2_item in zip(in_files1,
                                          in_files2):
            out_adaffile = out_adaffiles.create()
            out_adaffile.hjoin(file1_item)
            out_adaffile.hjoin(file2_item)
            out_adaffiles.append(out_adaffile)
