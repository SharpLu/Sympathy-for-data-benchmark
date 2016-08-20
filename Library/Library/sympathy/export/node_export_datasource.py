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
Datasources Export

The node is currently supporting extraction of zip and gzip files using
plugin_zip_exporter.py and plugin_gz_exporter.py

These plugins work somewhat differently compared with other exporter
plugins. They do not export the datasource itself, instead, they extract the
compressed archives pointed to by the datasources input and produce the
full list of extracted files in the datasources output.
"""
import os
import tempfile
from sympathy.api import exporters
from sympathy.api import datasource as dsrc
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyNodeError, sywarn


class ExportDatasources(synode.Node):
    """
    Export datasource to a selected data format.

    :Inputs:
        **Datasourcess** : Datasources
            Tables with data to export.
    :Outputs:
        **Datasources** : Datasources
            Datasources with paths to the created files.
    :Configuration:
        **Exporter to use**
            Select data format exporter. Each data format has its own exporter
            with its own special configuration, see exporter information. The
            selection of exporter do also suggest filename extension.
        **Output directory**
            Specify/select directory where the created files will be stored.
        **Filename(s) preview** : button
            When pressed a preview of all filenames will be presented under the
            considered button.
    :Opposite node: :ref:`Tables`
    :Ref. nodes: :ref:`Export ADAFs`
    """

    name = 'Export Datasources'
    description = 'Extract datassources'
    icon = 'export_datasource.svg'
    inputs = Ports([Port.Datasources(
        'Datasources to be exported', name='port0')])
    outputs = Ports([Port.Datasources(
        'Datasources of exported files', name='port0', scheme='text')])

    tags = Tags(Tag.Output.Export)
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2013 System Engineering Software Society'
    nodeid = 'org.sysess.sympathy.export.exportdatasources'
    version = '1.0'

    parameters = synode.parameters()
    parameters.set_string('active_exporter')
    custom_exporter_group = parameters.create_group('custom_exporter_data')
    parameters.set_string(
        'directory', value='.', label='Output directory',
        description='Select the directory where to export the files.',
        editor=synode.Util.directory_editor().value())
    parameters.set_string(
        'filename', label='Filename',
        description='Filename without extension.')

    def verify_parameters(self, node_context):
        parameter_root = synode.parameters(node_context.parameters)
        parameters_ok = "" != parameter_root.value_or_empty('active_exporter')
        return parameters_ok

    def exec_parameter_view(self, node_context):
        parameter_root = synode.parameters(node_context.parameters)
        export_params_widget = exporters.base.ExporterConfigurationWidget(
            exporters.utils.available_datasource_exporters(),
            parameter_root, node_context.input)
        widget = exporters.base.ExporterWidget(
            node_context, parameter_root, export_params_widget, dsrc)
        return widget

    def execute(self, node_context):
        parameter_root = synode.parameters(node_context.parameters)
        directory = parameter_root.value_or_empty('directory')
        if not os.path.isdir(directory):
            os.makedirs(directory)

        exporter_type = parameter_root['active_exporter'].value
        exporter = exporters.utils.datasource_exporter_factory(exporter_type)(
            parameter_root)
        input_list = node_context.input['port0']
        datasource_list = node_context.output['port0']
        number_of_objects = len(input_list)

        all_filenames = []
        for object_no, datasourcefile in enumerate(input_list):
            filenames = []
            try:
                filenames = exporter.export_data(datasourcefile, directory)
            except (IOError, OSError):
                raise SyNodeError(
                    'Unable to create file. Please check that you have '
                    'permission to write to the selected folder.')
            except:
                exporter.warn_invalid(datasourcefile)
            all_filenames.extend(filenames)
            for filename in filenames:
                # Output datasource is independent of input.
                datasource_file = dsrc.File()
                datasource_file.encode_path(
                    os.path.join(directory, filename))
                datasource_list.append(datasource_file)

            check_filenames(all_filenames)
            self.set_progress(100.0 * (1 + object_no) / number_of_objects)


def case_sensitive():
    """
    Trying to figure out weather or not the filesystem is case sensitive.
    This is done by opening the temporary filename in lowercase or capital
    letters checking if the file can be opened.
    """
    with tempfile.NamedTemporaryFile(prefix='case_', suffix='.cst') as tf:
        return not (os.path.exists(tf.name.lower()) and
                    os.path.exists(tf.name.upper()))


def check_filenames(filenames):
    result = []
    lookup = set()
    failed = []

    if case_sensitive():
        lookup.update(filenames)
        for filename in filenames:
            if filename in lookup:
                result.append(filename)
                lookup.remove(filename)
            else:
                failed.append(filename)
    else:
        lookup.update([filename.lower() for filename in filenames])
        for filename in filenames:
            if filename.lower() in lookup:
                result.append(filename)
                lookup.remove(filename.lower())
            failed.append(filename)

    if len(filenames) != len(result):
        sywarn(u'The following files could not be written: {}'.format(failed))
    return result
