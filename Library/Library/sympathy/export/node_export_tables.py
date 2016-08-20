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
The exportation of data is the final step in an analysis workflow. The analysis
is performed and the result must to be exported to an additional data format
for presentation or visualisation. Or, Sympathy for Data has been used for
data management, where data from different source has been gathered and merged
into a joint structure that can be exported to different data format.

There exists exportation from the following internal data types:
    - :ref:`Export Tables`
    - :ref:`Export RAW Tables`
    - Text, to be implemented,
    - :ref:`Export ADAFs`

The exportation nodes are all based on the use of plugins, the same structure
as the importation nodes. Each supported data format has its own plugin, and
may also have a specific GUI settings.

At the moment, exportation of Tables are supported to following data formats:
    - CSV
    - HDF5
    - SQL
    - SQLite
    - XLS
    - XLSX

In the separate node, :ref:`Export RAW Tables`, the internal structure of
Tables are exported into a single file, where data format is connected to
Sympathy with the extension .sydata.

The exportation nodes can also be used for storing partial results on disk.
The stored data can be reimplemented further ahead in the workflow by
connecting the outgoing datasources to an importation node.

If the input Table(s) has a plot attribute (as created by e.g.,
:ref:`Plot Tables`) it can be exported to a separate file by selecting one of
the extensions in the output section.
"""
import os
import itertools

from sympathy.api import exporters
from sympathy.api import datasource as dsrc
from sympathy.api import table
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyNodeError
from sylib.plot import backend as plot_backends
from sylib.plot import model as plot_models


class ExportTables(synode.Node):
    """
    Export tables to a selected data format.

    :Inputs:
        **Tables** : Tables
            Tables with data to export.
    :Outputs:
        **Datasources** : Datasources
            Datasources with paths to the created files.
    :Configuration:
        **Exporter to use**
            Select data format exporter. Each data format has its own exporter
            with its own special configuration, see exporter information. The
            selection of exporter do also suggest filename extension.
        **Filename extension**
            Specify a new extension if you are not satisfied with the
            predefined one for the exporter.
        **Output directory**
            Specify/select directory where the created files will be stored.
        **Filename**
            Specify the common base for the filenames. If there are several
            incoming Tables the node will add "_${index number of corresponding
            Table in the incoming list}" after the base for each file. If
            nothing is specified the filename will be equal to index number.
            Do not specify extension.
        **Filename(s) preview** : button
            When pressed a preview of all filenames will be presented under the
            considered button.
    :Opposite node: :ref:`Tables`
    :Ref. nodes: :ref:`Export ADAFs`
    """

    name = 'Export Tables'
    description = 'Export Tables'
    icon = 'export_table.svg'
    inputs = Ports([Port.Tables('Tables to be exported', name='port0')])
    outputs = Ports([Port.Datasources(
        'Datasources of exported files', name='port0', scheme='text')])

    tags = Tags(Tag.Output.Export)
    author = 'Alexander Busck <alexander.busck@combine.se>'
    copyright = '(c) 2013 Combine AB'
    nodeid = 'org.sysess.sympathy.export.exporttables'
    version = '0.1'

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
    parameters.set_list(
        'plot',
        label='Output separate plot file with the following extension:',
        description='If there is a plot attribute in the input tables(s), '
        'create a separate file with the plot.',
        value=[0],
        plist=['-', 'eps', 'pdf', 'svg', 'png'],
        editor=synode.Util.combo_editor().value())

    def verify_parameters(self, node_context):
        parameter_root = synode.parameters(node_context.parameters)
        parameters_ok = "" != parameter_root.value_or_empty('active_exporter')
        return parameters_ok

    def exec_parameter_view(self, node_context):
        parameter_root = synode.parameters(node_context.parameters)
        export_params_widget = exporters.base.ExporterConfigurationWidget(
            exporters.utils.available_table_exporters(),
            parameter_root, node_context.input)
        widget = exporters.base.ExporterWidget(
            node_context, parameter_root, export_params_widget, table)
        return widget

    def execute(self, node_context):
        parameter_root = node_context.parameters
        exporter_type = parameter_root['active_exporter'].value
        filename = parameter_root.value_or_empty('filename')
        directory = parameter_root.value_or_empty('directory')
        if not os.path.isdir(directory):
            os.makedirs(directory)
        exporter_parameter_root = parameter_root[
            'custom_exporter_data'][exporter_type]

        exporter = exporters.utils.table_exporter_factory(exporter_type)(
            exporter_parameter_root)
        # Create filenames from the parameter_root and the data available
        # as input. If active the exporter will use a specific filename
        # strategy when creating the filenames.

        fq_filenames = exporters.base.create_fq_filenames(
            directory, exporter.create_filenames(node_context.input, filename))

        if 'plot' in parameter_root:
            plot = parameter_root['plot'].selected
            plot = None if plot == '-' else plot
        else:
            plot = None

        if isinstance(fq_filenames, list):
            number_of_filenames = len(fq_filenames)
        else:
            number_of_filenames = None

        input_list = node_context.input['port0']
        datasource_list = node_context.output['port0']
        number_of_objects = len(input_list)

        exporter_class = (
            exporters.utils.table_exporter_factory(
                exporter_type))
        exporter_parameter_root = synode.parameters(
            node_context.parameters[
                'custom_exporter_data'][exporter_type])

        exporter = exporter_class(exporter_parameter_root)

        if number_of_filenames is None:
            for object_no, (fq_outfilename, table_file) in enumerate(
                    itertools.izip(fq_filenames, input_list)):

                if not os.path.isdir(os.path.dirname(fq_outfilename)):
                    os.makedirs(os.path.dirname(fq_outfilename))
                datasource_file = dsrc.File()
                datasource_file.encode_path(fq_outfilename)
                datasource_list.append(datasource_file)

                try:
                    exporter.export_data(table_file, fq_outfilename)
                except (IOError, OSError):
                    raise SyNodeError(
                        'Unable to create file. Please check that you have '
                        'permission to write to the selected folder.')
                if plot is not None:
                    plots_model = plot_models.get_plots_model(
                        table_file)
                    plot_exporter = plot_backends.ExporterBackend(
                        plots_model, plot)
                    plot_exporter.render(
                        os.path.splitext(fq_outfilename)[0])

                self.set_progress(
                    100.0 * (1 + object_no) / number_of_objects)

        else:
            fq_outfilename = fq_filenames[0]
            datasource_file = dsrc.File()
            datasource_file.encode_path(fq_outfilename)
            datasource_list.append(datasource_file)

            exporter.export_data(input_list, fq_outfilename)

            if plot is not None:
                for table_file, i in zip(input_list, range(len(input_list))):
                    plots_model = plot_models.get_plots_model(table_file)
                    plot_exporter = plot_backends.ExporterBackend(
                        plots_model, plot)
                    filename = (
                        os.path.splitext(fq_outfilename)[0] + '_' + str(i))
                    plot_exporter.render(filename)

            self.set_progress(100)


class ExportRAWTables(synode.Node):
    """
    Export tables to the internal data format .sydata.

    :Inputs:
        **Tables** : Tables
            Tables with data to export.
    :Outputs:
        **Datasources** : Datasource
            Datasource with paths to the created file.
    :Configuration:
        **Output directory**
            Specify/select directory where the created files will be stored.
        **Filename**
            Specify filename.
    :Opposite node: :ref:`RAW Tables`
    :Ref. nodes: :ref:`Export Tables`
    """

    name = 'Export RAW Tables'
    description = 'Export RAW Tables'
    icon = 'export_table.svg'
    inputs = Ports([Port.Tables('Tables to be exported', name='port0')])
    outputs = Ports([Port.Datasource(
        'Datasources of exported files', name='port0', scheme='text')])

    author = 'Alexander Busck <alexander.busck@combine.se>'
    copyright = '(c) 2013 Combine AB'
    nodeid = 'org.sysess.sympathy.export.exportrawtables'
    version = '0.12a'
    tags = Tags(Tag.Output.Export)

    parameters = synode.parameters()
    parameters.set_string(
        'directory', value='.', label='Output directory',
        description='Select the directory where to export the files.',
        editor=synode.Util.directory_editor().value())
    parameters.set_string(
        'filename', label='Filename',
        description='Filename without extension.')

    def verify_parameters(self, node_context):
        parameter_root = synode.parameters(node_context.parameters)
        filename = parameter_root.value_or_empty('filename')
        return filename != ''

    def execute(self, node_context):
        parameter_root = synode.parameters(node_context.parameters)

        directory = parameter_root['directory'].value
        if not os.path.isdir(directory):
            os.makedirs(directory)
        filename = parameter_root['filename'].value
        fq_outfilename = '{}{}{}'.format(
            os.path.join(directory, filename), os.path.extsep, 'sydata')

        in_table_file = node_context.input['port0']
        with table.FileList(filename=fq_outfilename,
                            mode='w') as out_table_file:
            out_table_file.extend(in_table_file)
            node_context.output['port0'].encode_path(fq_outfilename)
