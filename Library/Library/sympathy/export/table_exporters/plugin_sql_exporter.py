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
import pyodbc

from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui')

from sylib.export import table as exporttable
from sympathy.api import table
from sympathy.api import node as synode
sql = table.table_sql()


def odbc_module(method_name):
    try:
        if method_name == 'ceODBC':
            import ceODBC
            return ceODBC
        else:
            return pyodbc
    except ImportError as e:
        print('Using default ODBC due to: {}'.format(e))
    return pyodbc


class DataExportSQLWidget(QtGui.QWidget):
    def __init__(self, parameter_root, node_context_input):
        super(DataExportSQLWidget, self).__init__()
        self._parameter_root = parameter_root
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.addWidget(self._parameter_root['odbc'].gui())
        vlayout.addWidget(self._parameter_root['table_name'].gui())
        vlayout.addWidget(self._parameter_root['connection_string'].gui())
        vlayout.addWidget(self._parameter_root['drop_table'].gui())
        vlayout.addWidget(self._parameter_root['use_nvarchar_size'].gui())
        self.setLayout(vlayout)


class DataExportSQL(exporttable.TableDataExporterBase):
    """Exporter for SQL files."""
    EXPORTER_NAME = "SQL"
    FILENAME_EXTENSION = ""

    def __init__(self, custom_parameter_root):
        super(DataExportSQL, self).__init__(custom_parameter_root)
        self._init_parameters()

    def _init_parameters(self):
        if 'table_name' not in self._custom_parameter_root:
            self._custom_parameter_root.set_string(
                'table_name', label='Table name',
                description='The table name used when exporting.')

        if 'connection_string' not in self._custom_parameter_root:
            self._custom_parameter_root.set_string(
                'connection_string', label='Connection string',
                description='String used by pyodbc to make a connection.')

        if 'drop_table' not in self._custom_parameter_root:
            self._custom_parameter_root.set_boolean(
                'drop_table', label='Drop table',
                description='Drop table before adding data.')

        if 'use_nvarchar_size' not in self._custom_parameter_root:
            self._custom_parameter_root.set_boolean(
                'use_nvarchar_size', label='Use nvarchar(size)',
                description='Use nvarchar(size) instead of nvarchar(MAX).')

        if 'odbc' not in self._custom_parameter_root:
            self._custom_parameter_root.set_list(
                'odbc', ['default', 'pyodbc', 'ceODBC'],
                label='ODBC method', order=0,
                description='ODBC method to use.', value=[0],
                editor=synode.Util.combo_editor().value())

    @staticmethod
    def file_based():
        return False

    def parameter_view(self, node_context_input):
        return DataExportSQLWidget(
            self._custom_parameter_root, node_context_input)

    def export_data(self, in_sytable, fq_outfilename, progress=None):
        """Export Table to SQL."""
        table_name = self._custom_parameter_root.value_or_default(
            'table_name', 'test')
        connection_string = self._custom_parameter_root[
            'connection_string'].value
        drop_table = self._custom_parameter_root.value_or_default(
            'drop_table', False)
        use_nvarchar_size = self._custom_parameter_root.value_or_default(
            'use_nvarchar_size', False)
        try:
            odbc_name = self._custom_parameter_root['odbc'].selected
        except KeyError:
            odbc_name = 'odbc'

        odbc = odbc_module(odbc_name)

        sql.table_to_odbc(
            in_sytable, connection_string, table_name,
            drop_table, use_nvarchar_size, odbc=odbc)
