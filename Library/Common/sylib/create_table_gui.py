# -*- coding: utf-8 -*-
# Copyright (c) 2016, System Engineering Software Society
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
To generate data fast and easy is valuable when you want to test the
functionality of nodes or during the development process of nodes. In Sympathy
you can create a simple Table using the node Create Table.
"""
import json
import collections

import numpy as np
from sympathy.api import qt, ParameterView
QtGui = qt.QtGui
QtCore = qt.QtCore


def mock_wrap(cls):
    """
    For avoiding problems related to subclassing mocked class.
    This is used for being able to import modules without having the imports
    installed.
    See http://www.voidspace.org.uk/python/mock/.
    """
    return cls if isinstance(cls, type) else cls()


# These must be callable
NP_DATATYPES = collections.OrderedDict(
    [('U', unicode),
     ('f', float),
     ('i', int),
     ('b', bool)])


DATATYPES = collections.OrderedDict(
    [('Text', 'U'),
     ('Floating point', 'f'),
     ('Integer', 'i'),
     ('Boolean', 'b')])


DATATYPE_NAMES = collections.OrderedDict(
    [(v, k) for k, v in DATATYPES.items()])


def empty(datatype):
    """
    Factory function for creating an empty item depending of the correct
    datatype.
    """
    if datatype == 'U':
        return u''
    elif datatype == 'f':
        return 0.0
    elif datatype == 'i':
        return 0
    elif datatype == 'b':
        return False


class JsonTableModel(QtCore.QAbstractTableModel):
    """Model for storing a Sympathy-like table."""

    def __init__(self, data, parent=None):
        super(JsonTableModel, self).__init__(parent)

        # The data is stored as a list of columns. Each column is represented
        # as a list with three elements: name, datatype character, and column
        # values. The column values are in turn stored as a list of values.
        # For example, the table:
        # A  B
        # 1 'a'
        # 2 'b'
        #
        # is stored as: [['A', 'i', [1, 2]], ['B', 'U', ['a', 'b']]]
        self._data = json.loads(data)
        self.check_integrity()

    def get_json(self):
        """Return a serialized version of the model."""
        return json.dumps(self._data)

    def numpy_columns(self):
        """
        Returns a generator yielding tuples with column name and numpy array
        pairs.
        """
        for colname, datatype, coldata in self._data:
            yield (colname, np.array(coldata, dtype=NP_DATATYPES[datatype]))

    def check_integrity(self):
        """Raise exception if the data model seems to be corrupted."""
        length = None
        names = set()
        for colname, datatype, coldata in self._data:
            # Check that all columns have unique names.
            if colname in names:
                raise Exception(
                    "Column name {} is used for more than one column.".format(
                        colname))
            names.add(colname)

            # Check that all columns have legal datatype specifiers.
            if datatype not in DATATYPES.values():
                raise Exception(
                    "Column {} has invalid datatype: {}".format(
                        colname, datatype))

            # Check that all values in a column have the same datatype as the
            # column datatype specifier suggests.
            type_ = NP_DATATYPES[datatype]
            if any(not isinstance(v, type_) for v in coldata):
                raise Exception(
                    "Some of the values in column {} have incorrect type."
                    "".format(colname))

            # Check that all columns have the same length.
            if length is None:
                length = len(coldata)
            else:
                if length != len(coldata):
                    raise Exception(
                        "Column {} has length {} but some other column "
                        "has length {}".format(colname, len(coldata), length))

    def insert_row(self, n):
        """Insert an empty row just before index n."""
        # Can't add rows if there are no columns.
        if not len(self._data):
            return

        self.beginInsertRows(QtCore.QModelIndex(), n, n)
        for _, datatype, column in self._data:
            column.insert(n, empty(datatype))
        self.endInsertRows()
        self.check_integrity()

    def remove_row(self, n):
        """Remove the row at index n."""
        self.beginRemoveRows(QtCore.QModelIndex(), n, n)
        for _, _, column in self._data:
            del column[n]
        self.endRemoveRows()
        self.check_integrity()

    def insert_column(self, n, name, datatype):
        """
        Insert a column with the specified name and datatype just before
        index n.

        Arguments:
        n : int
            Insert the new column just before this column index.
        name : unicode
            The name of the new column.
        datatype : datatype
            A single character code ('b', 'i', 'f', or 'U') specifying the
            datatype of the column.
        """
        row_count = self.rowCount()
        self.beginInsertColumns(QtCore.QModelIndex(), n, n)
        self._data.insert(n, [name, datatype, [empty(datatype)] * row_count])
        self.endInsertColumns()
        self.check_integrity()

    def remove_column(self, n):
        """Remove the column at index n."""
        self.beginRemoveColumns(QtCore.QModelIndex(), n, n)
        del self._data[n]
        self.endRemoveColumns()

        # If we are about to remove the last column this will also remove all
        # rows. So emit layoutChanged to let the view know.
        if not len(self._data):
            self.layoutChanged.emit()
        self.check_integrity()

    def column_names(self):
        """Return column names in a list."""
        return [name for name, _, _ in self._data]

    def column_name(self, column):
        """Return column name for the specified column index."""
        return self._data[column][0]

    def set_column_name(self, column, name):
        """Set the column name for the specified column index to name."""
        self._data[column][0] = name
        self.headerDataChanged.emit(QtCore.Qt.Horizontal, column, column)
        self.check_integrity()

    def column_datatype(self, column):
        """Return column datatype for the specified column index."""
        return self._data[column][1]

    def set_column_datatype(self, column, datatype):
        """
        Set the column datatype for the specified column index to datatype.

        This is implemented as adding a new column with the new datatype and
        removing the old one.
        """
        def temp_name(old_name):
            column_names = set(self.column_names())
            i = 0
            while True:
                temp_name = "{}_{}".format(old_name, i)
                if temp_name not in column_names:
                    break
                i += 1
            return temp_name

        old_name = self._data[column][0]
        old_data = self._data[column][2]
        new_data = []
        for i, old_value in enumerate(old_data):
            try:
                new_data.append(NP_DATATYPES[datatype](old_value))
            except Exception as e:
                new_data.append(empty(datatype))

        self.insert_column(column, temp_name(old_name), datatype)
        for row, value in enumerate(new_data):
            index = self.createIndex(row, column)
            self.setData(index, value, QtCore.Qt.EditRole)
        self.remove_column(column + 1)
        self.set_column_name(column, old_name)
        self.check_integrity()

    def rowCount(self, parent=QtCore.QModelIndex()):
        """Return the number of rows in the table."""
        if not len(self._data):
            return 0
        else:
            # Return length of first column
            return len(self._data[0][2])

    def columnCount(self, parent=QtCore.QModelIndex()):
        """Return the number of columns in the table."""
        return len(self._data)

    def flags(self, index):
        """Return item flags. All items are editable, selectable and
        enabled.
        """
        return (QtCore.Qt.ItemIsEditable |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled)

    def headerData(self, section, orientation, role):
        """Return horizontal and vertical headers and tooltips."""
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._data[section][0]
            elif orientation == QtCore.Qt.Vertical:
                return unicode(section + 1)
        elif role == QtCore.Qt.ToolTipRole:
            if orientation == QtCore.Qt.Horizontal:
                return "Name: {}\nDatatype: {}".format(
                    self._data[section][0],
                    DATATYPE_NAMES[self._data[section][1]])

    def data(self, index, role):
        """Return data at index."""
        if not index.isValid():
            return
        row = index.row()
        column = index.column()

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return self._data[column][2][row]

    def setData(self, index, value, role):
        """Set data at index to value."""
        if not index.isValid():
            return
        row = index.row()
        column = index.column()

        if role == QtCore.Qt.EditRole:
            # TODO: Check datatype!
            self._data[column][2][row] = value
            self.check_integrity()
            self.dataChanged.emit(index, index)
            return True
        return False


class AddColumnDialog(QtGui.QDialog):
    """Dialog for specifying name and datatype for a new column."""

    def __init__(self, parent=None, title=u"New column", default_name='',
                 default_datatype='U'):
        super(AddColumnDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self._name_edit = QtGui.QLineEdit(self)
        self._name_edit.setText(default_name)
        self._datatype_edit = QtGui.QComboBox(self)
        self._datatype_edit.addItems(DATATYPES.keys())
        try:
            self._datatype_edit.setCurrentIndex(
                DATATYPES.values().index(default_datatype))
        except ValueError:
            pass

        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtGui.QFormLayout()
        layout.addRow("Column name:", self._name_edit)
        layout.addRow("Column datatype:", self._datatype_edit)
        layout.addRow(buttons)
        self.setLayout(layout)

    def column_name(self):
        return self._name_edit.text()

    def column_datatype(self):
        return DATATYPES[self._datatype_edit.currentText()]


@mock_wrap
class CreateTableWidget(ParameterView):
    """Gui for creating a static table."""

    def __init__(self, data, parent=None):
        super(CreateTableWidget, self).__init__(parent=parent)
        self.__selected_columns = []

        # Table model/view
        self._model = JsonTableModel(data)
        self._view = QtGui.QTableView(self)
        self._view.setSelectionMode(QtGui.QTableView.ContiguousSelection)
        self._view.setModel(self._model)

        # Buttons
        self._add_col_button = QtGui.QPushButton('Add column...')
        self._add_row_button = QtGui.QPushButton('Add row')
        self._del_col_button = QtGui.QPushButton('Delete column(s)')
        self._del_row_button = QtGui.QPushButton('Delete row(s)')
        button_layout = QtGui.QVBoxLayout()
        button_layout.addWidget(self._add_col_button)
        button_layout.addWidget(self._add_row_button)
        button_layout.addWidget(self._del_col_button)
        button_layout.addWidget(self._del_row_button)
        button_layout.addStretch(0)
        self._update_enabled_add_buttons()
        self._update_enabled_del_buttons()

        # Main layout
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self._view)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Actions (texts are updated each time context menus are built)
        self._add_row_before_action = QtGui.QAction("Add row before", self)
        self._add_row_after_action = QtGui.QAction("Add row after", self)
        self._add_col_before_action = QtGui.QAction("Add column before", self)
        self._add_col_after_action = QtGui.QAction("Add column after", self)
        self._del_row_action = QtGui.QAction("Delete selected rows", self)
        self._del_col_action = QtGui.QAction("Delete selected columns", self)
        self._edit_col_action = QtGui.QAction("Edit column name/type", self)
        self._add_row_before_action.activated.connect(self._add_row_before)
        self._add_row_after_action.activated.connect(self._add_row_after)
        self._add_col_before_action.activated.connect(self._add_col_before)
        self._add_col_after_action.activated.connect(self._add_col_after)
        self._del_row_action.activated.connect(self._del_selected_rows)
        self._del_col_action.activated.connect(self._del_selected_cols)
        self._edit_col_action.activated.connect(self._edit_selected_col)

        # Key bindings
        shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Delete), self._view)
        shortcut.activated.connect(self._clear_selected_values)

        # Signals
        self._add_col_button.clicked.connect(self._add_col)
        self._del_col_button.clicked.connect(self._del_selected_cols)
        self._add_row_button.clicked.connect(self._add_row)
        self._del_row_button.clicked.connect(self._del_selected_rows)

        # Connect model/selection changes to updating enabled state for buttons
        self._model.columnsInserted.connect(self._update_enabled_add_buttons)
        self._model.columnsRemoved.connect(self._update_enabled_add_buttons)
        self._model.columnsInserted.connect(
            self._update_enabled_del_buttons_on_model_change)
        self._model.columnsRemoved.connect(
            self._update_enabled_del_buttons_on_model_change)
        self._model.rowsInserted.connect(
            self._update_enabled_del_buttons_on_model_change)
        self._model.rowsRemoved.connect(
            self._update_enabled_del_buttons_on_model_change)
        # Temporary variable needed to avoid pyside crash:
        selection_model = self._view.selectionModel()
        selection_model.selectionChanged.connect(
            self._update_enabled_del_buttons_on_selection_change)

        # Connect items with custom context menu
        self._view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._item_menu)

        # Connect horizontal header with custom context menu
        horizontalHeader = self._view.horizontalHeader()
        horizontalHeader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        horizontalHeader.customContextMenuRequested.connect(
            self._horizontal_header_menu)

        # Connect vertical header with custom context menu
        verticalHeader = self._view.verticalHeader()
        verticalHeader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        verticalHeader.customContextMenuRequested.connect(
            self._vertical_header_menu)

    def _update_enabled_add_buttons(self, index=None, start=None, end=None):
        """Set the appropriate enabled state for the Add row button."""
        self._add_row_button.setEnabled(bool(self._model.columnCount()))

    def _update_enabled_del_buttons_on_model_change(
            self, index=None, start=None, end=None):
        self._update_enabled_del_buttons()

    def _update_enabled_del_buttons_on_selection_change(
            self, selected=None, deselected=None):
        self._update_enabled_del_buttons()

    def _update_enabled_del_buttons(self):
        """
        Set the appropriate enabled states for the Delete columns/rows buttons.
        """
        selection_model = self._view.selectionModel()
        self._del_row_button.setEnabled(
            bool(len(selection_model.selectedRows())))
        self._del_col_button.setEnabled(
            bool(len(selection_model.selectedColumns())))

    def _get_column_actions(self, selected_cols_count):
        """
        Return a list of actions that are relevant with the current number of
        selected columns.
        """
        if selected_cols_count == 0:
            return []
        elif selected_cols_count == 1:
            self._add_col_before_action.setText("Add column before")
            self._add_col_after_action.setText("Add column after")
            self._del_col_action.setText("Delete column")
            return [self._add_col_before_action, self._add_col_after_action,
                    self._del_col_action, self._edit_col_action]
        else:
            self._add_col_before_action.setText("Add column before selection")
            self._add_col_after_action.setText("Add column after selection")
            self._del_col_action.setText("Delete selected columns")
            return [self._add_col_before_action, self._add_col_after_action,
                    self._del_col_action]

    def _get_row_actions(self, selected_rows_count):
        """
        Return a list of actions that are relevant with the current number of
        selected rows.
        """
        if selected_rows_count == 0:
            return []
        elif selected_rows_count == 1:
            self._add_row_before_action.setText("Add row before")
            self._add_row_after_action.setText("Add row after")
            self._del_row_action.setText("Delete row")
        else:
            self._add_row_before_action.setText(
                "Add {} row before selection".format(selected_rows_count))
            self._add_row_after_action.setText(
                "Add {} row after selection".format(selected_rows_count))
            self._del_row_action.setText("Delete selected rows")
        return [self._add_row_before_action, self._add_row_after_action,
                self._del_row_action]

    def _item_menu(self, pos):
        """Show context menu for horizontal header items."""
        index = self._view.indexAt(pos)
        column = index.column()
        if column == -1:
            return

        # Select clicked item and deselect other items. If item was already
        # selected, don't deselect anything.
        selection_model = self._view.selectionModel()
        if not selection_model.isSelected(index):
            selection_model.clear()
            selection_model.select(index, QtGui.QItemSelectionModel.Select)

        # Find selected columns and store in private member
        # All actions that work on columns rely on __selected_columns.
        self.__selected_columns = [
            i.column() for i in selection_model.selectedColumns()]

        # Build and show context menu
        menu = QtGui.QMenu(self)
        actions = self._get_column_actions(len(self.__selected_columns))
        actions.extend(
            self._get_row_actions(len(selection_model.selectedRows())))
        if len(actions):
            for action in actions:
                menu.addAction(action)
            menu.popup(self._view.viewport().mapToGlobal(pos))

    def _horizontal_header_menu(self, pos):
        """Show context menu for horizontal header items."""
        column = self._view.horizontalHeader().logicalIndexAt(pos)
        if column == -1:
            return

        # Select clicked column and deselect partially selected columns
        selection_model = self._view.selectionModel()
        for c in range(self._model.columnCount()):
            if not selection_model.isColumnSelected(c, QtCore.QModelIndex()):
                selection_model.select(
                    self._model.createIndex(0, c),
                    QtGui.QItemSelectionModel.Deselect |
                    QtGui.QItemSelectionModel.Columns)
        if not selection_model.isColumnSelected(column, QtCore.QModelIndex()):
            self._view.selectColumn(column)

        # Find selected columns and store in private member
        # If there are no rows no columns will be selected, so finding the
        # selected columns from the selecteion model is not an option. Instead
        # all actions that work on columns should use __selected_columns.
        self.__selected_columns = [
            i.column() for i in selection_model.selectedColumns()] or [column]

        # Build and show context menu
        menu = QtGui.QMenu(self)
        actions = self._get_column_actions(len(self.__selected_columns))
        if len(actions):
            for action in actions:
                menu.addAction(action)
            menu.popup(self._view.viewport().mapToGlobal(pos))

    def _vertical_header_menu(self, pos):
        """Show context menu for vertical header items."""
        row = self._view.verticalHeader().logicalIndexAt(pos)
        if row == -1:
            return

        # Select clicked row
        selection_model = self._view.selectionModel()
        for r in range(self._model.rowCount()):
            if not selection_model.isRowSelected(r, QtCore.QModelIndex()):
                selection_model.select(
                    self._model.createIndex(r, 0),
                    QtGui.QItemSelectionModel.Deselect |
                    QtGui.QItemSelectionModel.Rows)
        if not selection_model.isRowSelected(row, QtCore.QModelIndex()):
            self._view.selectRow(row)

        # Build and show context menu
        menu = QtGui.QMenu(self)
        actions = self._get_row_actions(len(selection_model.selectedRows()))
        if len(actions):
            for action in actions:
                menu.addAction(action)
            menu.popup(self._view.viewport().mapToGlobal(pos))

    def _clear_selected_values(self):
        """
        Replace the values of all selected items with the default value for
        that columns datatype (empty string, zero, False, etc.).
        """
        indexes = self._view.selectedIndexes()
        # def setData(self, index, value, role):
        for index in indexes:
            datatype = self._model.column_datatype(index.column())
            self._model.setData(index, empty(datatype), QtCore.Qt.EditRole)

    def _add_col(self, col=None):
        """
        Add a column before index col.

        Display a dialog for choosing column name and datatype.
        Append column if col is None.
        """
        dialog = AddColumnDialog(self)
        result = dialog.exec_()
        if result == QtGui.QDialog.Rejected:
            return

        name = dialog.column_name()
        datatype = dialog.column_datatype()

        # Check that the column name is not empty and that it is not already in
        # the model.
        if name == '' or name in self._model.column_names():
            QtGui.QMessageBox.information(
                self, "Invalid name", "Invalid column name.")
            return

        if col is None:
            col = self._model.columnCount()
        self._model.insert_column(col, name, datatype)

    def _del_col(self, col=None):
        """Remove column at index col. Remove last column if col is None."""
        # Can't remove columns if there aren't any columns to remove.
        if not self._model.columnCount():
            return

        if col is None:
            col = self._model.columnCount() - 1
        self._model.remove_column(col)

    def _add_row(self, row=None):
        """Add a row before index row. Append row if row is None."""
        if row is None:
            row = self._model.rowCount()
        self._model.insert_row(row)

    def _del_row(self, row=None):
        """Remove row at index row. Remove last row if row is None."""
        # Can't remove rows if there aren't any rows to remove.
        if not self._model.rowCount():
            return

        if row is None:
            row = self._model.rowCount() - 1
        self._model.remove_row(row)

    def _del_selected_rows(self):
        """Delete all fully selected rows."""
        selection_model = self._view.selectionModel()
        rows = [i.row() for i in selection_model.selectedRows()]
        for row in sorted(rows, reverse=True):
            self._del_row(row)

    def _edit_selected_col(self):
        """Display a dialog for choosing a new column name and datatype."""
        cols = self._get_selected_cols()
        if len(cols) != 1:
            return
        col = cols[0]

        old_name = self._model.column_name(col)
        old_datatype = self._model.column_datatype(col)

        dialog = AddColumnDialog(self, "Edit column", old_name, old_datatype)
        result = dialog.exec_()
        if result == QtGui.QDialog.Rejected:
            return

        name = dialog.column_name()
        datatype = dialog.column_datatype()

        if name != old_name:
            # Check that the column name is not empty and that it is not
            # already in the model.
            if name in self._model.column_names() or name == '':
                QtGui.QMessageBox.information(
                    self, "Invalid name", "Invalid column name.")
                return
            self._model.set_column_name(col, name)
        if datatype != old_datatype:
            self._model.set_column_datatype(col, datatype)

    def _get_selected_cols(self):
        """
        Return a list of selected columns. This should work even in the case
        with no rows, where the 'selection' is whatever column header was
        clicked.
        """
        selection_model = self._view.selectionModel()
        cols = [i.column() for i in selection_model.selectedColumns()]

        # Fallback for when a horizontal header was clicked and no column is
        # properly selected:
        cols = cols or self.__selected_columns

        return cols

    def _del_selected_cols(self):
        """Delete all fully selected columns."""
        for col in sorted(self._get_selected_cols(), reverse=True):
            self._del_col(col)

    def _add_col_before(self):
        """Add a column before first selected column."""
        self._add_col(min(self._get_selected_cols()))

    def _add_col_after(self):
        """Add a column after last selected column."""
        self._add_col(max(self._get_selected_cols()) + 1)

    def _add_row_before(self):
        """
        Add as many rows as are currently selected before first selected row.
        """
        selection_model = self._view.selectionModel()
        selected_rows_count = len(selection_model.selectedRows())
        min_selected_row = min(
            i.row() for i in selection_model.selectedRows())
        for _ in range(selected_rows_count):
            self._add_row(min_selected_row)

    def _add_row_after(self):
        """
        Add as many rows as are currently selected after last selected row.
        """
        selection_model = self._view.selectionModel()
        selected_rows_count = len(selection_model.selectedRows())
        max_selected_row = max(
            i.row() for i in selection_model.selectedRows())
        for _ in range(selected_rows_count):
            self._add_row(max_selected_row + 1)
