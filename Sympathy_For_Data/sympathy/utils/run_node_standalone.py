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
import os
import sys
import glob
import json
import tempfile

#import qt_compat
import PySide.QtGui as QtGui


def load_json_type_aliases(typealias_path):
    json_type_aliases_filenames = glob.glob1(typealias_path, "*.json")
    type_aliases = {}
    for json_type_aliases_filename in json_type_aliases_filenames:
        fq_json_type_aliases_filename = os.path.join(
            typealias_path, json_type_aliases_filename)
        with open(fq_json_type_aliases_filename, 'r') as type_alias_file:
            typealias_dict = json.load(type_alias_file)
            alias_name = typealias_dict['name']
            del typealias_dict['name']
            del typealias_dict['color']
            type_aliases[alias_name] = typealias_dict
    json_type_aliases = json.dumps(type_aliases)
    return json_type_aliases


def load_json_definition(fq_json_definition_filename):
    json_definition = ""
    with open(fq_json_definition_filename, 'r') as json_definition_file:
        json_definition = json_definition_file.read()
    return json_definition


def inject_definition_files(json_definition, definition_filenames,
                            use_temp_output_files=True):
    injected_json_definition = json.loads(json_definition)
    input_ports = injected_json_definition['definition']['inputs']
    for port_name in input_ports.iterkeys():
        input_ports[port_name]['file'] = definition_filenames[port_name]

    output_ports = injected_json_definition['definition']['outputs']
    for output_port in output_ports.itervalues():
        with tempfile.NamedTemporaryFile(
                prefix='run_node_', suffix='.sydata', delete=False) as fq:
            output_port['file'] = fq.name
    return json.dumps(injected_json_definition)


def add_port_filename(portname, fq_filename, port_filename_dict):
    port_filename_dict[portname]['file'] = fq_filename


def run_node(sy_app_path, app_relative_support_path,
             fq_json_definition_filename, definition_filenames,
             node_path, source_filename, class_name, use_parameter_helper=True,
             parameter_initializer_fn=lambda x: x, execute_node=True,
             configure_node=True):
    # Add all necessary paths to PYTHONPATH the first thing.
    sys.path.append(node_path)

    json_definition = load_json_definition(fq_json_definition_filename)
    typealias_path = os.path.join(sy_app_path, "Library/typealias")
    json_type_aliases = load_json_type_aliases(typealias_path)

    json_definition = inject_definition_files(
        json_definition, definition_filenames)

    definition = json.loads(json_definition)
    try:
        definition['parameters']
    except KeyError:
        definition['parameters'] = {'type': 'group'}
    if use_parameter_helper:
        from sympathy.utils.parameter_helper import ParameterRoot
        parameters = ParameterRoot(definition['parameters'])
    else:
        parameters = definition['parameters']
    # Initialize parameters
    parameter_initializer_fn(parameters)
    json_definition = json.dumps(definition)

    fq_source_filename = os.path.join(node_path, source_filename)
    source_code = None
    with open(fq_source_filename, 'r') as f:
        source_code = f.read()
    compiled_code = compile(source_code, fq_source_filename, 'exec')
    context = {}
    eval(compiled_code, context, context)
    node = context[class_name]()

    app = QtGui.QApplication(sys.argv)
    adjusted_json_definition = (
        node._sys_adjust_parameters(json_definition, json_type_aliases))
    if configure_node:
        configured_json_definition = node._sys_exec_parameter_view(
            adjusted_json_definition, json_type_aliases)
    else:
        configured_json_definition = adjusted_json_definition
    if execute_node:
        node._sys_execute(configured_json_definition, json_type_aliases)
        print "Data is written to file(s):"
        output_ports = definition['definition']['outputs']
        for port in output_ports.values():
            print port['file']


def example():
    """Example how to run a node standalone. Function run_node(...) should
    be called from a different file in order to avoid commit/merge problems.
    """
    SY_APP_PATH = (
        "/Users/alexander/Projects/sympathy/code/sympathy-datasources/src")

    fq_json_definition_filename = os.path.join(
        SY_APP_PATH, "Library/sympathy/data/table/select_table_rows.json")

    definition_filenames = {}
    definition_filenames['port1'] = (
        "/Users/alexander/Projects/sympathy/code/"
        "sympathy-datasources/flows/cardata_table.h5")

    node_path = os.path.join(
        SY_APP_PATH, "Library/sympathy/data/table")
    app_relative_support_path = "Python/"
    absolute_support_path = os.path.join(
        SY_APP_PATH, app_relative_support_path)
    sys.path.append(absolute_support_path)

    from sympathy.utils.run_node_standalone import run_node as run_node_func

    run_node_func(
        sy_app_path=SY_APP_PATH,
        app_relative_support_path=app_relative_support_path,
        fq_json_definition_filename=fq_json_definition_filename,
        definition_filenames=definition_filenames,
        node_path=node_path,
        source_filename="select_table_rows.py",
        class_name='SelectTableRows')


if __name__ == '__main__':
    example()
