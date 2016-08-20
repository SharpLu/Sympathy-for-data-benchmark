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
In Sympathy for Data, the action of pointing out where data is located and
actual importation of data are separated into two different categories of
nodes. The internal data type Datasource is used to carry the information
about the location of the data to the importation nodes.

There exist two nodes for establishing paths to locations with data, either
you are interested in a single source of data, :ref:`Datasource`, or several
sources, :ref:`Datasources`. The single source can either be a data file or a
location in a data base. While for multiple sources only several data files
are handled.
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import os

import six

from sympathy.api import qt as qt_compat
QtCore = qt_compat.QtCore  # noqa
QtGui = qt_compat.import_module('QtGui')  # noqa

from sympathy.api import node as synode
from sympathy.common import filename_retriever_gui
from sympathy.api import datasource as dsrc
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class SuperNode(object):
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.1'
    icon = 'datasource.svg'
    tags = Tags(Tag.Input.Import)


def resolve_relative_path(path):
    relative_path = ''
    if path:
        try:
            relative_path = os.path.relpath(six.text_type(path))
        except:
            relative_path = os.path.abspath(six.text_type(path))
    return relative_path


class FileDatasourceWidget(QtGui.QWidget):
    def __init__(self, synode_context, parameters, parent=None):
        super(FileDatasourceWidget, self).__init__(parent)
        self._parameters = parameters

        self._init_gui()
        self._init_gui_from_parameters()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)

        file_widget = QtGui.QWidget()
        file_vlayout = QtGui.QVBoxLayout()
        file_widget.setLayout(file_vlayout)

        db_widget = QtGui.QWidget()
        db_vlayout = QtGui.QVBoxLayout()
        db_widget.setLayout(db_vlayout)

        self._filename_widget = self._parameters['filename'].gui()
        self._db_driver_widget = self._parameters['db_driver'].gui()
        self._db_servername_widget = (
            self._parameters['db_servername'].gui())
        self._db_databasename_widget = (
            self._parameters['db_databasename'].gui())
        self._db_user_widget = self._parameters['db_user'].gui()
        self._db_password_widget = self._parameters['db_password'].gui()
        self._connection_widget = (
            self._parameters['db_connection_string'].gui())

        self._datasource_tabwidget = QtGui.QTabWidget()

        file_vlayout.addWidget(self._filename_widget)
        file_vlayout.addStretch()

        db_vlayout.addWidget(self._db_driver_widget)
        db_vlayout.addWidget(self._db_servername_widget)
        db_vlayout.addWidget(self._db_databasename_widget)
        db_vlayout.addWidget(self._db_user_widget)
        db_vlayout.addWidget(self._db_password_widget)
        db_vlayout.addWidget(self._connection_widget)

        self._datasource_tabwidget.addTab(file_widget, 'File')
        self._datasource_tabwidget.addTab(db_widget, 'Database')

        vlayout.addWidget(self._datasource_tabwidget)

        self.setLayout(vlayout)

        self._datasource_tabwidget.currentChanged[int].connect(
            self._tab_changed)

    def _init_gui_from_parameters(self):
        try:
            index = self._parameters['datasource_type'].value[0]
        except KeyError:
            index = 0
        self._datasource_tabwidget.setCurrentIndex(index)

    def _tab_changed(self, index):
        self._parameters['datasource_type'].value = [index]


def datasource_factory(datasource, parameter_root):
    try:
        datasource_type = parameter_root['datasource_type'].selected
    except KeyError:
        datasource_type = 'File'

    if datasource_type == 'File':
        tabledata = datasource.to_file_dict(
            parameter_root['filename'].value)
    elif datasource_type == 'Database':
        tabledata = datasource.to_database_dict(
            parameter_root['db_driver'].selected,
            parameter_root['db_servername'].value,
            parameter_root['db_databasename'].value,
            parameter_root['db_user'].value,
            parameter_root['db_password'].value,
            parameter_root.value_or_empty('db_connection_string'))
    else:
        assert(False)

    return tabledata


class FileDatasource(SuperNode, synode.Node):
    """
    Create Datasource with path to a data source.

    :Outputs:
        **Datasource** : DataSource
            Datasource with path to a data source.
    :Configuration:
        **Select location of data, file or database.**

        - **File**
            **Use relative path**
                Turn on/off relative path towards the location where the
                corresponding workflow is stored in the dictionary tree.
            **Filename**
                Specify filename, togther with path, of data source or select
                by using the button with the three buttons.
        - **Database**
            **Database driver**
                Select database driver.
            **Server name**
                Specify name of server.
            **Database name**
                Specify name of database.
            **User**
                Specify name of user.
            **Password**
                Enter password for specified user.
            **Connection string**
                Enter a connection string.
    :Opposite nodes:
    :Ref. nodes: :ref:`Datasources`
    """

    name = 'Datasource'
    description = 'Select a data source.'
    nodeid = 'org.sysess.sympathy.datasources.filedatasource'

    outputs = Ports([Port.Datasource(
        'Datasource', name='port1', scheme='text')])

    parameters = synode.parameters()
    parameters.set_string(
        'filename', label='Filename',
        description='A filename including path if needed',
        editor=synode.Util.filename_editor(['Any files (*)']).value())
    parameters.set_list(
        'db_driver', ['SQL Server'], label='Database driver',
        description='Database driver to use.',
        editor=synode.Util.combo_editor().value())
    parameters.set_string(
        'db_servername', label='Server name',
        description='A valid name to a database server.')
    parameters.set_string(
        'db_databasename', label='Database name',
        description='The name of the database.')
    parameters.set_string(
        'db_user', label='User',
        description='A valid database user.')
    parameters.set_string(
        'db_password', label='Password',
        description='A valid password for the selected user.')
    parameters.set_string(
        'db_connection_string', label='Connection string',
        description='A connection string that will override other settings.')

    parameters.set_list(
        'datasource_type', ['File', 'Database'], label='Datasource type',
        description='Type of datasource.')

    INTERACTIVE_NODE_ARGUMENTS = {
        'uri': ['filename', 'value']
    }

    def exec_parameter_view(self, synode_context):
        return FileDatasourceWidget(
            synode_context, synode_context.parameters)

    def verify_parameters(self, synode_context):
        """Verify parameters"""
        parameters_ok = True
        if synode_context.parameters['datasource_type'].selected == 'File':
            parameters_ok &= os.path.isfile(
                synode_context.parameters['filename'].value)
        return parameters_ok

    def execute(self, synode_context):
        """Execute"""
        synode_context.output['port1'].encode(
            datasource_factory(synode_context.output['port1'],
                               synode_context.parameters))


class FileDatasourcesWidget(QtGui.QWidget):
    def __init__(self, synode_context, parameter_root, parent=None):
        super(FileDatasourcesWidget, self).__init__(parent)
        self._parameter_root = parameter_root

        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)

        use_recursive_widget = self._parameter_root['recursive'].gui()
        self._directory_widget = self._parameter_root['directory'].gui()
        search_pattern_widget = self._parameter_root['search_pattern'].gui()
        self._file_widget = QtGui.QListWidget()
        self._file_widget.setAlternatingRowColors(True)
        self._file_widget.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        _file_widget_label = QtGui.QLabel(u'Preview')

        vlayout.addWidget(use_recursive_widget)
        vlayout.addWidget(self._directory_widget)
        vlayout.addWidget(search_pattern_widget)
        vlayout.addWidget(_file_widget_label)
        vlayout.addWidget(self._file_widget)
        self.setLayout(vlayout)

        self._update_filewidget()

        use_recursive_widget.stateChanged.connect(
            self._update_filewidget)
        self._directory_widget.editor().state_changed[bool].connect(
            self._update_filewidget)
        self._directory_widget.valueChanged.connect(
            self._update_filewidget)
        search_pattern_widget.valueChanged.connect(
            self._update_filewidget)

    def _update_filewidget(self):
        filename_retriever = filename_retriever_gui.FilenameRetriever(
            self._parameter_root['directory'].value,
            self._parameter_root['search_pattern'].value)

        selected_fq_filenames = filename_retriever.filenames(
            fully_qualified=True,
            recursive=self._parameter_root['recursive'].value, max_length=20)
        self._file_widget.clear()
        self._file_widget.addItems(selected_fq_filenames)


class FileDatasourceMultiple(SuperNode, synode.Node):
    """
    Create Datasources with paths to data sources.

    :Outputs:
        **Datasource** : DataSources
            Datasources with paths to data sources.
    :Configuration:
        **Recursive**
            Turn on/off recursive folder search for filenames satisfying
            the specified pattern beneath selected directory in the directory
            tree.
        **Use relative path**
            Turn on/off relative path towards the location where the
            corresponding workflow is stored in the dictionary tree.
        **Directory**
            Specify dictionary in dictionary tree where to search for files
            with the specified pattern or select by using the button with the
            three buttons.
        **Search pattern**
            Specify the wildcard/regexp pattern to match files.
    :Opposite nodes:
    :Ref. nodes: :ref:`Datasource`
    """

    name = 'Datasources'
    description = 'Select data sources.'
    nodeid = 'org.sysess.sympathy.datasources.filedatasourcemultiple'

    outputs = Ports([Port.Datasources(
        'DataSource', name='port1', scheme='text')])

    parameters = synode.parameters()
    parameters.set_boolean(
        'recursive', value=False, label='Recursive',
        description='Find files in all subfolders.')
    parameters.set_string(
        'directory', label='Directory',
        description='The base directory.',
        editor=synode.Util.directory_editor().value())
    parameters.set_string(
        'search_pattern', value='*', label='Search pattern',
        description='A wildcard/regexp pattern to match files.')

    def exec_parameter_view(self, synode_context):
        return FileDatasourcesWidget(synode_context, synode_context.parameters)

    def execute(self, synode_context):
        """Create a list of datasources and add them to the output
        file.
        """
        filename_retriever = filename_retriever_gui.FilenameRetriever(
            synode_context.parameters['directory'].value,
            synode_context.parameters['search_pattern'].value)

        selected_fq_filenames = filename_retriever.filenames(
            fully_qualified=True,
            recursive=synode_context.parameters['recursive'].value)

        for fq_filename in selected_fq_filenames:
            datasource = dsrc.File()
            datasource.encode_path(fq_filename)
            synode_context.output['port1'].append(datasource)
