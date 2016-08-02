# Copyright (c) 2015, System Engineering Software Society
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
import numpy as np
import dsgroup
import json


class Hdf5Lambda(dsgroup.Hdf5Group):
    """Abstraction of an HDF5-lambda."""
    def __init__(self, factory, group=None, datapointer=None, can_write=False,
                 can_link=False):
        super(Hdf5Lambda, self).__init__(
            factory, group, datapointer, can_write, can_link)

    def read(self):
        """
        Return stored pair of flow and list of port assignments or None if
        nothing is stored.
        """
        flow = self.group.attrs['flow']
        name = self.group.attrs['name'].decode('utf8')
        nodes = self.group['nodes'][...].tolist()

        input_nodes = self.group['input_nodes'][...].tolist()
        output_nodes = self.group['output_nodes'][...].tolist()
        input_ports = json.loads(self.group['input_ports'][...].tolist())
        output_ports = self.group['output_ports'][...].tolist()
        ports = self.group['ports'][...].tolist()

        return (
            (flow, name, nodes, input_nodes, output_nodes, input_ports,
             output_ports),
            ports)

    def write(self, value):
        """
        Stores lambda in the hdf5 file, at path,
        with data from the given text
        """
        (flow, name, nodes, input_nodes, output_nodes, input_ports,
         output_ports) = value[0]
        ports = value[1]
        self.group.attrs.create('flow', str(flow))
        self.group.attrs.create('name', name.encode('utf8'))
        self.group.create_dataset(
            'nodes', data=np.array(nodes, dtype=str))
        self.group.create_dataset('input_nodes',
                                  data=np.array(input_nodes, dtype=str))
        self.group.create_dataset('output_nodes',
                                  data=np.array(output_nodes, dtype=str))
        self.group.create_dataset('input_ports',
                                  data=np.array(
                                      json.dumps(input_ports), dtype=str))
        self.group.create_dataset('output_ports',
                                  data=np.array(output_ports, dtype=str))
        self.group.create_dataset('ports',
                                  data=np.array(ports, dtype=str))

    def transferable(self, other):
        return False

    def transfer(self, other):
        self.group.attrs['flow'] = other.group.attrs['flow']
        self.group.attrs['name'] = other.group.attrs['name']
        for key in ['nodes', 'input_nodes', 'output_nodes', 'input_ports',
                    'output_ports']:
            self.group[key] = other.group[key]
