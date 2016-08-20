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
ADAF is an internal data type in Sympathy for Data. In the ADAF different
kind of data, metadata (data about data), results (aggregated/calculated data)
and timeseries (accumulated time-resolved data), connected to a simultaneous
event can be stored together with defined connections to each other.

The different kinds of data are separated into containers. For the metadata
and the results, the containers consist of a set of signals stored as a
:ref:`Table`.

For the time-resolved data, the container has a more advanced structure.
The time-resolved data from a measurement can have been collected from
different measurement system and the data can, because of different reason,
not be stored together. For example, the two systems do not using the same
sample rate or do not have a common absolute zero time. The timeseries
container in the ADAF can therefore include one or many system containers.
Even within a measurement system, data can have been measured with different
sample rates, therefore the system container can consist of one or many
rasters. Each raster consists of a time base and a set of corresponding
signals, which all are stored as the internal :ref:`Table` type.

The importation into ADAFs are based on plugins, where each supported
file format has its own plugin. The plugins have their own configurations
which are reached by choosing among the tabs in the configuration GUI. The
documentation for each plugin is obtained by clicking at listed file formats
below.

The node has an auto configuration which uses a validity check in the plugins
to detect and choose the proper plugin for the considered datasource. When
the node is executed in the auto mode the default settings for the plugins
will be used.

Existing file formats plugins:
    - ADAF
    - ATF
    - DIVA
    - LAA
    - MDF
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)
import os
import traceback
from collections import OrderedDict

from sympathy.api import node as synode
from sympathy.api import adaf
from sympathy.api import datasource as dsrc
from sympathy.api import importers
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyDataError, NoDataError


FAILURE_STRATEGIES = OrderedDict(
    [('Exception', 0), ('Create Empty Entry', 1)])

LIST_FAILURE_STRATEGIES = OrderedDict(
    [('Exception', 0), ('Create Empty Entry', 1), ('Skip File', 2)])


def import_adaf_data(importer_class, datasource, output,
                     parameters, manage_input, progress):
    """Function to handle the special case when importing an ADAF file
    due to the way they are opened.
    """
    dspath = datasource.decode_path()
    importer = importer_class(dspath, parameters)

    if importer.is_adaf():
        # This is a special case where the ADAF file should be
        # copied into the platform.

        try:
            # Got plugin adaf importer.
            import_links = importer.import_links
        except AttributeError:
            import_links = False

        in_datafile = adaf.File(filename=dspath, mode='r',
                                import_links=import_links)
        output.source(in_datafile)
        manage_input(dspath, in_datafile)
    else:
        importer.import_data(output, parameters, progress=progress)


class SuperNode(object):
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'import_adaf.svg'
    tags = Tags(Tag.Input.Import)

    @staticmethod
    def parameters_base():
        parameters = synode.parameters()
        parameters.set_string('active_importer', value='Auto')
        custom_importer_group = parameters.create_group(
            'custom_importer_data')
        custom_importer_group.create_group('Auto')
        return parameters


class ImportADAF(SuperNode, synode.Node):
    """
    Import datasource as ADAF.

    :Inputs:
        **Inport** : DataSource
            Path to datasource.
    :Outputs:
        **Outport** : ADAF
            ADAF with imported data.
    :Configuration: See description for specific plugin
    :Opposite node:
    :Ref. nodes: :ref:`ADAFs`
    """

    name = 'ADAF'
    description = 'Data source as ADAF'
    nodeid = 'org.sysess.sympathy.data.adaf.importadaf'
    inputs = Ports([Port.Datasource('Datasource')])
    outputs = Ports([Port.ADAF('Imported ADAF')])

    parameters = SuperNode.parameters_base()
    parameters.set_list(
        'fail_strategy', label='Action on import failure',
        list=FAILURE_STRATEGIES.keys(), value=[0],
        descripton='Decide how failure to import a file should be handled.',
        editor=synode.Util.combo_editor().value())

    def exec_parameter_view(self, node_context):
        dspath = None
        try:
            datasource = node_context.input.first
            dspath = datasource.decode_path()

            if dspath is not None and not os.path.isfile(dspath):
                raise SyDataError("File does not exist: {}".format(dspath))
        except NoDataError:
            # This is if no input is connected.
            pass
        widget = importers.base.ImporterConfigurationWidget(
            importers.utils.available_adaf_importers(),
            synode.parameters(node_context.parameters), dspath)
        return widget

    def execute(self, node_context):
        params = synode.parameters(node_context.parameters)
        importer_type = params['active_importer'].value
        if 'fail_strategy' in params:
            fail_strategy = params['fail_strategy'].value[0]
        else:
            fail_strategy = 0

        try:
            datasource = node_context.input.first
            importer_class = (
                importers.utils.adaf_importer_from_datasource_factory(
                    datasource, importer_type))

            if importer_class is None:
                raise SyDataError(
                    "No importer could automatically be found for this file.")
            import_adaf_data(
                importer_class, datasource, node_context.output.first,
                params["custom_importer_data"][importer_type],
                node_context.manage_input,
                progress=self.set_progress)
        except Exception:
            if fail_strategy == FAILURE_STRATEGIES['Create Empty Entry']:
                pass
            else:
                raise

        self.set_progress(100)


class ImportADAFs(SuperNode, synode.Node):
    """
    Import file(s) into the platform as ADAF(s).

    :Inputs:
        **Inport** : DataSources
            Paths to datasources.
    :Outputs:
        **Outport** : ADAFs
            ADAFs with imported data.
    :Configuration: See description for specific plugin
    :Opposite node: :ref:`Export ADAFs`
    :Ref. nodes: :ref:`ADAF`
    """

    name = 'ADAFs'
    description = 'Import multiple adaf files'
    nodeid = 'org.sysess.sympathy.data.adaf.importadafs'

    inputs = Ports([
        Port.Datasources('Datasources', name='bob', requiresdata=True)])
    outputs = Ports([Port.ADAFs('Imported ADAFs')])

    parameters = SuperNode.parameters_base()
    parameters.set_list(
        'fail_strategy', label='Action on import failure',
        list=LIST_FAILURE_STRATEGIES.keys(), value=[0],
        descripton='Decide how failure to import a file should be handled.',
        editor=synode.Util.combo_editor().value())

    def __init__(self):
        super(ImportADAFs, self).__init__()

    def exec_parameter_view(self, node_context):
        dspath = None
        try:
            try:
                datasource = node_context.input.first[0]
            except IndexError:
                datasource = dsrc.File()
            dspath = datasource.decode_path()
        except NoDataError:
            # This is if no input is connected.
            pass

        widget = importers.base.ImporterConfigurationWidget(
            importers.utils.available_adaf_importers(),
            node_context.parameters, dspath)
        return widget

    def execute(self, node_context):
        """Import file(s) into platform as a ADAF(s)."""
        params = node_context.parameters
        importer_type = params['active_importer'].value
        if 'fail_strategy' in params:
            fail_strategy = params['fail_strategy'].value[0]
        else:
            fail_strategy = 0

        input_list = node_context.input.first
        len_input_list = len(input_list)
        output_list = node_context.output.first
        for i, datasource in enumerate(input_list):
            out_file = None
            try:
                importer_class = (
                    importers.utils.adaf_importer_from_datasource_factory(
                        datasource, importer_type))
                if importer_class is None:
                    raise SyDataError(
                        "No importer could automatically be found for "
                        "this file.")
                dspath = datasource.decode_path()
                adaf_importer = importer_class(
                    dspath,
                    params['custom_importer_data'][importer_type])

                if adaf_importer.is_adaf():
                    try:
                        # Got plugin adaf importer.
                        import_links = adaf_importer.import_links
                    except AttributeError:
                        import_links = False

                    ds_infile = adaf.File(
                        filename=dspath, mode='r',
                        import_links=import_links)
                    output_list.append(ds_infile)
                    node_context.manage_input(dspath, ds_infile)
                else:
                    outputfile = adaf.File()
                    adaf_importer.import_data(
                        outputfile,
                        params['custom_importer_data'][importer_type],
                        progress=lambda x: self.set_progress(
                            (100 * i + x) / len_input_list))
                    output_list.append(outputfile)
            except Exception as e:
                if fail_strategy == LIST_FAILURE_STRATEGIES['Exception']:
                    traceback.print_exc()
                    raise e
                elif fail_strategy == LIST_FAILURE_STRATEGIES[
                        'Create Empty Entry']:
                    print('Creating empty output file (index {}).'.format(i))
                    out_file = adaf.File()
                else:
                    print('Skipping file (index {}).'.format(i))
                    out_file = None

            if out_file is not None:
                output_list.append(out_file)
            self.set_progress(100 * (1 + i) / len_input_list)
