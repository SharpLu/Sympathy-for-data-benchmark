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
import sys
import os
import collections
import itertools
import tempfile
import copy
import json
import uuid


SY_APPLICATION_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))

# Needed for importer plugins to be found.
os.environ['SY_APPLICATION_PATH'] = SY_APPLICATION_PATH
SY_PYTHON_SUPPORT = os.path.join(SY_APPLICATION_PATH, 'Support', 'Python')
SY_LIBRARY_PATH = os.path.normpath(os.path.join(SY_APPLICATION_PATH, os.pardir, 'Library'))
os.environ['SY_PYTHON_SUPPORT'] = SY_PYTHON_SUPPORT
sys.path.append(SY_PYTHON_SUPPORT)
sys.path.append(os.path.join(SY_LIBRARY_PATH, 'Library'))
sys.path.append(os.path.join(SY_LIBRARY_PATH, 'Common'))

from sympathy.typeutils import table
from sympathy.utils.parameter_helper import ParameterRoot, ParameterGroup
from sympathy.platform.library import create_library_manager
from sympathy.utils.port import (
    port_wrapper, port_generator, typeutil_components, typealiases_parser,
    typealiases_expander, disable_linking)
from sympathy.platform.workflow_converter import (
    xml_file_to_xmltojson_converter)
from sympathy.utils.prim import open_url


disable_linking()

NODE_IDS = collections.OrderedDict({
    'datasource': 'org.sysess.sympathy.datasources.filedatasource',
    'table': 'org.sysess.sympathy.data.table.importtable',
    'adaf': 'org.sysess.sympathy.data.adaf.importadaf',
    'table2tables': 'org.sysess.sympathy.data.table.table2tables',
    'vjoin_table': 'org.sysess.sympathy.data.table.vjointablenode',
    'calculator': 'org.sysess.sympathy.data.table.calculator',
    'select_columns': 'org.sysess.sympathy.data.table.selecttablecolumns',
    'select_rows': 'org.sysess.sympathy.data.table.selecttablerows',
    'example1': 'org.sysess.sympathy.examples.example1',
    'example2': 'org.sysess.sympathy.examples.example2',
    'example3': 'org.sysess.sympathy.examples.example3',
    'example5': 'org.sysess.sympathy.examples.example5'
})

LIBRARY_MANAGER = create_library_manager(SY_APPLICATION_PATH)

LIBRARY_BY_NODEID = LIBRARY_MANAGER.library_by_nodeid()
JSON_TYPEALIASES = LIBRARY_MANAGER.typealiases()
TYPEUTIL_COMPONENTS = typeutil_components()
TYPEALIASES = typealiases_expander(typealiases_parser(
    LIBRARY_MANAGER.typealiases()))


QT_APP = None


def qapplication_instance():
    from sympathy.platform import qt_compat
    QtGui = qt_compat.import_module('QtGui')

    qt_app = QtGui.QApplication.instance()

    if qt_app is None:
        global QT_APP
        QT_APP = QtGui.QApplication(sys.argv)
        qt_app = QT_APP

    return qt_app


class SyiError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SyiNodePort(object):
    def __init__(self, port):
        self._port = port

    @property
    def name(self):
        return self._port.get('name', '')

    @property
    def description(self):
        return self._port['description']

    @property
    def file(self):
        try:
            return self._port['file']
        except KeyError:
            raise SyiError('Input port is not connected properly.')

    @file.setter
    def file(self, name):
        self._port['file'] = name

    @property
    def index(self):
        return self._port['index']

    @property
    def type(self):
        return self._port['type']

    @property
    def scheme(self):
        return self._port['scheme']

    @scheme.setter
    def scheme(self, scheme):
        self._port['scheme'] = scheme

    def to_data(self, mode='r', link=False):
        port_gen = port_generator(self._port, mode, link, TYPEALIASES)
        return port_wrapper(port_gen, self.type, mode, TYPEUTIL_COMPONENTS)

    def __str__(self):
        text = 'SyNodePort[' + self.description + ']({\n'
        if 'scheme' in self._port:
            text += ' scheme: {0},\n'.format(self.scheme)
        text += ' type: {0},\n'.format(self.type)
        if 'file' in self._port:
            text += ' file: {0},\n'.format(self.file)
        text += ' index: {0}'.format(self.index)
        text += '})'
        return text


class SyiNodeIO(object):
    def __init__(self, definition=None, inputs=None):
        self._inputs = definition['ports'].get('inputs', [])
        self._outputs = definition['ports'].get('outputs', [])

        self._input_ports = [SyiNodePort(port) for port in self._inputs]
        self._output_ports = [SyiNodePort(port) for port in self._outputs]

    def inputs(self):
        return self._input_ports

    def input_port_by_index(self, index):
        return self._port_by_index(self._input_ports, index)

    def input_port_by_name(self, name):
        return self._port_by_name(self._input_ports, name)

    def output_port_by_index(self, index):
        return self._port_by_index(self._output_ports, index)

    def output_port_by_name(self, name):
        return self._port_by_name(self._output_ports, name)

    def outputs(self):
        return self._output_ports

    def output(self, index):
        return self.outputs()[index]

    def create_output_files(self):
        for port in self._output_ports:
            # Only create a new output file if empty.
            try:
                port.file
            except SyiError:
                with tempfile.NamedTemporaryFile(
                        prefix='syi_', suffix='.sydata', delete=False) as fq:
                    port.file = fq.name

    def output_files(self):
        output_files = []
        for output in self._outputs:
            output_files.append(output['file'])
        return output_files

    def _outputs(self):
        pass

    def _port_by_index(self, ports, index):
        return ports[index]

    def _port_by_name(self, ports, name):
        return (port for port in ports if port.name == name).next()

    def __str__(self):
        text = 'SyNodeIO({\n'
        port_formatter = (
            lambda name, ports: '\n'.join(
                ['{0}: ['.format(name),
                 '\n'.join(str(port) for port in ports),
                 ']\n']))
        text += port_formatter('inputs', self.inputs())
        text += port_formatter('outputs', self.outputs())
        return text


def i_p(synode, index):
    return synode.io.input_port_by_index(index)


def o_p(synode, index):
    return synode.io.output_port_by_index(index)


class SyiConnectionManager(object):
    """Provides port connection functionality."""
    def __init__(self, graph):
        self._graph = graph

        self._nodes = set()
        self._outport_connections = collections.defaultdict(dict)
        self._inport_connections = collections.defaultdict(dict)

    def connect(self, input_node, connections):
        inputs = input_node.io.inputs()
        # if not isinstance(inputs, tuple):
        #     raise SyiError('Input must be on tuple form ex. inputs=(node,).')
        for dst_port, connection in itertools.izip(inputs, connections):
            if isinstance(connection, tuple):
                src_node, src_port_index = connection
                dst_node = input_node
                dst_port_index = dst_port.index
                self._nodes.add(src_node)
                self._nodes.add(dst_node)
                self._graph.add_edge(src_node, dst_node)
                self._connect(
                    src_node, src_port_index, dst_node, dst_port_index)
            elif isinstance(connection, SyiNode):
                src_node = connection
                src_port_index = connection.io.output(0).index
                dst_node = input_node
                dst_port_index = dst_port.index
                self._nodes.add(src_node)
                self._nodes.add(dst_node)
                self._graph.add_edge(src_node, dst_node)
                self._connect(
                    src_node, src_port_index, dst_node, dst_port_index)
            else:
                raise NotImplementedError("Connection type not implemented.")

    def remove_node(self, node):
        for src_port, connections in self._outport_connections[node].items():
            for dst_node, dst_port in connections:
                del self._inport_connections[dst_node][dst_port]
        del self._outport_connections[node]

        for dst_port, (src_node, src_port) in (
                self._inport_connections[node].items()):
            self._outport_connections[src_node][src_port].remove(
                (node, dst_port))
        del self._inport_connections[node]

    def inputs_properly_connected(self, node):
        incoming_nodes = self.get_back_connections(node)
        # Ensure all input ports are connected.
        if len(incoming_nodes) != len(node.io.inputs()):
            return False
        # Ensure all input port has a file available
        for port_index, (innode, inport_index) in incoming_nodes.iteritems():
            try:
                if not os.path.isfile(i_p(node, port_index).file):
                    return False
            except SyiError:
                return False
        return True

    def disconnect(self, src_node, src_port_index,
                   dst_node, dst_port_index):
        """Remove a connection."""
        self._outport_connections[src_node][src_port_index].remove(
            (dst_node, dst_port_index))
        del self._inport_connections[dst_node][dst_port_index]

    def get_back_connections(self, node):
        """Get all connections to input ports of specified node."""
        return self._inport_connections[node]

    def get_forward_connections(self, node):
        """Get all connections to output ports of specified node."""
        return self._outport_connections[node]

    def pull_input_files(self, node):
        """Insert all created files into the input port of the given node."""
        incoming_nodes = self.get_back_connections(node)
        for port_index, (innode, inport_index) in incoming_nodes.iteritems():
            i_p(node, port_index).file = o_p(innode, inport_index).file
            i_p(node, port_index).scheme = o_p(innode, inport_index).scheme

    def push_output_files(self, node):
        """Push output data available for node to all the connected ports."""
        outgoing_nodes = self.get_forward_connections(node)
        for port_index, connected_nodes in outgoing_nodes.iteritems():
            for outnode, outport_index in connected_nodes:
                i_p(outnode, outport_index).file = o_p(node, port_index).file
                i_p(outnode, outport_index).scheme = o_p(
                    node, port_index).scheme

        # outputs = self._nodes_json_data[node]['definition']['outputs']
        # for port in outputs.values():
        #     try:
        #         connected_nodes = (
        #             self._outport_connections[node][port['index']])
        #     except:
        #         continue
        #     for conn_node, conn_port_index in connected_nodes:
        #         conn_json_data = self._nodes_json_data[conn_node]
        #         json_input_ports = conn_json_data['definition']['inputs']
        #         for conn_port in json_input_ports.values():
        #             if conn_port['index'] == conn_port_index:
        #                 conn_port['file'] = port['file']

    def _connect(self, src_node, src_port_index,
                 dst_node, dst_port_index):
        """Connect two ports."""
        src_type = o_p(src_node, src_port_index).type
        dst_type = i_p(dst_node, dst_port_index).type
        assert(src_type == dst_type)

        if src_port_index not in self._outport_connections[src_node]:
            self._outport_connections[src_node][src_port_index] = []
        self._outport_connections[src_node][src_port_index].append(
            (dst_node, dst_port_index))

        self._inport_connections[dst_node][dst_port_index] = (
            src_node, src_port_index)


class SyiParameters(object):
    def __init__(self, parameter_root):
        self._parameter_root = parameter_root

        for key in parameter_root.keys():
            if isinstance(parameter_root[key], ParameterGroup):
                setattr(self, key, SyiParameters(parameter_root[key]))
            else:
                setattr(self, key, parameter_root)

    def __getattribute__(self, name):
        attribute = super(SyiParameters, self).__getattribute__(name)
        if isinstance(attribute, ParameterGroup):
            return super(SyiParameters, self).__getattribute__(name)[name]
        else:
            return super(SyiParameters, self).__getattribute__(name)

    def __setattr__(self, name, value):
        super(SyiParameters, self).__setattr__(name, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __str__(self):
        return str(vars(self))


def create_node_instance_from_source(fq_source_filename, class_name):
    with open_url(fq_source_filename) as f:
        source_code = f.read()
    compiled_code = compile(source_code, fq_source_filename, 'exec')
    context = {}
    eval(compiled_code, context, context)

    return context[class_name]()


def partially_update_dict(user_parameters, parameters):
    for up_k, up_v in user_parameters.iteritems():
        p_k, p_v = up_k, parameters[up_k]
        if isinstance(up_v, dict):
            partially_update_dict(up_v, p_v)
        else:
            parameters[p_k] = up_v


def partially_update_and_add_keys_dict(user_parameters, parameters):
    for up_k, up_v in user_parameters.iteritems():
        try:
            p_k, p_v = up_k, parameters[up_k]
        except KeyError:
            parameters[up_k] = copy.deepcopy(user_parameters[up_k])
            continue
        if isinstance(up_v, dict):
            partially_update_and_add_keys_dict(up_v, p_v)
        else:
            parameters[p_k] = up_v


def remove_parameters_from_dict(remove_parameters, parameter_dict):
    temp_dict = parameter_dict
    prev_temp_dict = parameter_dict
    up_k = None
    for up_k in remove_parameters:
        prev_temp_dict = temp_dict
        temp_dict = temp_dict[up_k]
    if up_k is not None:
        del prev_temp_dict[up_k]


class SyiNode(object):
    def __init__(self, document, definition=None, inputs=None,
                 user_parameters=None, configure_node=False,
                 execute_on_instantiation=True, **kwargs):
        self._document = document
        self._connection_manager = document._connection_manager
        self._definition = definition

        fq_source_filename = definition['file']
        class_name = definition['class']

        with open_url(fq_source_filename) as f:
            source_code = f.read()
        compiled_code = compile(source_code, fq_source_filename, 'exec')
        context = {}
        eval(compiled_code, context, context)
        node = context[class_name]

        try:
            interactive_shortcuts = node.INTERACTIVE_NODE_ARGUMENTS
        except AttributeError:
            interactive_shortcuts = {}
        for shortcut, param in interactive_shortcuts.iteritems():
            if shortcut in kwargs:
                expanded_parameter = definition['parameters']['data']
                for key in param[:-1]:
                    expanded_parameter = expanded_parameter[key]
                expanded_parameter[param[-1]] = kwargs[shortcut]

        self._io = None
        self._node_instance_cache = None

        self._document.add_node(self)

        if definition is not None:
            self._init_definition(definition, inputs, user_parameters)

        if execute_on_instantiation:
            self.run(configure_node=configure_node)

    def file(self):
        return self._definition['file']

    def name(self):
        return self._definition['name']

    def class_name(self):
        return self._definition['class']

    @property
    def parameters(self):
        return SyiParameters(ParameterRoot(
            self._definition['parameters']['data']))

    @parameters.setter
    def parameters(self, new_parameters):
        self._definition['parameters']['data'] = new_parameters

    def create_instance(self):
        fq_source_filename = self.file()
        class_name = self.class_name()

        if self._node_instance_cache is None:
            self._node_instance_cache = create_node_instance_from_source(
                fq_source_filename, class_name)

        return self._node_instance_cache

    def run(self, configure_node=False):
        if self._connection_manager.inputs_properly_connected(self):
            if configure_node:
                self.configure()
            self._run()
        else:
            raise SyiError(
                'Node cannot be executed due to incorrect configuration.')

    def configure(self, without_parameters=None):
        self._configure(without_parameters)

    def parameter_widget(self):
        # Ensure a QApplication to be initialized before creating a QWidget.
        qapplication_instance()
        node_instance = self.create_instance()
        adjusted_json_definition = (
            node_instance._sys_adjust_parameters(
                self._definition, JSON_TYPEALIASES))
        self.parameters = adjusted_json_definition['parameters']['data']
        widget, close_handles = node_instance._sys_parameter_widget(
            self._definition, JSON_TYPEALIASES)
        return widget

    @property
    def io(self):
        return self._io

    def definition(self):
        return self._definition

    def output_files(self):
        return self._io.output_files()

    def _init_definition(self, definition, inputs, user_parameters):
        self._io = SyiNodeIO(definition, inputs)
        parameters = definition['parameters'].get('data', {})
        if user_parameters is not None:
            partially_update_dict(user_parameters, parameters)

        if inputs is not None:
            self._connection_manager.connect(self, inputs)
            self._connection_manager.pull_input_files(self)
        self._io.create_output_files()

    def _run(self):
        node_instance = self.create_instance()
        adjusted_json_definition = (
            node_instance._sys_adjust_parameters(
                self.definition(), JSON_TYPEALIASES))
        node_instance._sys_execute(adjusted_json_definition, JSON_TYPEALIASES)

        self.parameters = adjusted_json_definition['parameters']['data']
        # Push the output file(s) to all connected nodes.
        self._connection_manager.push_output_files(self)

    def _configure(self, without_parameters=None):
        node_instance = self.create_instance()
        if without_parameters is None:
            definition = self.definition()
        else:
            definition = copy.deepcopy(self.definition())
            temp_parameters = definition['parameters']['data']
            for remove_parameter in without_parameters:
                remove_parameters_from_dict(remove_parameter, temp_parameters)
            definition['parameters']['data'] = temp_parameters

        adjusted_json_definition = (
            node_instance._sys_adjust_parameters(
                definition, JSON_TYPEALIASES))

        from sympathy.platform import qt_compat
        QtGui = qt_compat.import_module('QtGui')
        global QT_APP
        if QT_APP is None:
            QT_APP = QtGui.QApplication(sys.argv)

        configured_json_definition = node_instance._sys_exec_parameter_view(
            adjusted_json_definition, JSON_TYPEALIASES)

        new_parameters = configured_json_definition['parameters']['data']

        if without_parameters is None:
            self.parameters = new_parameters
        else:
            partially_update_dict(
                new_parameters, self._definition['parameters']['data'])

    def __str__(self):
        return self.name()


class ISyiBaseLibraryManager(object):
    def __init__(self):
        pass


def synode_factory(document, definition):
    def instantiate(inputs=None, execute_on_instantiation=True, **kwargs):
        return SyiNode(document, copy.deepcopy(definition),
                       inputs=inputs,
                       execute_on_instantiation=execute_on_instantiation,
                       **kwargs)
    return instantiate


class SyiNodes(object):
    """Keeps shortcuts to commonly used nodes as attributes. The nodes
    exposed as attributes change over time as the library evolves."""
    def __init__(self, document, execute_on_instantiation=True):
        self._execute_on_instantiation = execute_on_instantiation

        for key, nodeid in NODE_IDS.iteritems():
            setattr(self, key, synode_factory(document,
                                              LIBRARY_BY_NODEID[nodeid]))

    def __str__(self):
        text = 'Available nodes: {0}'.format(', '.join(sorted(NODE_IDS)))
        return str(text)


def create_synode_from_definition_copy(definition):
    return SyiNode(definition)


class SyiBaseTableLibraryManager(ISyiBaseLibraryManager):
    """Expose table base library functionality."""
    def __init__(self, node_creator):
        super(SyiBaseTableLibraryManager, self).__init__()
        self._node_creator = node_creator

    def _read_table(self, uri):
        table_node = self._node_creator.table(
            inputs=(self._node_creator.datasource(uri=uri),))

        fq_table_filename = table_node.io.output_port_by_name('port1').file
        return table.File(filename=fq_table_filename, mode='r')

    def read_csv(self, uri):
        return self._read_table(uri)

    def read_xls(self, uri):
        return self._read_table(uri)


class SyiLibraryManager(object):
    def __init__(self, node_creator):
        self.table = SyiBaseTableLibraryManager(node_creator)


class SyiNodeCreator(object):
    def __init__(self, library, mode='interactive'):
        pass


class SyWorkflow(object):
    def __init__(self, uri):
        xml_converter = xml_file_to_xmltojson_converter(uri)
        self._xml_dict = xml_converter.dict()
        self._node_uuids = {}
        self._input_port_uuids = {}
        self._output_port_uuids = {}


class DocumentGraph(object):
    """Graph to keep all connections between nodes in a document."""

    class Vertex(object):
        def __init__(self, name):
            self._name = name

        def __str__(self):
            return self._name

    ENTRY = Vertex('ENTRY')
    EXIT = Vertex('EXIT')

    def __init__(self):
        """Init."""
        self._vertices = []
        self._in_edges = collections.defaultdict(lambda: [])
        self._out_edges = collections.defaultdict(lambda: [])

        # Add ENTRY and EXIT vertices to graph.
        self._vertices.append(DocumentGraph.ENTRY)
        self._vertices.append(DocumentGraph.EXIT)
        self._out_edges[DocumentGraph.ENTRY] = [DocumentGraph.EXIT]
        self._in_edges[DocumentGraph.EXIT] = [DocumentGraph.ENTRY]

    def add_vertex(self, vertex):
        """Add vertex to graph."""
        self._vertices.append(vertex)
        self.add_edge(DocumentGraph.ENTRY, vertex)
        self.add_edge(vertex, DocumentGraph.EXIT)
        # self._in_edges[vertex] = [DocumentGraph.ENTRY]
        # self._out_edges[vertex] = [DocumentGraph.EXIT]
        return self

    def add_edge(self, src_node, dst_node):
        """Add edge to graph."""
        if DocumentGraph.EXIT in self._out_edges[src_node]:
            self.remove_edge(src_node, DocumentGraph.EXIT)
        if DocumentGraph.ENTRY in self._in_edges[dst_node]:
            self.remove_edge(DocumentGraph.ENTRY, dst_node)

        self._out_edges[src_node].append(dst_node)
        self._in_edges[dst_node].append(src_node)
        return self

    def remove_vertex(self, node):
        """Remove vertex from graph."""
        self._vertices.remove(node)

        for in_node in self._in_edges[node]:
            self._out_edges[in_node].remove(node)
            if self._out_edges[in_node] == []:
                self.add_edge(in_node, DocumentGraph.EXIT)

        for out_node in self._out_edges[node]:
            self._in_edges[out_node].remove(node)
            if self._in_edges[out_node] == []:
                self.add_edge(DocumentGraph.ENTRY, out_node)

        del self._in_edges[node]
        del self._out_edges[node]

    def remove_edge(self, src_node, dst_node):
        """Remove the edge from graph."""
        self._out_edges[src_node].remove(dst_node)
        self._in_edges[dst_node].remove(src_node)

    def vertices(self):
        """Return all vertices in graph."""
        return self._vertices

    def incoming_vertices(self, node):
        """Return all incoming vertices to the node."""
        return self._in_edges[node]

    def outgoing_vertices(self, node):
        """Return all outgoing vertices to the node."""
        return self._out_edges[node]


class DepthFirstSearchVisitor(object):
    """Perform depth first search on a DocumentGraph."""
    def __init__(self, graph):
        """Init."""
        self._graph = graph

        self._dfs_time = 0
        self._visited = {}
        self.discovery_time = {}
        self.finish_time = {}

    def traverse_and_apply(self, start_vertex):
        """Traverse graph using depth first search."""
        for vertex in self._graph.vertices():
            self._visited[vertex] = False
        self._search_postorder(start_vertex)

    def _search_postorder(self, u):
        """Search graph recursively in dfs order."""
        self._visited[u] = True
        self.discovery_time[u] = self._dfs_time
        self._dfs_time = self._dfs_time + 1

        for v in self._graph.outgoing_vertices(u):
            if not self._visited[v]:
                self._search_postorder(v)

        self.finish_time[u] = self._dfs_time
        self._dfs_time = self._dfs_time + 1
        # Apply method if used as a visitor
        self.apply(u)

    def apply(self, v):
        """Overrive this function to apply a function."""
        pass


class TopologicalSort(object):
    def __init__(self, graph, dfs_context):
        self._graph = graph
        self._dfs_context = dfs_context

    def sort(self):
        finish_times = reversed(sorted(self._dfs_context.finish_time.values()))
        node_time = {}
        for vertex in self._graph.vertices():
            node_time[vertex] = 0
        inverted_finish_time_dict = dict(
            {(v, k) for k, v in self._dfs_context.finish_time.iteritems()})

        for finish_time in finish_times:
            v = inverted_finish_time_dict[finish_time]
            in_nodes = self._graph.incoming_vertices(v)
            if in_nodes != []:
                maxdist = 0
                for in_node in in_nodes:
                    maxdist = max(node_time[in_node], maxdist)
                node_time[v] = maxdist + 1

        del node_time[DocumentGraph.ENTRY]
        del node_time[DocumentGraph.EXIT]
        return node_time


def with_curly_braces(uuid_):
    return '{{{}}}'.format(uuid_)


class SyiDocument(object):
    """Sympathy document."""
    def __init__(self):
        self._nodes = []
        self._connections = []
        self._graph = DocumentGraph()
        self._connection_manager = SyiConnectionManager(self._graph)

    def add_node(self, node):
        self._graph.add_vertex(node)

    def remove_node(self, node):
        """Remove node from document."""
        self._graph.remove_vertex(node)
        del self._nodes[node]

    def connect_ports(self, src_node, src_port_index,
                      dst_node, dst_port_index):
        """Create a connection between two nodes."""
        self._port_connection_manager.connect(
            src_node, src_port_index, dst_node, dst_port_index)
        self._graph.add_edge(src_node, dst_node)

    def remove_connection(self, src_node, src_port_index,
                          dst_node, dst_port_index):
        """Remove connection between two ports."""
        self._port_connection_manager.disconnect(
            src_node, src_port_index, dst_node, dst_port_index)
        self._graph.remove_edge(src_node, dst_node)

    def open_document(self, uri, use_flow_parameters):
        self._fq_workflow_filename = uri
        self._synodes = {}

        xml_converter = xml_file_to_xmltojson_converter(uri)
        xml_dict = xml_converter.dict()
        nodes = xml_dict['nodes']

        self._node_uuids = {}
        self._input_port_uuids = {}
        self._output_port_uuids = {}
        for node in nodes:
            uuid_ = node['uuid']
            self._node_uuids[uuid_] = node
            for port in node['ports']['inputs']:
                self._input_port_uuids[port['uuid']] = port
            for port in node['ports']['outputs']:
                self._output_port_uuids[port['uuid']] = port

        for uuid_, node in self._node_uuids.iteritems():
            nodeid = node['id']
            synode_creator = synode_factory(
                self, LIBRARY_BY_NODEID[nodeid])
            self._synodes[uuid_] = synode_creator(
                execute_on_instantiation=False)
            if use_flow_parameters:
                self._synodes[uuid_].parameters = json.loads(
                    node['parameters']['data'])
            else:
                node_parameters = copy.deepcopy(
                    self._synodes[uuid_]._definition['parameters'])
                partially_update_and_add_keys_dict(
                    json.loads(node['parameters']['data']),
                    node_parameters)
                self._synodes[uuid_].parameters = node_parameters

        self._connections = {}
        for connection in xml_dict['connections']:
            src = connection['source']
            src_node = self._synodes[src['node']]
            src_port = self._output_port_uuids[src['port']]
            src_port_index = src_port['index']

            dst = connection['destination']
            dst_node = self._synodes[dst['node']]
            dst_port = self._input_port_uuids[dst['port']]
            dst_port_index = dst_port['index']

            self._connection_manager._connect(
                src_node, src_port_index, dst_node, dst_port_index)

        return self
            # print 'Connecting', dst_node.name(), 'to', src_node.name()

    def node_by_uuid(self, uuid_):
        return self._synodes[uuid_]

    def execute_node_by_uuid(self, uuid_, instantiate_param_widget=False):
        # Execute with working dir set to workflow directory.
        old_dir = os.getcwdu()
        try:
            os.chdir(os.path.dirname(self._fq_workflow_filename))

            synode = self._synodes[uuid_]
            if instantiate_param_widget:
                synode.parameter_widget()
            synode.run()
        finally:
            os.chdir(old_dir)
        return synode

    def to_clipboard(self):
        from sympathy.platform import flow_model
        from sympathy.platform import qt_compat
        QtCore = qt_compat.import_module('QtCore')

        qt_app = qapplication_instance()

        clipboard = qt_app.clipboard()

        nodes = []
        for vertex in self._graph.vertices():
            if isinstance(vertex, SyiNode):
                nodes.append(vertex)

        flow = flow_model.Flow()

        flow_nodes = {}
        node_uuid_dict = {}
        node_inport_uuid_dict = collections.defaultdict(dict)
        node_outport_uuid_dict = collections.defaultdict(dict)
        # Ensure correct copy when Port.from_dict.
        # Create a good class structure.

        for node in nodes:
            flow_node = flow_model.Node.from_dict(node._definition)
            node_uuid = with_curly_braces(uuid.uuid1())
            flow_node.set_uuid(node_uuid)
            node_uuid_dict[node] = node_uuid

            self._set_port_uuid(
                flow_node.inputs(), node, node_inport_uuid_dict)
            self._set_port_uuid(
                flow_node.outputs(), node, node_outport_uuid_dict)

            flow_nodes[node] = flow_node
            flow.append_node(flow_node)

        for node in nodes:
            connections = self._connection_manager.get_forward_connections(
                node)
            for src_port_index, output_connections in connections.iteritems():
                flow_connection = flow_model.Connection()
                for dst_node, dst_port_index in output_connections:
                    src_node_uuid = node_uuid_dict[node]
                    src_port_uuid = (
                        node_outport_uuid_dict[node][src_port_index])
                    flow_connection.set_source(src_node_uuid, src_port_uuid)

                    dst_node_uuid = node_uuid_dict[dst_node]
                    dst_port_uuid = (
                        node_inport_uuid_dict[dst_node][dst_port_index])
                    flow_connection.set_destination(
                        dst_node_uuid, dst_port_uuid)
                    flow.append_connection(flow_connection.to_dict())

        dfs = DepthFirstSearchVisitor(self._graph)
        dfs.traverse_and_apply(DocumentGraph.ENTRY)
        topological_sort = TopologicalSort(self._graph, dfs)
        topological_times = topological_sort.sort()

        # time_count = collections.Counter(topological_times.itervalues())
        # top_max_count = max(time_count.itervalues())

        node_height = 50

        time_node_dict = collections.defaultdict(list)
        for top_node, top_time in topological_times.iteritems():
            time_node_dict[top_time].append(top_node)

        sorted_top_times = sorted(time_node_dict.keys())
        for top_time in sorted_top_times:
            top_nodes = time_node_dict[top_time]
            for index, top_node in enumerate(top_nodes, 1):
                flow_nodes[top_node].set_x((top_time - 1) * 150)
                if index % 2:
                    y_coordinate = 0 - (node_height / 1.5) * index
                else:
                    y_coordinate = 0 + (node_height / 1.5) * index
                flow_nodes[top_node].set_y(y_coordinate)

        d = flow.to_clipboard()

        # print json.dumps(d, indent=4)

        mime_type_itemlist = 'application-x-sympathy-itemlist'

        mime_data = QtCore.QMimeData()
        mime_data.setData(
            mime_type_itemlist, QtCore.QByteArray(json.dumps(d)))
        clipboard.setMimeData(mime_data)

    def _set_port_uuid(self, flow_ports, node, node_port_uuid_dict):
        for flow_port in flow_ports:
            port_uuid = with_curly_braces(uuid.uuid1())
            node_port_uuid_dict[node][flow_port.index()] = port_uuid
            flow_port.set_uuid(port_uuid)


class SyiDocumentManager(object):
    """Sympathy document manager."""
    def __init__(self, connection_manager):
        self._connection_manager = connection_manager

        self._documents = {}

    def open(self, uri, name=''):
        """Open existing document."""
        self._documents[name] = SyiDocument(self._connection_manager, uri)
        return self._documents[name]

    def create(self, name=''):
        """Create a document."""
        self._documents[name] = SyiDocument(self._connection_manager)
        return self._documents[name]

    def __getitem__(self, key):
        return self._documents[key]


class Syi(object):
    """Syi is the interactive mode of Sympathy for Data. It wraps the core
    functionality of the platform in a way suitable when working in an
    interactive environment like IPython."""
    def __init__(self):
        super(Syi, self).__init__()

        self._document = SyiDocument()
        # self.documents = SyiDocumentManager(self.connection_manager)
        self.node_creator = SyiNodes(self._document)
        self.library = SyiLibraryManager(self.node_creator)

    def open_workflow(self, uri, use_flow_parameters=True):
        return self._document.open_document(uri, use_flow_parameters)
