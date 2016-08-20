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
Table is the internal data type in Sympathy for Data representing a
two-dimensional data set. A Table consists of an arbitrary number of
columns, where all columns have the equal number of elements. Each column
has an unique header and a defined data type - all elements in a column
are of the same data type. In a Table, the columns are not bound to have
same data type, columns with different data types can be mixed in a Table.
The supported data types for the columns are the same as for numpy arrays,
with exception for the object type, np.object. Optional, an column can also
be given additional attributes, like unit or description.

The importation into Tables are based on plugins, where each supported
file format has its own plugin. The plugins have their own configurations
which are reached by choosing among the tabs in the configuration GUI. The
documentation for each plugin is obtained by clicking at the listed file
formats below.

The node has an auto configuration which uses a validy check in the plugins
to detect and choose the proper plugin for the considered datasource. When
the node is executed in the auto mode the default settings for the plugins
will be used.

Existing file formats plugins:
    - CSV
    - HDF5
    - SQL
    - Table
    - XLS
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)
import os
from collections import OrderedDict

from sympathy.api import importers
from sympathy.api import datasource as dsrc
from sympathy.api import table
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyDataError, NoDataError
from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui')


FAILURE_STRATEGIES = OrderedDict(
    [('Exception', 0), ('Create Empty Entry', 1)])

LIST_FAILURE_STRATEGIES = OrderedDict(
    [('Exception', 0), ('Create Empty Entry', 1), ('Skip File', 2)])


def import_table_data(table_importer, datasource, output_sytype,
                      parameters, manage_input):
    """Function to handle the special case when importing an Table file
    due to the way they are opened.
    """
    dspath = datasource.decode_path()
    importer = table_importer(dspath, parameters)
    if importer.is_table():
        # This is a special case where the Table file should be
        # copied into the platform.
        in_datafile = table.File(filename=dspath, mode='r')
        output_sytype.source(in_datafile)
        manage_input(dspath, in_datafile)
    else:
        importer.import_data(output_sytype, parameters)
        if not output_sytype.get_name():
            output_sytype.set_name(os.path.splitext(
                os.path.basename(dspath))[0])


class SuperNode(object):
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    icon = 'import_table.svg'
    tags = Tags(Tag.Input.Import)

    @staticmethod
    def parameters_base():
        parameters = synode.parameters()
        parameters.set_string('active_importer', value='Auto')
        custom_importer_group = parameters.create_group(
            'custom_importer_data')
        custom_importer_group.create_group('Auto')
        return parameters


class ImportTable(SuperNode, synode.Node):
    """
    Import Datasource as Table.

    :Inputs:
        **port1** : Datasource
            Path to datasource.
    :Outputs:
        **port1** : Table
            Table with imported data.
    :Configuration: See description for specific plugin
    :Opposite node: :ref:`Export Tables`
    :Ref. nodes: :ref:`Table`
    """

    name = 'Table'
    description = 'Data source as a table'
    nodeid = 'org.sysess.sympathy.data.table.importtable'

    inputs = Ports([Port.Datasource(
        'Datasource', name='port1', requiresdata=True, scheme='text')])
    outputs = Ports([Port.Table('Imported Table', name='port1')])

    parameters = SuperNode.parameters_base()
    parameters.set_list(
        'fail_strategy', label='Action on import failure',
        list=FAILURE_STRATEGIES.keys(), value=[0],
        descripton='Decide how failure to import a file should be handled.',
        editor=synode.Util.combo_editor().value())

    def exec_parameter_view(self, node_context):
        dspath = None
        datasource_type = None
        try:
            datasource = node_context.input['port1']
            dspath = datasource.decode_path()
            datasource_type_text = datasource.decode_type()
            if dspath is not None:
                datasource_type = getattr(
                    importers.base.DATASOURCE, datasource_type_text)
        except NoDataError:
            # This is if no input is connected.
            pass

        available_importers = importers.utils.available_table_importers(
            datasource_type)

        widget = importers.base.ImporterConfigurationWidget(
            available_importers, node_context.parameters,
            dspath)
        return widget

    def execute(self, node_context):
        """Import file into platform as a table."""
        parameter_root = node_context.parameters
        importer_type = parameter_root['active_importer'].value
        try:
            if 'fail_strategy' in parameter_root:
                fail_strategy = parameter_root['fail_strategy'].selected
            else:
                fail_strategy = 0

            datasource = node_context.input['port1']
            table_importer = (
                importers.utils.table_importer_from_datasource_factory(
                    datasource, importer_type))
            if table_importer is None:
                raise SyDataError(
                    "No importer could automatically be found for this file.")
            import_table_data(
                table_importer, datasource, node_context.output['port1'],
                parameter_root["custom_importer_data"][importer_type],
                node_context.manage_input)

        except Exception:
            if fail_strategy == FAILURE_STRATEGIES['Create Empty Entry']:
                pass
            else:
                raise


class ImportTables(SuperNode, synode.Node):
    """
    Import Datasources as Tables.

    :Inputs:
        **port1** : Datasources
            Paths to datasources.
    :Outputs:
        **port1** : Tables
            Tables with imported data.
    :Configuration: See description for specific plugin
    :Opposite node: :ref:`Export Tables`
    :Ref. nodes: :ref:`Table`
    """

    name = 'Tables'
    description = 'Import datasources as Tables.'
    nodeid = 'org.sysess.sympathy.data.table.importtablemultiple'

    inputs = Ports([Port.Datasources(
        'Datasource', name='port1', requiresdata=True, scheme='text')])
    outputs = Ports([Port.Tables('Imported Tables', name='port1')])

    parameters = SuperNode.parameters_base()
    parameters.set_list(
        'fail_strategy', label='Action on import failure',
        list=LIST_FAILURE_STRATEGIES.keys(), value=[0],
        descripton='Decide how failure to import a file should be handled.',
        editor=synode.Util.combo_editor().value())

    def exec_parameter_view(self, node_context):
        dspath = None
        try:
            try:
                datasource = node_context.input['port1'][0]
            except IndexError:
                datasource = dsrc.File()
            dspath = datasource.decode_path()
        except NoDataError:
            # This is if no input is connected.
            pass
        widget = importers.base.ImporterConfigurationWidget(
            importers.utils.available_table_importers(),
            node_context.parameters, dspath)
        return widget

    def execute(self, node_context):
        """Import file(s) into platform as Table(s)."""
        params = node_context.parameters
        importer_type = params['active_importer'].value
        parameter_root = params
        input_list = node_context.input['port1']
        output_list = node_context.output['port1']
        objects = input_list
        number_of_objects = len(objects)

        if 'fail_strategy' in params:
            fail_strategy = parameter_root['fail_strategy'].value[0]
        else:
            fail_strategy = 0

        for object_no, datasource in enumerate(objects):
            out_file = None

            try:
                table_importer_class = (
                    importers.utils.table_importer_from_datasource_factory(
                        datasource, importer_type))
                if table_importer_class is None:
                    raise SyDataError(
                        "No importer could automatically be found for "
                        "this file.")
                dspath = datasource.decode_path()
                table_importer = table_importer_class(
                    dspath, params["custom_importer_data"][importer_type])
                if table_importer.is_table():
                    ds_infile = table.File(filename=dspath, mode='r')
                    output_list.append(ds_infile)
                    node_context.manage_input(dspath, ds_infile)
                else:
                    outputfile = table.File()
                    table_importer.import_data(
                        outputfile,
                        params["custom_importer_data"][importer_type])
                    if not outputfile.get_name():
                        outputfile.set_name(os.path.splitext(
                            os.path.basename(dspath))[0])
                    output_list.append(outputfile)
            except Exception:
                if fail_strategy == LIST_FAILURE_STRATEGIES['Exception']:
                    raise
                elif fail_strategy == LIST_FAILURE_STRATEGIES[
                        'Create Empty Entry']:
                    out_file = table.File()
                else:
                    print('Skipping file')
                    out_file = None

            if out_file is not None:
                output_list.append(out_file)
            self.set_progress(100.0 * (1 + object_no) / number_of_objects)


class ImportRAWTables(synode.Node):
    """
    Import Tables from a single HDF5-file.

    :Inputs:
        **port1** : DataSource
            Datasource with a filepath to a HDF5-file.
    :Outputs:
        **port1** : Tables
            Tables with data from HDF5-file.
    :Configuration: No configuration.
    :Opposite node:
    :Ref. nodes: :ref:`ADAFs`
    """

    name = 'RAW Tables'
    description = 'Import RAW Tables'
    nodeid = 'org.sysess.sympathy.data.table.importrawtables'
    icon = 'import_table.svg'
    tags = Tags(Tag.Input.Import)

    inputs = Ports([Port.Datasource(
        'Datasource', name='port1', requiresdata=True, scheme='text')])
    outputs = Ports([Port.Tables('Imported Table', name='port1')])

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'

    def execute(self, node_context):
        dspath = node_context.input['port1'].decode_path()
        out_tables = node_context.output['port1']
        in_tables = table.FileList(filename=dspath, mode='r')
        node_context.manage_input(dspath, in_tables)
        in_tables.set_read_through()
        out_tables.extend(in_tables)
        self.set_progress(100)
