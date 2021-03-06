# -*- coding: utf-8 -*-
# Copyright (c) 2014, System Engineering Software Society
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
Apply new data to an existing report template and export visual elements.

**Signal Mapping**
    Map input signal names to template signal names. If the input
    signal field is empty the template signal name will be used.
    Input signals are chosen using a combo box in which the length and
    the name of the signal are shown. The signal name is always
    presented as "table_name.column_name". There is currently no
    check to ensure that the same signal length is used for template
    signals which require same length (a plot is only meaningful if
    e.g. the length of the x-coordinates and the length of the
    y-coordinates match).
"""
import re
import os
import sys
import json
import tempfile
import subprocess

from sympathy.api import node as synode
from sympathy.api import adaf, table
from sympathy.api.exceptions import SyNodeError, sywarn
from sympathy.api.nodeconfig import Ports, Port, Tag, Tags
from sympathy.api import report
from sylib.report import gui_signal_mapping


class DataType(object):
    adaf = 'adafs'
    table = 'tables'


def file_type(data_type):
    if data_type == 'adafs':
        return adaf.FileList
    elif data_type == 'tables':
        return table.FileList
    else:
        assert(False)


def generate_widgets(node, node_context, data_type, filenames=None):
    node.set_progress(0)

    # Read files and parameters
    parameter_root = synode.parameters(node_context.parameters)
    file_format = parameter_root['file_format'].list[
        parameter_root['file_format'].value[0]]
    if 'save_path' in parameter_root.keys():
        save_path = parameter_root['save_path'].value
    else:
        save_path = None
    if 'filename_prefix' in parameter_root.keys():
        prefix = parameter_root['filename_prefix'].value
    else:
        prefix = None
    template = node_context.input[0].get()
    input_data = node_context.input[1]
    signal_mapping = parameter_root['signal_mapping'].value

    node.set_progress(15)

    # Write input data to a file accessible to the qt process.
    transfer_file = tempfile.NamedTemporaryFile(
        dir=os.environ['SY_TEMP_SESSION'], suffix='.sydata', delete=False)
    transfer_file.close()
    with file_type(data_type)(filename=transfer_file.name, mode='w') as f:
        f.source(input_data)

    node.set_progress(20)

    # Create the widgets in a different process.
    from sylib.report import write_reports
    python_file = write_reports.__file__
    function_args = [template, signal_mapping, transfer_file.name, data_type,
                     file_format, json.dumps(save_path), json.dumps(prefix),
                     json.dumps(filenames)]
    sys_path = json.dumps(sys.path)
    proc = subprocess.Popen(
        [sys.executable, python_file, sys_path] + function_args,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errors = proc.communicate()
    output = output.decode('utf8')
    errors = errors.decode('utf8')

    # Read stdout too see if any error occurs.
    error_re = re.compile(r'__ERROR__ \((.*)\)', re.MULTILINE)
    error_match = error_re.search(errors)
    if error_match:
        raise SyNodeError(error_match.group(1))
    elif proc.returncode > 0:
        raise SyNodeError("Could not create output files.")
    elif proc.returncode < 0:
        raise SyNodeError(
            "Could not create output files (python process crashed).")
    else:
        warn_re = re.compile(r'__WARNING__ \((.*)\)', re.MULTILINE)
        warnings = warn_re.findall(errors)
        if warnings:
            sywarn("\n".join(warnings))
    filenames_json = output
    filenames = json.loads(filenames_json)
    os.remove(transfer_file.name)

    return filenames


class ReportApplyTables(synode.Node):
    """
    Applies new data to an existing report template and exports visual
    elements.

    :Inputs:
        **ReportTemplate**: Report
            Document template for visualization of data.
        **TableList**: Tables
            List of tables to use as data sources for the document template.
    :Configuration:
        **Signal Mapping**
            See above.
        **Save Path**
            Path to save images to.
        **Filename Prefix**
            Prefix of file which becomes ``<prefix><file#>.<suffix>``.
        **File Format**
            File format used when saving images.
    :Ref. nodes: :ref:`Report Template Tables`
    """

    name = 'Report Apply Tables'
    nodeid = 'org.sysess.sympathy.report.apply.tables'
    author = 'Stefan Larsson <stefan.larsson@combine.se>'
    copyright = '(C) 2014 System Engineering Software Society'
    version = '1.0'
    icon = 'report-apply.svg'
    tags = Tags(Tag.Visual.Report)

    inputs = Ports([
        report.Report('Report template', name='template'),
        Port.Tables('List of tables', name='tables')])
    outputs = Ports([
        Port.Datasources('Output files', name='dsrc')])

    parameters = synode.parameters()
    parameters.set_string(
        'save_path',
        value='',
        label='Save Path',
        description='Path to save report pages to.',
        editor=synode.Util.directory_editor().value())
    parameters.set_string(
        'filename_prefix',
        value='',
        label='Filename Prefix',
        description='Prefix of saved files.')
    parameters.set_list(
        'file_format',
        value=[0],
        plist=['png', 'jpg'],
        label='File Format',
        editor=synode.Util.combo_editor().value(),
        description='File format of exported pages.')
    parameters.set_string(
        'signal_mapping',
        value='{}',
        label='Signal Mapping',
        description='Mapping of incoming signal names to template signal '
                    'names.')

    def execute(self, node_context):
        filenames = generate_widgets(self, node_context, DataType.table)

        output = node_context.output['dsrc']
        for f in filenames:
            dsrc = output.create()
            dsrc.encode_path(f)
            output.append(dsrc)

    def exec_parameter_view(self, node_context):
        document = None
        input_tables = None
        if (node_context.input[0].is_valid() and
                node_context.input[1].is_valid()):
            document = json.loads(node_context.input[0].get())
            input_tables = node_context.input[1]
        return gui_signal_mapping.SignalMappingWidget(node_context.parameters,
                                                      document,
                                                      input_tables,
                                                      DataType.table)


class ReportApplyADAFs(synode.Node):
    """
    Applies new data to an existing report template and exports visual
    elements.

    :Inputs:
        **ReportTemplate**: Report
            Document template for visualization of data.
        **ADAFList**: ADAFs
            List of ADAFs to use as data sources for the document template.
    :Configuration:
        **Signal Mapping**
            See above.
        **Save Path**
            Path to save images to.
        **Filename Prefix**
            Prefix of file which becomes ``<prefix><file#>.<suffix>``.
        **File Format**
            File format used when saving images.
    :Ref. nodes: :ref:`Report Template ADAFs` :ref:`Report Template Tables`
    """

    name = 'Report Apply ADAFs'
    nodeid = 'org.sysess.sympathy.report.apply.adafs'
    author = 'Stefan Larsson <stefan.larsson@combine.se>'
    copyright = '(C) 2014 System Engineering Software Society'
    version = '1.0'
    icon = 'report-apply.svg'

    inputs = Ports([
        report.Report('Report Template', name='template'),
        Port.ADAFs('Input ADAFs', name='adafs')])
    outputs = Ports([
        Port.Datasources('Output files', name='dsrc')])
    tags = Tags(Tag.Visual.Report)

    parameters = synode.parameters()
    parameters.set_string(
        'save_path',
        value='',
        label='Save Path',
        description='Path to save report pages to.',
        editor=synode.Util.directory_editor().value())
    parameters.set_string(
        'filename_prefix',
        value='',
        label='Filename Prefix',
        description='Prefix of saved files.')
    parameters.set_list(
        'file_format',
        value=[0],
        plist=['png', 'jpg'],
        label='File Format',
        editor=synode.Util.combo_editor().value(),
        description='File format of exported pages.')
    parameters.set_string(
        'signal_mapping',
        value='{}',
        label='Signal Mapping',
        description='Mapping of incoming signal names to template signal '
                    'names.')

    def execute(self, node_context):
        filenames = generate_widgets(self, node_context, DataType.adaf)

        output = node_context.output['dsrc']
        for f in filenames:
            dsrc = output.create()
            dsrc.encode_path(f)
            output.append(dsrc)

    def exec_parameter_view(self, node_context):
        document = None
        input_data = None
        if (node_context.input[0].is_valid() and
                node_context.input[1].is_valid()):
            document = json.loads(node_context.input[0].get())
            input_data = node_context.input[1]
        return gui_signal_mapping.SignalMappingWidget(node_context.parameters,
                                                      document,
                                                      input_data,
                                                      DataType.adaf)


class ReportApplyADAFsWithDsrc(synode.Node):
    """
    Applies new data to an existing report template and exports visual
    elements to the datasources recieved on one of the input ports.

    :Ref. nodes: :ref:`Report Template ADAFs` :ref:`Report Template Tables`
    """

    name = 'Report Apply ADAFs with Datasources'
    nodeid = 'org.sysess.sympathy.report.apply.adafswithdsrcs'
    author = 'Magnus Sandén <magnus.sanden@combine.se>'
    copyright = '(C) 2016 System Engineering Software Society'
    version = '1.0'
    icon = 'report-apply.svg'

    inputs = Ports([
        report.Report('Report Template', name='template'),
        Port.ADAFs('Input ADAFs', name='adafs'),
        Port.Datasources('Save path', name='dsrc')])
    outputs = Ports([
        Port.Datasources('Output files', name='dsrc')])
    tags = Tags(Tag.Visual.Report)

    parameters = synode.parameters()
    parameters.set_list(
        'file_format',
        value=[0],
        plist=['png', 'jpg'],
        label='File Format',
        editor=synode.Util.combo_editor().value(),
        description='File format of exported pages.')
    parameters.set_string(
        'signal_mapping',
        value='{}',
        label='Signal Mapping',
        description='Mapping of incoming signal names to template signal '
                    'names.')

    def execute(self, node_context):
        dsrcs = node_context.input['dsrc']
        input_filenames = [dsrc.decode_path() for dsrc in dsrcs]
        filenames = generate_widgets(self, node_context, DataType.adaf,
                                     filenames=input_filenames)

        output = node_context.output['dsrc']
        for f in filenames:
            dsrc = output.create()
            dsrc.encode_path(f)
            output.append(dsrc)

    def exec_parameter_view(self, node_context):
        document = None
        input_data = None
        if (node_context.input[0].is_valid() and
                node_context.input[1].is_valid()):
            document = json.loads(node_context.input[0].get())
            input_data = node_context.input[1]
        return gui_signal_mapping.SignalMappingWidget(node_context.parameters,
                                                      document,
                                                      input_data,
                                                      DataType.adaf)
