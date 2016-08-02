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
import copy
import json
import workflow_converter


def flow_from_syx(syx_filename):
    with open(syx_filename, 'r') as source:
        to_json_converter = workflow_converter.XMLToJson(source)
        flow_dict = to_json_converter.dict()
        flow = Flow.from_dict(flow_dict)
        return flow


class ElementInterface(object):
    def __init__(self):
        super(ElementInterface, self).__init__()

        self._dict = {'uuid': ''}

    def to_dict(self):
        return self._dict

    def uuid(self):
        return self._dict['uuid']

    def set_uuid(self, uuid):
        self._dict['uuid'] = uuid


class NodeInterface(ElementInterface):
    def __init__(self):
        super(NodeInterface, self).__init__()
        node_dict = {
            'x': -1.0,
            'y': -1.0,
            'width': -1.0,
            'height': -1.0,
            'ports': {
                'inputs': [],
                'outputs': []},
            'id': '',
            'label': '',
            'author': '',
            'copyright': '',
            'description': '',
            'version': '',
            'docs': '',
            'parameters': ''}
        self._dict.update(node_dict)

    def to_dict(self):
        node_dict = self._dict
        inputs = [port.to_dict() for port in node_dict['ports']['inputs']]
        outputs = [port.to_dict() for port in node_dict['ports']['outputs']]
        node_dict['ports']['inputs'] = inputs
        node_dict['ports']['outputs'] = outputs
        return node_dict

    def to_clipboard(self):
        node_dict = copy.deepcopy(self.to_dict())
        return node_dict

    def x(self):
        return self._dict['x']

    def y(self):
        return self._dict['y']

    def width(self):
        return self._dict['width']

    def height(self):
        return self._dict['height']

    def inputs(self):
        return self._dict['ports']['inputs']

    def outputs(self):
        return self._dict['ports']['outputs']

    def id(self):
        return self._dict['id']

    def label(self):
        return self._dict['label']

    def author(self):
        return self._dict['author']

    def copyright(self):
        return self._dict['copyright']

    def description(self):
        return self._dict['description']

    def version(self):
        return self._dict['version']

    def docs(self):
        return self._dict['docs']

    def parameters(self):
        return self._dict['parameters']

    def parameter_data(self):
        return json.loads(self._dict['parameters']['data'])

    def parameter_type(self):
        return self._dict['parameters']['type']

    def set_x(self, x):
        self._dict['x'] = x

    def set_y(self, y):
        self._dict['y'] = y

    def set_width(self, width):
        self._dict['width'] = width

    def set_height(self, height):
        self._dict['height'] = height

    def set_id(self, identifier):
        self._dict['id'] = identifier

    def set_label(self, label):
        self._dict['label'] = label

    def set_author(self, author):
        self._dict['author'] = author

    def set_copyright(self, copyright_holder):
        self._dict['copyright'] = copyright_holder

    def set_description(self, description):
        self._dict['description'] = description

    def set_version(self, version):
        self._dict['version'] = version

    def set_docs(self, docs):
        self._dict['docs'] = docs

    def set_parameters(self, parameters, type_='json'):
        self._dict['parameters']['data'] = json.dumps(parameters)
        self._dict['parameters']['type'] = type_


class ConnectionInterface(ElementInterface):
    def __init__(self):
        super(ConnectionInterface, self).__init__()


class Node(NodeInterface):
    def __init__(self):
        super(Node, self).__init__()

    @staticmethod
    def from_dict(in_dict):
        node = Node()
        dict_ = copy.deepcopy(in_dict)
        node._dict = dict_

        inputs = []
        outputs = []
        if 'ports' in in_dict:
            if 'inputs' in in_dict['ports']:
                inputs = [Port.from_dict(port)
                          for port in in_dict['ports']['inputs']]
            if 'outputs' in in_dict['ports']:
                outputs = [Port.from_dict(port)
                           for port in in_dict['ports']['outputs']]
        if 'ports' not in dict_:
            dict_['ports'] = {}

        parameters = dict_['parameters']
        del dict_['parameters']
        dict_['parameters'] = {}
        node.set_parameters(parameters)

        dict_['ports']['inputs'] = inputs
        dict_['ports']['outputs'] = outputs
        return node


class Flow(NodeInterface):
    def __init__(self):
        super(Flow, self).__init__()

        flow_dict = {
            'nodes': [],
            'flows': [],
            'connections': [],
            'source': '',
            'is_linked': False}

        self._dict.update(flow_dict)

    def to_dict(self):
        flow_dict = self._dict
        inputs = [port.to_dict() for port in flow_dict['ports']['inputs']]
        outputs = [port.to_dict() for port in flow_dict['ports']['outputs']]
        flows = [flow.to_dict() for flow in flow_dict['flows']]
        nodes = [node.to_clipboard() for node in flow_dict['nodes']]
        flow_dict['ports']['inputs'] = inputs
        flow_dict['ports']['outputs'] = outputs
        flow_dict['flows'] = flows
        flow_dict['nodes'] = nodes
        return flow_dict

    def to_clipboard(self):
        clipboard = {
            'flow': self.to_dict(),
            'center': {
                'x': 0.0,
                'y': 0.0}}
        return clipboard

    @staticmethod
    def from_dict(in_dict):
        dict_ = in_dict
        inputs = outputs = []
        if 'ports' in in_dict:
            if 'inputs' in in_dict['ports']:
                inputs = [Port.from_dict(port)
                          for port in in_dict['ports']['inputs']]
            if 'outputs' in in_dict['ports']:
                outputs = [Port.from_dict(port)
                           for port in in_dict['ports']['outputs']]
        if 'ports' not in dict_:
            dict_['ports'] = {}
        dict_['ports']['inputs'] = inputs
        dict_['ports']['outputs'] = outputs

        flows = [Flow.from_dict(flow) for flow in in_dict['flows']]
        dict_['flows'] = flows
        nodes = [Node.from_dict(node) for node in in_dict['nodes']]
        dict_['nodes'] = nodes
        flow = Flow()
        flow._dict = dict_
        return flow

    def nodes(self):
        return self._dict['nodes']

    def flows(self):
        return self._dict['flows']

    def connections(self):
        return self._dict['connections']

    def append_node(self, node):
        self._dict['nodes'].append(node)

    def append_flow(self, flow):
        self._dict['flows'].append(flow)

    def append_connection(self, connection):
        self._dict['connections'].append(connection)


class Connection(ConnectionInterface):
    def __init__(self):
        super(Connection, self).__init__()
        connection_dict = {
            'source': {
                'node': '',
                'port': ''},
            'destination': {
                'node': '',
                'port': ''}}

        self._dict.update(connection_dict)

    def to_dict(self):
        return self._dict

    def source(self):
        return self._dict['source']['node'], self._dict['source']['port']

    def destination(self):
        return (self._dict['destination']['node'],
                self._dict['destination']['port'])

    def set_source(self, node, port):
        self._dict['source']['node'] = node
        self._dict['source']['port'] = port

    def set_destination(self, node, port):
        self._dict['destination']['node'] = node
        self._dict['destination']['port'] = port


class Port(ElementInterface):
    def __init__(self):
        super(Port, self).__init__()
        port_dict = {
            'index': 0,
            'type': '',
            'scheme': '',
            'requiresdata': False,
            'optional': False,
            'label': '',
            'key': ''}
        self._dict.update(port_dict)

    @staticmethod
    def from_dict(in_dict):
        port = Port()
        port._dict = in_dict
        return port

    def index(self):
        return self._dict['index']

    def type(self):
        return self._dict['type']

    def scheme(self):
        return self._dict['scheme']

    def requiresdata(self):
        return self._dict['requiresdata']

    def optional(self):
        return self._dict['optional']

    def label(self):
        return self._dict['label']

    def key(self):
        return self._dict['key']

    def set_index(self, index):
        self._dict['index'] = index

    def set_type(self, type_):
        self._dict['type'] = type_

    def set_scheme(self, scheme):
        self._dict['scheme'] = scheme

    def set_requiresdata(self, requiresdata):
        self._dict['requiresdata'] = requiresdata

    def set_optional(self, optional):
        self._dict['optional'] = optional

    def set_label(self, label):
        self._dict['label'] = label

    def set_key(self, key):
        self._dict['key'] = key


def main():
    import sys
    flow = flow_from_syx(sys.argv[1])
    print json.dumps(flow.to_clipboard(), indent=2)

if __name__ == '__main__':
    main()
