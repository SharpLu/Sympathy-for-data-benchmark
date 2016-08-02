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
Convert workflow files between JSON and XML formats. This tool is intended
to be used internally by the Sympathy platform.
"""
from xml.etree import ElementTree, ElementInclude
import sys
import os
import json
import argparse
import inspect
import urllib
import traceback
import copy
import logging

from lxml import etree

core_logger = logging.getLogger('core')

ns = 'http://www.sysess.org/sympathyfordata/workflow/1.0'


def xml_format_detector(source):
    """Parse source file to discover file format."""
    text = source.read()
    source.seek(0)
    file_format = 'unknown'
    if text.find(ns) >= 0:
        file_format = 'xml-1.0'
    elif (text.find('sympathy-document') >= 0 and
          text.find('gui_graph') >= 0):
        file_format = 'xml-alpha'
    elif text.find('sympathy-document') >= 0:
        file_format = 'xml-0.4'
    print('Detected format {}'.format(file_format))
    return file_format


def CDATA(text=None):
    """Return a CDATA section"""
    element = ElementTree.Element('![CDATA[')
    element.text = text
    return element

ElementTree._original_serialize_xml = ElementTree._serialize_xml


def _serialize_xml(write, elem, encoding, qnames, namespaces):
    """Fix for CDATA in ElementTree"""
    if elem.tag == '![CDATA[':
        write('<%s%s]]>\n' % (elem.tag, elem.text))
        return
    return ElementTree._original_serialize_xml(
        write, elem, encoding, qnames, namespaces)


ElementTree._serialize_xml = ElementTree._serialize['xml'] = _serialize_xml


class ToJsonInterface(object):
    """
    Interface for converters from XML to JSON/dict
    """
    def __init__(self, xml_file):
        self._xml_file = xml_file

    def json(self):
        """Return a JSON representation of the XML file"""
        raise NotImplementedError('Not implemented for interface.')

    def dict(self):
        """Return a dict representation of the XML file"""
        raise NotImplementedError('Not implemented for interface.')


class ToXmlInterface(object):
    """
    Interface for converters from dict to xml
    """
    def xml(self):
        """Return a XML data representation"""
        raise NotImplementedError('Not implemented for interface.')


class JsonToXml(ToXmlInterface):
    """
    Convert from JSON structure to XML using xml.dom.miniom
    """
    def __init__(self):
        super(JsonToXml, self).__init__()

    @classmethod
    def from_file(cls, json_file):
        """Create class instance from a JSON file"""
        instance = cls()
        instance._json_data = json.load(json_file)
        return instance

    @classmethod
    def from_dict(cls, dictionary):
        """Create class instance from a Python dictionary"""
        instance = cls()
        instance._json_data = dictionary
        return instance

    def xml(self):
        flow = self._flow_to_xml(None, self._json_data)
        return etree.tostring(
            flow, xml_declaration=True, pretty_print=True)

    def _flow_to_xml(self, parent, data):
        """Flow helper"""
        is_linked = data.get('is_linked', False) and parent is not None
        attribs_ = ['uuid', 'id', 'x', 'y', 'width', 'height', 'is_locked',
                    'cls', 'source_uuid']
        elements_ = ['label', 'description', 'author', 'copyright', 'version',
                     'source']
        if parent is not None:
            flow = etree.SubElement(parent, "flow")
        else:
            flow = etree.Element("flow", attrib={'xmlns': ns})
        self._add_attributes(flow, data, attribs_)

        if is_linked:
            flow.set('href', unicode(data['source']))

        self._add_text_elements(flow, data, elements_)

        if 'ports' in data:
            self._ports_to_xml(flow, data['ports'])

        if 'basic_ports' in data:
            self._ports_to_xml(flow, data['basic_ports'],
                               'basic_ports')

        if 'overrides' in data:
            self._json_element_to_xml('overrides', flow, data['overrides'])

        if 'aggregation_settings' in data:
            self._json_element_to_xml(
                'aggregation', flow, data['aggregation_settings'])

        if not is_linked:
            if 'parameters' in data:
                self._json_element_to_xml(
                    'parameters', flow, data['parameters'])

            converters = (
                ('flows', self._flow_to_xml),
                ('nodes', self._node_to_xml),
                ('connections', self._connection_to_xml),
                ('textfields', self._textfield_to_xml))

            for field, converter in converters:
                for elem in sorted(data.get(field, []),
                                   key=lambda x: x['uuid']):
                    converter(flow, elem)

        return flow

    def _add_text_elements(self, flow, data, element_list):
        """Create text nodes"""
        for elem in element_list:
            text_node = etree.SubElement(flow, elem)
            text_node.text = data.get(elem, '')

    def _add_attributes(self, node, data, attribute_list):
        """Attriubute helper"""
        for attrib in sorted(attribute_list):
            if attrib in data:
                node.set(attrib, unicode(data[attrib]))

    def _ports_to_xml(self, flow, data, ports_ns='ports'):
        """Port helper"""
        ports = etree.SubElement(flow, ports_ns)

        attribs_ = ['uuid', 'source_uuid', 'index', 'type', 'scheme',
                    'requiresdata', 'optional', 'x', 'y', 'width', 'height',
                    'key']
        elements_ = ['label', 'description']

        for tag, port_data_list in zip(('input', 'output'),
                                       (data['inputs'], data['outputs'])):
            for port_data in port_data_list:
                port_data['label'] = port_data['description']
                port_data['key'] = port_data['name']
                port = etree.SubElement(ports, tag)
                self._add_attributes(port, port_data, attribs_)
                self._add_text_elements(port, port_data, elements_)

    def _node_to_xml(self, flow, data):
        """Node helper"""
        attribs_ = ['uuid', 'id', 'x', 'y', 'width', 'height']
        elements_ = ['label', 'description', 'author', 'copyright', 'version']

        node = etree.SubElement(flow, 'node')
        self._add_attributes(node, data, attribs_)
        self._add_text_elements(node, data, elements_)

        if 'parameters' in data:
            # Do I need node to parameters?
            parameters = etree.SubElement(node, 'parameters')
            parameters.set('type', data['parameters']['type'])
            parameters.text = etree.CDATA(
                json.dumps(data['parameters']['data']).strip())
        if 'ports' in data:
            self._ports_to_xml(node, data['ports'])

    def _connection_to_xml(self, flow, data):
        """Connection helper"""
        attribs_con = ['uuid']
        attribs_port = ['node', 'port']

        # Apparently workflow_operations.update_workflow_configuration cause
        # the type to be None.
        ctype = data.get('type')
        if ctype:
            attribs_con.append('type')
        else:
            core_logger.warn(
                "Invalid or missing connection type for %s is None",
                data.get('uuid'))

        connection = etree.SubElement(flow, 'connection')
        self._add_attributes(connection, data, attribs_con)
        for tag in ['source', 'destination']:
            port_data = data[tag]
            port = etree.SubElement(connection, tag)
            self._add_attributes(port, port_data, attribs_port)

    def _textfield_to_xml(self, flow, data):
        """Textfield helper"""
        attribs_ = ['uuid', 'width', 'height', 'x', 'y']
        textfield = etree.SubElement(flow, 'text')
        self._add_attributes(textfield, data, attribs_)
        if 'text' in data and data['text']:
            textfield.text = data['text']
        else:
            textfield.text = ''

    def _json_element_to_xml(self, name, flow, data):
        element = etree.SubElement(flow, name)
        element.set('type', 'json')
        element.text = etree.CDATA(json.dumps(data).strip())


class XMLToJson(ToJsonInterface):
    """
    Convert from XML to JSON
    """
    type_dict = {
        'uuid': str,
        'id': str,
        'label': lambda x: unicode(x).strip(),
        'description': lambda x: unicode(x).strip(),
        'author': lambda x: unicode(x).strip(),
        'copyright': lambda x: unicode(x).strip(),
        'version': lambda x: unicode(x).strip(),
        'source': lambda x: unicode(x).strip(),
        'source_uuid': str,
        'x': float,
        'y': float,
        'width': float,
        'height': float,
        'index': int,
        'type': str,
        'key': lambda x: unicode(x).strip(),
        'scheme': str,
        'docs': str,
        'optional': lambda x: x.lower() == 'true',
        'requiresdata': lambda x: x.lower() == 'true',
        'node': str}

    def __init__(self, xml_file):
        super(XMLToJson, self).__init__(xml_file)
        self._doc = etree.parse(xml_file)
        self._file_root = os.path.dirname(xml_file.name)
        self._root = self._doc.getroot()

        # self._resolve_inclusions()
        self._all_nodes = {}
        self._all_parameters = {}

    def _resolve_inclusions(self, node):
        """Handle HREF links"""
        # Resolve inclusions - this is a rewritten version of
        # ElementInclude.include that only works for xml tags and also
        # injects a source attribute.
        flows = []
        parameters = []
        for i in xrange(len(node)):
            elem = node[i]
            if elem.tag == ElementInclude.XINCLUDE_INCLUDE:
                href = elem.get('href')
                parse = elem.get('parse', 'xml')
                if not parse == 'xml':
                    raise SyntaxError('Incorrect include type')
                included = self._url_loader(href, parse, self._file_root)
                included = copy.copy(included)
                included.set('source', href)
                included.set('is_linked', True)

                # Inject included node in the document.
                if elem.tail:
                    included.tail = (included.tail or '') + elem.tail
                node[i] = included

                if included.tag == self._add_ns('flow'):
                    flows.append(included)
                elif included.tag == self._add_ns('parameters'):
                    parameters.append(included)
                else:
                    print('Unknown include type {}'.format(included.tag))
        return flows, parameters

    def _url_loader(self, href, parse, root, encoding=None):
        """
        Loader for ElementInclude that handles relative paths and http includes
        """
        if not href.lower().startswith(('file:', 'http:', 'https:')):
            try:
                return ElementInclude.default_loader(
                    os.path.join(root, href), parse, encoding)
            except:
                return None

        file_ = urllib.urlopen(href)
        if parse == "xml":
            data = ElementTree.parse(file_).getroot()
        else:
            data = file_.read()
            if encoding:
                data = data.decode(encoding)
        file_.close()
        return data

    def _node_to_dict(self, node, path):
        """
        {
            "uuid": "fbbdc405-bb8a-4ad7-b3ac-a52649941b16",
            "x": 100,
            "y": 200,
            "width": 50,
            "height": 50,
            "id": "myid1",
            "label": "MyLabel",
            "author": "Greger Cronquist <greger.cronquist@sysess.org>",
            "copyright": "(c) 2013 System Engineering Software Society",
            "description": "Longer description should that be necessary",
            "docs": "file://document.html",
            "version": "1.0",
            "ports": {
                "inputs": [...],
                "outputs": [..]
            }
            "parameters": ...
        }


        {
            "flow": {
                "nodes": []
            }
        }

        """
        contents = self._get_standard_node_data(node, path)
        self._all_nodes['{}.{}'.format(path, contents['uuid'])] = contents
        return contents

    def _add_ns(self, tag):
        """Add XML namespace to tag"""
        return '{{{}}}{}'.format(ns, tag)

    def _get_standard_node_data(self, element, path):
        """Common attributes helper for nodes and flows."""
        contents = {}
        for tag in ['author', 'label', 'description', 'copyright', 'version',
                    'docs']:
            elems = element.findall(self._add_ns(tag))
            if len(elems) > 0:
                if elems[0].text:
                    text = self.type_dict[tag](elems[0].text)
                else:
                    text = ''
                contents[tag] = text

        for attribute in ['uuid', 'id', 'x', 'y', 'width', 'height']:
            if attribute in element.attrib:
                contents[attribute] = self.type_dict[
                    attribute](element.attrib[attribute])

        ports_ = element.findall(self._add_ns('ports'))
        if len(ports_) > 0:
            contents['ports'] = self._ports_to_dict(ports_[0])
        basic_ports_ = element.findall(self._add_ns('basic_ports'))
        if len(basic_ports_) > 0:
            contents['basic_ports'] = self._ports_to_dict(basic_ports_[0])
        params = element.findall(self._add_ns('parameters'))
        if len(params) > 0:
            contents['parameters'] = self._parameters_to_dict(
                params[0], '{}.{}'.format(path, contents['uuid']))

        return contents

    def _include_subflow(self, root, href):
        included_flow = self._url_loader(href, 'xml', root)
        return included_flow

    def _flow_to_dict(self, flow, path, root):
        """
        {
            "uuid": "fbbdc405-bb8a-4ad7-b3ac-a52649941b16",
            "x": 100.0,
            "y": 200.0,
            "width": 50.0,
            "height": 50.0,
            "id": "myid1",
            "label": "MyLabel",
            "author": "Greger Cronquist <greger.cronquist@sysess.org>",
            "copyright": "(c) 2013 System Engineering Software Society",
            "description": "Longer description should that be necessary",
            "docs": "file://document.html",
            "source": "file://OriginalSourceFile.syx",
            "is_linked": False,
            "version": "1.0",
            "parameters": {},
            "aggregation_settings": {},
            "overrides": {},
            "ports": {
                "inputs": [...],
                "outputs": [..]
            },
            "flows": [ flows... ],
            "nodes": [ nodes... ],
            "connections": [
                {
                    "uuid": "fbbdc405-bb8a-4ad7-b3ac-a52649941c19",
                    "source": {
                        "node": "fbbdc405-bb8a-4ad7-b3ac-a52649941b17",
                        "port": "fbbdc405-bb8a-4ad7-b3ac-a52649941b17"
                    },
                    "destination": {
                        "node": "fbbdc405-bb8a-4ad7-b3ac-a52649941b11",
                        "index": 0
                    }
                }
            ]
            "parameters": ...
        }
        """
        new_root = root

        # TODO(Greger) Only accept parameters using xi:include?
        inc_flows, inc_params = self._resolve_inclusions(flow)

        # Read linked flow.
        contents_ = self._get_standard_node_data(flow, path)
        contents_['is_locked'] = (
            True if (flow.get('is_locked', 'False')) == 'True' else False)
        contents_['cls'] = flow.get('cls', 'Flow')

        if 'href' in flow.keys():
            source = flow.get('href')
            linked_flow = self._include_subflow(root, source)

            if linked_flow is None:
                contents = contents_
                contents['broken_link'] = True
                contents['source'] = source
                contents['filename'] = os.path.join(root, source)
            else:
                new_root = os.path.join(root, os.path.dirname(source))
                contents = self._get_standard_node_data(linked_flow, path)
                for key in ('label', 'description', 'x', 'y', 'width',
                            'height'):
                    contents[key] = contents_[key]

                contents['source_uuid'] = contents['uuid']
                contents['uuid'] = contents_['uuid']

                for port_ in (contents_['ports']['inputs'] +
                              contents_['ports']['outputs']):
                    port = None
                    for p in (contents['ports']['inputs'] +
                              contents['ports']['outputs']):
                        if ('source_uuid' in port_ and p['uuid'] ==
                                port_['source_uuid']):
                            port = p
                            break
                    if port:
                        port['source_uuid'] = port['uuid']
                        port['uuid'] = port_['uuid']
                    else:
                        pass
                        # TODO (Magnus): Fall back on matching ports by order?
                contents['source'] = source
                contents['filename'] = os.path.join(root, source)
                contents['is_linked'] = True

                overrides = flow.findall(self._add_ns('overrides'))
                if len(overrides) > 0:
                    contents['overrides'] = self._json_element_to_dict(
                        overrides[0])

                flow = linked_flow

        else:
            contents = contents_

        aggregation_settings = flow.findall(self._add_ns('aggregation'))
        if len(aggregation_settings) > 0:
            contents['aggregation_settings'] = self._json_element_to_dict(
                aggregation_settings[0])

        # if 'source' in flow.keys():
        #     contents['source'] = flow.get('source')
        # if 'is_linked' in flow.keys():
        #     contents['is_linked'] = flow.get('is_linked')

        if len(path) > 0:
            new_path = '{}.{}'.format(path, contents['uuid'])
        else:
            new_path = contents['uuid']
        flows = [self._flow_to_dict(flow_, new_path, new_root)
                 for flow_ in flow.findall(self._add_ns('flow'))]
        contents['flows'] = flows
        nodes = [self._node_to_dict(node, new_path)
                 for node in flow.findall(self._add_ns('node'))]
        contents['nodes'] = nodes
        connections = [self._connection_to_dict(connection, new_path)
                       for connection in flow.findall(
                           self._add_ns('connection'))]
        contents['connections'] = connections
        textfields = [self._textfield_to_dict(textfield, new_path)
                      for textfield in flow.findall(
                          self._add_ns('text'))]
        contents['textfields'] = textfields

        return contents

    def _ports_to_dict(self, ports):
        """
        "ports": {
            "inputs": [...],
            "outputs": [..]
        }

        input/output:
        {
            "uuid": "fbbdc405-bb8a-4ad7-b3ac-a52649941b16",
            "index": "0",
            "type": "table",
            "scheme": "hdf5",
            "requiresdata": True,
            "optional": False,
            "label": "Input 1"
            "key": "Input 1"
        }
        """
        contents = {}
        inputs = []
        outputs = []

        for tag, list_ in zip(['input', 'output'], [inputs, outputs]):
            for value in ports.findall(self._add_ns(tag)):
                port = {}
                for attribute in ['uuid', 'type', 'scheme', 'index',
                                  'requiresdata', 'optional', 'x', 'y',
                                  'width', 'height', 'key', 'source_uuid']:
                    if attribute in value.attrib:
                        port[attribute] = self.type_dict[
                            attribute](value.attrib[attribute])
                if 'key' in port:
                    port['name'] = port['key']

                label = value.findall(self._add_ns('label'))
                if len(label) > 0:
                    port['description'] = (
                        self.type_dict['label'](label[0].text))
                list_.append(port)

        contents['inputs'] = inputs
        contents['outputs'] = outputs
        return contents

    def _parameters_to_dict(self, parameters, path):
        """
        {
            "type": "json",
            "data": base64 blob
        }
        """
        contents = {}
        node_path = path
        if 'node' in parameters.attrib:
            node_path += '.{}'.format(parameters.attrib['node'])

        contents['type'] = parameters.attrib['type'].strip()
        data = parameters.text.strip()
        contents['data'] = json.loads(data)

        self._all_parameters[node_path] = contents

        return contents

    def _json_element_to_dict(self, json_element):
        data = json_element.text.strip()
        contents = json.loads(data)
        return contents

    def _connection_to_dict(self, connection, path):
        """
        {
            "uuid": "fbbdc405-bb8a-4ad7-b3ac-a52649941c19",
            "source": {
                "node": "fbbdc405-bb8a-4ad7-b3ac-a52649941b17",
                "port": "fbbdc405-bb8a-4ad7-b3ac-a52649941b18"
            },
            "destination": {
                "node": "fbbdc405-bb8a-4ad7-b3ac-a52649941b18",
                "port": "fbbdc405-bb8a-4ad7-b3ac-a52649981b16"
            }
        }
        """
        contents = {}
        source = {}
        destination = {}
        contents['uuid'] = connection.attrib['uuid']
        contents['type'] = connection.attrib.get('type')

        for dict_, tag in zip([source, destination],
                              ['source', 'destination']):
            port = connection.findall(self._add_ns(tag))[0]
            dict_['node'] = port.attrib['node']
            dict_['port'] = port.attrib['port']
            contents[tag] = dict_
        return contents

    def _textfield_to_dict(self, textfield, path):
        """
        {
            "height", 10.0,
            "text": "Hello world",
            "uuid": "fbbdc405-bb8a-4ad7-b3ac-a52649941c19",
            "width", 10.0,
            "x", 10.0,
            "y", 10.0
        }
        """
        contents = {}
        for attrib in ['uuid', 'x', 'y', 'height', 'width']:
            if attrib in textfield.attrib:
                contents[attrib] = self.type_dict[
                    attrib](textfield.attrib[attrib])
        contents['text'] = textfield.text
        return contents

    def _get_tag(self, element):
        """Tag split helper"""
        return element.tag.split('}', 1)[1]

    def _create_dictionary_from_xml(self, element):
        """Main XML parser loop"""
        tag = self._get_tag(element)
        if not tag == 'flow':
            raise RuntimeError('Not a proper workflow')
        all_contents = self._flow_to_dict(element, '', self._file_root)
        for node_path in self._all_parameters:
            if node_path in self._all_nodes:
                self._all_nodes[node_path]['parameters'] = (
                    self._all_parameters[node_path])
        return all_contents

    def json(self):
        return json.dumps(self._create_dictionary_from_xml(self._root),
                          sort_keys=True, separators=(',', ':'))

    def dict(self):
        return self._create_dictionary_from_xml(self._root)


def xml_file_to_xmltojson_converter(fq_xml_filename):
    """Simple XML to JSON parser helper"""
    to_json_converter = None
    with open(fq_xml_filename, 'r') as source_file:
        source_format = xml_format_detector(source_file)

        if source_format == 'xml-1.0':
            to_json_converter = XMLToJson(source_file)
        else:
            raise NotImplementedError(
                'XML {} not yet supported'.format(source_format))
    assert(to_json_converter is not None)
    return to_json_converter


TO_JSON_FORMAT_CLASSES = {
    'xml-1.0': XMLToJson}


def main():
    """
    Convert between different Sympathy workflow descriptions:

      - From JSON to XML)
      - From XML to JSON
    """
    parser = argparse.ArgumentParser(description=inspect.getdoc(main))
    parser.add_argument('--source-format', action='store',
                        choices=['json', 'xml-1.0',
                                 'detect'], required=True,
                        dest='source_format')
    parser.add_argument('--destination-format', action='store',
                        choices=['json', 'xml-1.0'], required=True,
                        dest='destination_format')
    parser.add_argument('source_file', action='store')
    parser.add_argument('destination_file', action='store')

    session = os.getenv('SY_TEMP_SESSION')
    if session is None:
        session = '.'
    return_code = 0
    with open(os.path.join(session, 'workflow_converter.log'), 'w') as log:
        stdout = sys.stdout
        sys.stdout = log
        write_is_allowed = False
        arguments = parser.parse_args(sys.argv[1:])
        with open(arguments.source_file, 'r') as source:
            source_format = arguments.source_format
            destination_format = arguments.destination_format
            try:
                if (source_format == 'detect' and
                        destination_format == 'json'):
                    source_format = xml_format_detector(source)

                if source_format == 'json':
                    if destination_format == 'xml-1.0':
                        # to_xml_converter = JsonToXml(source)
                        to_xml_converter = JsonToXml.from_file(source)
                        output_data = to_xml_converter.xml()
                        write_is_allowed = True
                    else:
                        print('Conversion {} -> {} not yet supported'.
                              format(source_format, destination_format))
                elif destination_format == 'json':
                    if source_format in TO_JSON_FORMAT_CLASSES:
                        to_json_converter = TO_JSON_FORMAT_CLASSES[
                            source_format](source)
                    else:
                        print('Conversion {} -> {} not yet supported'.
                              format(source_format, destination_format))
                    output_data = to_json_converter.json()
                    write_is_allowed = True

                else:
                    print('Conversion {} -> {} not yet supported'.format(
                          source_format,
                          destination_format))

            except Exception as error:
                print('workflow_converter critical error {0}'.format(error))
                print(traceback.format_exc())
                return_code = 1

            if write_is_allowed:
                with open(arguments.destination_file, 'w') as destination:
                    destination.write(output_data.encode('UTF-8'))

        sys.stdout = stdout
    sys.exit(return_code)


if __name__ == '__main__':
    main()
