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
Created on Mon Nov 05 08:23:41 2012

@author: Helena
"""
import pyodbc
import re
import os

from sympathy.api import qt as qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module('QtGui')

from sympathy.api import importers
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


def get_table_names(datasource, filedbs):
    if datasource == importers.base.DATASOURCE.FILE:
        return filedbs[0].table_names()
    elif datasource == importers.base.DATASOURCE.DATABASE:
        return []
    else:
        raise NotImplementedError('Datasource not implemented.')


def get_filedbs(fq_filename):
    fq_filename = os.path.abspath(fq_filename)

    return [filedb for filedb in [sql.MDBDatabase(fq_filename),
                                  sql.SQLite3Database(fq_filename)]
            if filedb.is_valid()]


class DataImportSQLWidget(QtGui.QWidget):
    def __init__(self, parameters, fq_infilename, datasource):
        super(DataImportSQLWidget, self).__init__()
        self._parameters = parameters
        self._fq_infilename = fq_infilename
        self._datasource = datasource
        self._filedbs = []

        if fq_infilename is not None:
            self._filedbs = get_filedbs(fq_infilename)

        self._init_parameters()
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        hlayout_simple_table = QtGui.QHBoxLayout()
        hlayout_query_edit = QtGui.QHBoxLayout()
        hlayout_join_info = QtGui.QHBoxLayout()
        hlayout_where = QtGui.QHBoxLayout()
        max_height = 150

        vlayout.addWidget(self._parameters['odbc'].gui())
        # Create ButtonGroup
        self._sqlite_query_alternatives = QtGui.QButtonGroup()
        self._sqlite_query_alternatives.setExclusive(True)

        self._table_query_button = QtGui.QRadioButton('Table query')
        self._table_query_button.setChecked(True)
        self._lineedit_query_button = QtGui.QRadioButton('Write query')
        self._custom_query_button = QtGui.QRadioButton('Make custom query')
        # Add buttons to group
        self._sqlite_query_alternatives.addButton(self._table_query_button)
        self._sqlite_query_alternatives.addButton(self._lineedit_query_button)
        self._sqlite_query_alternatives.addButton(self._custom_query_button)
        # Add group to layout
        vlayout.addWidget(self._table_query_button)

        self._row_label = QtGui.QLabel("Choose database table.")
        self._row_combo = QtGui.QComboBox()
        hlayout_simple_table.addWidget(self._row_label)
        hlayout_simple_table.addWidget(self._row_combo)
        vlayout.addLayout(hlayout_simple_table)
        vlayout.addWidget(self._lineedit_query_button)
        self._query_label = QtGui.QLabel("SQLite query:")
        self._query_edit = QtGui.QLineEdit(self)
        hlayout_query_edit.addWidget(self._query_label)
        hlayout_query_edit.addWidget(self._query_edit)
        vlayout.addLayout(hlayout_query_edit)
        vlayout.addWidget(self._custom_query_button)
        self._join_tables = QtGui.QListWidget()
        self._join_tables.setSelectionMode(
            QtGui.QAbstractItemView.MultiSelection)
        self._join_tables.setMaximumHeight(max_height)
        self._join_tables.addItems(get_table_names(self._datasource,
                                                   self._filedbs))
        self._table_columns = QtGui.QListWidget()
        self._table_columns.setSelectionMode(
            QtGui.QAbstractItemView.MultiSelection)
        self._table_columns.setMaximumHeight(max_height)
        self._label_join_tables = QtGui.QLabel("Select tables")
        vlayout_join_tables = QtGui.QVBoxLayout()
        vlayout_join_tables.addWidget(self._label_join_tables)
        vlayout_join_tables.addWidget(self._join_tables)
        hlayout_join_info.addLayout(vlayout_join_tables)
        self._label_table_columns = QtGui.QLabel(
            "Select resulting table columns")
        vlayout_table_columns = QtGui.QVBoxLayout()
        vlayout_table_columns.addWidget(self._label_table_columns)
        vlayout_table_columns.addWidget(self._table_columns)
        hlayout_join_info.addLayout(vlayout_table_columns)

        self._join_column_selection = QtGui.QListWidget()
        self._join_column_selection.setDragEnabled(True)
        self._join_column_selection.setMaximumHeight(max_height)
        self._label_join_column_selection = QtGui.QLabel(
            "Double click on names to add to join")
        vlayout_join_column_selection = QtGui.QVBoxLayout()
        vlayout_join_column_selection.addWidget(
            self._label_join_column_selection)
        vlayout_join_column_selection.addWidget(self._join_column_selection)
        hlayout_join_info.addLayout(vlayout_join_column_selection)

        hlayout_where_preview = QtGui.QHBoxLayout()
        self._join_columns = QtGui.QListWidget()
        # Added for double click method
        self._join_columns.setDragDropMode(
            QtGui.QAbstractItemView.InternalMove)
        self._join_columns.setAcceptDrops(True)
        self._join_columns.setDropIndicatorShown(True)
        self._join_columns.setMaximumHeight(max_height)
        self._label_join_columns = QtGui.QLabel(
            "Join on two consecutive column names. Double click to remove."
            "Change order by drag and drop.")
        self._label_join_columns.setWordWrap(True)
        vlayout_join_columns = QtGui.QVBoxLayout()
        vlayout_join_columns.addWidget(
            self._label_join_columns)
        vlayout_join_columns.addWidget(self._join_columns)
        hlayout_join_info.addLayout(vlayout_join_columns)

        # For adding where statements
        hlayout_where_combo = QtGui.QHBoxLayout()
        self._where_column_combo = QtGui.QComboBox()
        hlayout_where_combo.addWidget(self._where_column_combo)
        self._where_comparison = QtGui.QComboBox()
        hlayout_where.addWidget(self._where_comparison)
        self._where_condition = QtGui.QLineEdit()
        hlayout_where.addWidget(self._where_condition)
        self._where_add_button = QtGui.QPushButton('Add', self)
        hlayout_where.addWidget(self._where_add_button)
        self._where_condition_list = QtGui.QListWidget()
        self._where_condition_list.setDragDropMode(
            QtGui.QAbstractItemView.InternalMove)
        self._where_condition_list.setAcceptDrops(True)
        self._where_condition_list.setDropIndicatorShown(True)
        self._where_condition_list.setMaximumHeight(max_height)
        self._label_where_condition = QtGui.QLabel(
            "Add WHERE statements")
        self._label_where_condition.setWordWrap(True)
        vlayout_where_condition = QtGui.QVBoxLayout()
        vlayout_where_condition.addWidget(
            self._label_where_condition)
        vlayout_where_condition.addLayout(hlayout_where_combo)
        vlayout_where_condition.addLayout(hlayout_where)
        vlayout_where_condition.addWidget(self._where_condition_list)
        hlayout_where_preview.addLayout(vlayout_where_condition)

        # Preview buttons, tables and label created.
        self._preview_query_button = QtGui.QPushButton('Preview query')
        self._preview_query_button.setFixedWidth(150)
        self._preview_query = QtGui.QLabel('Query')
        self._preview_query.setWordWrap(True)
        hlayout_query_preview = QtGui.QHBoxLayout()
        hlayout_query_preview.addWidget(self._preview_query_button)
        hlayout_query_preview.addWidget(self._preview_query)

        self._preview_table_button = QtGui.QPushButton('Preview table')
        self._preview_table = QtGui.QTableWidget()
        self._preview_table.setMaximumHeight(max_height)
        vlayout_table_preview = QtGui.QVBoxLayout()
        vlayout_table_preview.addWidget(self._preview_table_button)
        vlayout_table_preview.addWidget(self._preview_table)

        hlayout_where_preview.addLayout(vlayout_table_preview)

        vlayout.addLayout(hlayout_join_info)
        vlayout.addLayout(hlayout_where_preview)
        vlayout.addLayout(hlayout_query_preview)
        self.setLayout(vlayout)

        self._row_combo.addItems(self._parameters["table_names"].list)
        self._row_combo.setCurrentIndex(self._parameters
                                        ["table_names"].value[0])
        self._query_edit.setText(self._parameters["query_str"].value)

        self._table_query_button.setChecked(
            self._parameters["table_query"].value)
        self._table_query_enable(self._parameters["table_query"].value)
        self._lineedit_query_button.setChecked(
            self._parameters["lineedit_query"].value)
        self._lineedit_query_enable(self._parameters["lineedit_query"].value)
        self._custom_query_button.setChecked(
            self._parameters["custom_query"].value)
        self._custom_query_enable(self._parameters["custom_query"].value)

        for item in self._parameters["join_tables"].list:
            self._join_tables.findItems(
                item, QtCore.Qt.MatchCaseSensitive)[0].setSelected(True)

        # Add column names and mark previous selected ones as selected
        self._names_changed()

        for item in self._parameters["table_columns"].list:
            self._table_columns.findItems(
                item, QtCore.Qt.MatchCaseSensitive)[0].setSelected(True)

        for item in self._parameters["join_column_selection"].list:
            self._join_column_selection.findItems(
                item, QtCore.Qt.MatchCaseSensitive)[0].setSelected(True)

        # Init where combos
        self._where_column_combo.clear()
        self._where_column_combo.addItems(
            self._parameters["where_column_combo"].list)
        self._where_column_combo.setCurrentIndex(
            self._parameters["where_column_combo"].value[0])
        self._where_comparison.addItems(
            self._parameters["where_comparison_combo"].list)
        self._where_comparison.setCurrentIndex(
            self._parameters["where_comparison_combo"].value[0])
        self._where_condition.setText(
            self._parameters["where_condition"].value)
        self._where_condition_list.clear()
        self._where_condition_list.addItems(
            self._parameters["where_condition_list"].list)

        self._row_combo.currentIndexChanged[int].connect(self._row_changed)
        self._query_edit.textChanged[str].connect(self._query_changed)

        self._join_tables.itemClicked.connect(self._names_changed)
        self._table_columns.itemClicked.connect(self._columns_changed)
        self._join_tables.itemSelectionChanged.connect(self._names_changed)
        self._table_columns.itemSelectionChanged.connect(
            self._columns_changed)

        # For double click method
        self._join_column_selection.itemDoubleClicked.connect(
            self._add_double_click)
        self._join_columns.itemDoubleClicked.connect(self._remove_double_click)
        self._join_columns.itemClicked.connect(self._change_order)
        self._join_columns.currentRowChanged.connect(self._change_order)

        self._where_condition_list.itemDoubleClicked.connect(
            self._remove_where_condition)
        self._where_condition_list.currentRowChanged.connect(
            self._change_order_where)

        # For where combo boxes changed
        (self._where_column_combo.currentIndexChanged[int].
            connect(self._where_column_changed))
        (self._where_comparison.currentIndexChanged[int].
            connect(self._where_comparison_changed))
        (self._where_condition.textChanged[str].
            connect(self._where_condition_changed))
        # Button clicked, add where statement
        self._where_add_button.clicked.connect(self._add_where_clause)

        # Preview buttons clicked:
        self._preview_table_button.clicked.connect(self._add_preview_table)
        self._preview_query_button.clicked.connect(self._add_preview_query)

        # query selection radiobuttons clicked
        self._table_query_button.clicked.connect(
            self._table_query_button_clicked)

        self._lineedit_query_button.clicked.connect(
            self._lineedit_query_button_clicked)

        self._custom_query_button.clicked.connect(
            self._custom_query_button_clicked)

    def _init_parameters(self):

        try:
            self._parameters["table_query"]
        except KeyError:
            self._parameters.set_boolean("table_query", value=True)
        try:
            self._parameters["table_names"]
        except KeyError:
            self._parameters.set_list(
                "table_names",
                get_table_names(self._datasource, self._filedbs),
                value=[0])
        try:
            self._parameters["query_str"]
        except KeyError:
            self._parameters.set_string("query_str")
        try:
            self._parameters["lineedit_query"]
        except KeyError:
            self._parameters.set_boolean("lineedit_query", value=False)
        try:
            self._parameters["custom_query"]
        except KeyError:
            self._parameters.set_boolean("custom_query", value=False)
        try:
            self._parameters["join_tables"]
        except KeyError:
            self._parameters.set_list("join_tables")
        try:
            self._parameters["table_columns"]
        except KeyError:
            self._parameters.set_list("table_columns")
        try:
            self._parameters["join_column_selection"]
        except KeyError:
            self._parameters.set_list("join_column_selection")
        try:
            self._parameters["join_columns"]
        except KeyError:
            self._parameters.set_list("join_columns")
        try:
            self._parameters["where_add_comparison"]
        except KeyError:
            self._parameters.set_string("where_add_comparison")
        try:
            self._parameters["where_column_combo"]
        except KeyError:
            self._parameters.set_list("where_column_combo",
                                      self._parameters['join_column_selection']
                                      .list)
        try:
            self._parameters["where_comparison_combo"]
        except KeyError:
            self._parameters.set_list("where_comparison_combo",
                                      ['=', '<', '>', '>=', '<=', '!=',
                                       ' LIKE ', ' GLOB ', ' BETWEEN '])
        try:
            self._parameters["where_condition"]
        except KeyError:
            self._parameters.set_string("where_condition")
        try:
            self._parameters["where_condition_list"]
        except KeyError:
            self._parameters.set_list("where_condition_list")
        try:
            self._parameters["preview_query"]
        except KeyError:
            self._parameters.set_string("preview_query")
        try:
            self._parameters['odbc']
        except KeyError:
            self._parameters.set_list(
                'odbc', ['default', 'pyodbc', 'ceODBC'],
                label='ODBC method', order=0,
                description='ODBC method to use.', value=[0],
                editor=synode.Util.combo_editor().value())

    def _row_changed(self, index):
        self._parameters["table_names"].value = [index]

    def _table_query_button_clicked(self):
        self._parameters["table_query"].value = True
        self._parameters["lineedit_query"].value = False
        self._parameters["custom_query"].value = False
        self._table_query_enable(True)
        self._lineedit_query_enable(False)
        self._custom_query_enable(False)

    def _lineedit_query_button_clicked(self):
        self._parameters["table_query"].value = False
        self._parameters["lineedit_query"].value = True
        self._parameters["custom_query"].value = False
        self._table_query_enable(False)
        self._lineedit_query_enable(True)
        self._custom_query_enable(False)

    def _custom_query_button_clicked(self):
        self._parameters["table_query"].value = False
        self._parameters["lineedit_query"].value = False
        self._parameters["custom_query"].value = True
        self._table_query_enable(False)
        self._lineedit_query_enable(False)
        self._custom_query_enable(True)

    def _table_query_enable(self, state):
        self._row_combo.setEnabled(state)
        self._row_label.setEnabled(state)

    def _lineedit_query_enable(self, state):
        self._query_edit.setEnabled(state)
        self._query_label.setEnabled(state)

    def _custom_query_enable(self, state):
        self._join_tables.setEnabled(state)
        self._label_join_tables.setEnabled(state)
        self._table_columns.setEnabled(state)
        self._label_table_columns.setEnabled(state)
        self._join_column_selection.setEnabled(state)
        self._label_join_column_selection.setEnabled(state)
        self._join_columns.setEnabled(state)
        self._label_join_columns.setEnabled(state)
        self._label_where_condition.setEnabled(state)
        self._where_column_combo.setEnabled(state)
        self._where_comparison.setEnabled(state)
        self._where_condition.setEnabled(state)
        self._where_add_button.setEnabled(state)
        self._where_condition_list.setEnabled(state)
        self._preview_query.setEnabled(state)
        self._preview_query_button.setEnabled(state)
        self._preview_table.setEnabled(state)
        self._preview_table_button.setEnabled(state)

    def _query_changed(self, text):
        self._parameters["query_str"].value = str(text)

    def _names_changed(self):
        current_join_columns = self._parameters["join_columns"].list
        names = self._join_tables.selectedItems()
        self._parameters["join_tables"].list = [str(name.text())
                                                for name in names]
        columns = []
        columns_with_table = []
        names_text = []

        for filedb in self._filedbs:
            for name in names:
                name = name.text()
                names_text.append(name)
                [columns.append(str(column))
                 for column in filedb.table_column_names(name)
                 if column not in columns]
                [columns_with_table.append(str(name + '.' + column))
                 for column in filedb.table_column_names(name)]
            columns.sort()
        columns_with_table.sort()
        current_selected_cols = self._parameters["table_columns"].list
        self._table_columns.clear()
        self._table_columns.addItems(columns_with_table)
        # Mark columns previously selected as selected if column name still in
        # column list.
        for item in current_selected_cols:
            if item in columns_with_table:
                self._table_columns.findItems(
                    item, QtCore.Qt.MatchCaseSensitive)[0].setSelected(True)

        self._join_column_selection.clear()
        self._join_column_selection.addItems(columns_with_table)
        self._parameters["join_column_selection"].list = columns_with_table

        self._join_columns.clear()
        reset_join_on = []
        [reset_join_on.append(str(item)) for item in current_join_columns
            if item in columns_with_table]
        if len(reset_join_on) != 0:
            self._join_columns.addItems(reset_join_on)
        self._parameters["join_columns"].list = reset_join_on

        # Fix where_columns_combo values
        self._where_column_combo.clear()
        self._where_column_combo.addItems(columns_with_table)
        self._parameters["where_column_combo"].list = columns_with_table
        self._parameters["where_column_combo"].value = [0]

        # Remove where statements including table names not longer selected
        # for query
        where_statements = self._parameters["where_condition_list"].list
        valid_where_statements = []
        regex = re.compile("^([a-zA-Z0-9_]*).")
        [valid_where_statements.append(where_statement)
            for where_statement in where_statements
            if regex.findall(where_statement)[0] in names_text]

        self._parameters["where_condition_list"].list = valid_where_statements
        self._where_condition_list.clear()
        self._where_condition_list.addItems(valid_where_statements)

    def _columns_changed(self):
        columns = self._table_columns.selectedItems()
        self._parameters["table_columns"].list = (
            [str(column.text()) for column in columns])

    def _add_double_click(self):
        """Add items to join_column list widget."""
        item = self._join_column_selection.currentItem().text()
        self._join_columns.addItem(item)
        items = [str(self._join_columns.item(index).text())
                 for index in xrange(self._join_columns.count())]
        self._parameters["join_columns"].list = items

    def _remove_double_click(self):
        """Remove items from join_column list widget."""
        item = self._join_columns.currentItem().text()
        items = [str(self._join_columns.item(index).text())
                 for index in xrange(self._join_columns.count())]
        items.remove(item)
        self._join_columns.clear()
        self._join_columns.addItems(items)
        self._parameters["join_columns"].list = items

    def _change_order(self):
        """Change order on join_columns."""
        self._parameters["join_columns"].list = (
            [str(self._join_columns.item(index).text())
             for index in xrange(self._join_columns.count())])

    def _change_order_where(self):
        """Change order on where_statements."""
        self._parameters["where_condition_list"].list = (
            [str(self._where_condition_list.item(index).text())
             for index in xrange(self._where_condition_list.count())])

    def _where_column_changed(self, index):
        self._parameters["where_column_combo"].value = [index]

    def _where_comparison_changed(self, index):
        self._parameters["where_comparison_combo"].value = [index]

    def _where_condition_changed(self, text):
        self._parameters["where_condition"].value = str(text)

    def _add_where_clause(self):
        where_clause = ''
        condition = self._parameters["where_condition"].value
        if condition != '':
            where_clause += self._parameters["where_column_combo"].selected
            where_clause += self._parameters["where_comparison_combo"].selected
            where_clause += condition
            self._where_condition_list.addItem(where_clause)
            items = [str(self._where_condition_list.item(index).text())
                     for index in xrange(self._where_condition_list.count())]
            self._parameters["where_condition_list"].list = items

    def _remove_where_condition(self):
        item = self._where_condition_list.currentItem().text()
        items = [str(self._where_condition_list.item(index).text())
                 for index in xrange(self._where_condition_list.count())]
        items.remove(item)
        self._where_condition_list.clear()
        self._where_condition_list.addItems(items)
        self._parameters["where_condition_list"].list = items

    def _add_preview_table(self):
        """Preview table when button clicked."""
        try:
            filedb = self._filedb[0]
            query = sql.build_where_query(
                self._parameters["join_tables"].list,
                self._parameters["table_columns"].list,
                self._parameters["join_columns"].list,
                self._parameters["where_condition_list"].list)

            with filedb.to_rows_query(self._fq_infilename, query) as (
                    tablenames, tabledata):
                tablenames = list(tablenames)
                tabledata = list(tabledata)
                self._preview_table.clear()
                nbr_rows = len(tabledata)
                nbr_cols = len(tablenames)
                self._preview_table.setRowCount(nbr_rows)
                self._preview_table.setColumnCount(nbr_cols)
                self._preview_table.setHorizontalHeaderLabels(tablenames)

                for row_ind, row in enumerate(tabledata):
                    for col_ind, item in enumerate(list(row)):
                        self._preview_table.setItem(
                            row_ind, col_ind,
                            QtGui.QTableWidgetItem(str(item)))

        except:
            self._preview_table.clear()
            self._preview_table.setRowCount(1)
            self._preview_table.setColumnCount(1)
            self._preview_table.setItem(
                0, 0, QtGui.QTableWidgetItem('Not a valid query'))

    def _add_preview_query(self):
        """Preview query."""
        query = sql.build_where_query(
            self._parameters["join_tables"].list,
            self._parameters["table_columns"].list,
            self._parameters["join_columns"].list,
            self._parameters["where_condition_list"].list)

        self._preview_query.setText(str(query))
        self._parameters["preview_query"].value = str(query)


class DataImportSQL(importers.base.TableDataImporterBase):
    """Importer for SQL databases."""
    IMPORTER_NAME = "SQL"
    PARAMETER_VIEW = DataImportSQLWidget
    DATASOURCES = [importers.base.DATASOURCE.FILE,
                   importers.base.DATASOURCE.DATABASE]

    def __init__(self, fq_infilename, parameters):
        super(DataImportSQL, self).__init__(fq_infilename, parameters)

    def name(self):
        return self.IMPORTER_NAME

    def valid_for_file(self):
        """Return True if input file is a valid SQL file."""
        if self._fq_infilename is None:
            return False

        # Check if file Sqlite3
        return len(get_filedbs(self._fq_infilename)) > 0

    def valid_for_database(self):
        try:
            odbc_name = self._parameters['odbc'].selected
        except KeyError:
            odbc_name = 'odbc'

        odbc = odbc_module(odbc_name)

        try:
            connection_string = self._fq_infilename
            cnxn = odbc.connect(connection_string)
            cursor = cnxn.cursor()
            cursor.close()
            return True
        except:
            pass
        return False

    def parameter_view(self, parameters):
        valid_for_file = self.valid_for_file()
        datasource = (importers.base.DATASOURCE.FILE
                      if valid_for_file
                      else importers.base.DATASOURCE.DATABASE)
        return DataImportSQLWidget(
            parameters, self._fq_infilename, datasource=datasource)

    def import_data(self, out_datafile,
                    parameters=None, progress=None):
        """Import SQLite data from a file"""
        self._parameters = parameters
        # For auto to work. Need to know table name if not table name selected
        # yet.
        try:
            lineedit_query = self._parameters['lineedit_query'].value
        except:
            lineedit_query = False
        try:
            query_str = self._parameters["query_str"].value
        except:
            query_str = ''

        valid_for_file = self.valid_for_file()
        datasource = (importers.base.DATASOURCE.FILE
                      if valid_for_file
                      else importers.base.DATASOURCE.DATABASE)
        if datasource == importers.base.DATASOURCE.DATABASE:
            print lineedit_query
            if lineedit_query:
                # HACK(alexander): This is not a pretty solution.
                try:
                    try:
                        odbc_name = self._parameters['odbc'].selected
                    except KeyError:
                        odbc_name = 'odbc'

                    odbc = odbc_module(odbc_name)
                    with sql.table_from_odbc_query(
                            self._fq_infilename, query_str, odbc=odbc) as (
                                names, rows):
                        tabledata = table.File.from_rows(names, rows)
                except IndexError:
                    tabledata = table.File()
            else:
                raise NotImplementedError('')
            out_datafile.update(tabledata)
        elif datasource == importers.base.DATASOURCE.FILE:

            filedb = get_filedbs(self._fq_infilename)[0]

            try:
                table_name = self._parameters["table_names"].selected
            except:
                table_name = get_table_names(datasource, [filedb])[0]
            try:
                custom_query = self._parameters["custom_query"].value
            except:
                custom_query = False
            try:
                join_tables = self._parameters["join_tables"].list
            except:
                join_tables = []

            if lineedit_query:
                with filedb.to_rows_query(query_str) as (names, rows):
                    tabledata = table.File.from_rows(names, rows)

            elif custom_query:
                table_columns = self._parameters["table_columns"].list
                join_columns = self._parameters["join_columns"].list
                where_conditions = (
                    self._parameters["where_condition_list"].list)
                query = sql.build_where_query(
                    join_tables, table_columns, join_columns, where_conditions)
                with filedb.to_rows_query(query) as (names, rows):
                    tabledata = table.File.from_rows(names, rows)
            else:
                table_names = get_table_names(datasource, [filedb])

                if table_name not in table_names:
                    table_name = table_names[0]

                with filedb.to_rows_table(table_name) as (names, rows):
                    tabledata = table.File.from_rows(names, rows)
            out_datafile.update(tabledata)
