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
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import functools
import keyword
import operator
import re
import tokenize
import traceback

import six
from six.moves import builtins

import numpy as np

from sympathy.api import node as synode
from sympathy.api import table, qt, ParameterView
from sympathy.platform.table_viewer import fuzzy_list_filter
from sympathy.platform import widget_library as sywidgets

QtGui = qt.QtGui  # noqa
QtCore = qt.QtCore  # noqa
from sylib.calculator import calculator_model as models
from sylib.calculator import plugins


class OldCalcListWidget(QtGui.QListWidget):
    layout_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(OldCalcListWidget, self).__init__(parent)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        model = self.model()
        model.layoutChanged.connect(self._layout_changed)

    def _layout_changed(self):
        self.layout_changed.emit()


class OldSignalListWidget(QtGui.QListWidget):
    def __init__(self, parent=None):
        super(OldSignalListWidget, self).__init__(parent)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
        self._format = '${{{0}}}'

    def set_format(self, format_):
        self._format = format_

    def mimeTypes(self):
        return ['text/plain']

    def mimeData(self, items):
        data = self._format.format(items[0].text())
        self._mime_data = QtCore.QMimeData()
        self._mime_data.setData('text/plain', data.encode('utf8'))
        return self._mime_data


class OldTreeDragWidget(QtGui.QTreeWidget):
    """Extends QtGui.QTreeWidget and lets it use drag and drop."""

    def __init__(self, parent=None):
        super(OldTreeDragWidget, self).__init__(parent)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)

    def mimeTypes(self):
        return 'text/plain'

    def mimeData(self, items):
        tree_item = items[0]
        if tree_item.childCount() == 0:
            data = tree_item.data(0, QtCore.Qt.UserRole)
            # TODO: Perhaps a good idea, but I don't like the implementation
            # if '(' not in data:
            #     data = tree_item.text(0)
            self._mime_data = QtCore.QMimeData()
            self._mime_data.setData('text/plain', data.encode('utf8'))
            return self._mime_data


class OldPreviewTable(QtGui.QTableWidget):
    def __init__(self, parent=None):
        super(OldPreviewTable, self).__init__(parent)

    def set_column(self, data, column):
        """Set all data for the given column."""
        for row, row_data in enumerate(data):
            # TODO: add formatting capability
            item = QtGui.QTableWidgetItem(six.text_type(row_data))
            self.setItem(row, column, item)


class CalcPreviewWorker(QtCore.QObject):
    preview_ready = QtCore.Signal(int, unicode, np.ndarray, bool)

    def __init__(self, calc_function):
        super(CalcPreviewWorker, self).__init__()
        self._calc_function = calc_function

    def create_preview_table(self, *args):
        outputs = []
        calc_list = args[0]

        for col_index, calc in enumerate(calc_list):
            is_error_column = False
            try:
                calc_res = self._calc_function(calc, dict(outputs))
                result = calc_res
                outputs.extend(calc_res)
            except Exception as e:
                # Show the exception in the preview
                error_lines = traceback.format_exception_only(type(e), e)
                try:
                    col_name = calc.split("=")[0].strip()
                    if (col_name.startswith("${") and
                            col_name.endswith("}") and
                            len(col_name) >= 4):
                        col_name = col_name[2:-1]
                except:
                    col_name = 'Calc {0}'.format(col_index)
                result = [(col_name, np.array(error_lines[-1:]))]
                outputs.extend(result)
                is_error_column = True
            for sub_result in result:
                self.preview_ready.emit(
                    col_index, six.text_type(sub_result[0]),
                    sub_result[1], is_error_column)


class OldCalculatorWidget(ParameterView):
    get_preview = QtCore.Signal(list)

    def __init__(self, in_data, parameters, backend='python',
                 preview_calculator=None, parent=None):
        super(OldCalculatorWidget, self).__init__(parent=parent)

        if isinstance(in_data, table.File):
            self._in_tables = table.FileList()
            self._in_tables.append(in_data)
            self._multiple_input = False
        else:
            self._in_tables = in_data
            self._multiple_input = True

        self._parameter_root = synode.parameters(parameters)
        self._backend = backend
        self.model = models.CalculatorModel(
            self._in_tables, parameters, backend=backend,
            preview_calculator=preview_calculator)
        self._has_preview = self.model.get_preview_calculator() is not None
        self._timeout_after = 1000
        self._calculation_timer = QtCore.QTimer(self)
        self._calculation_timer.setInterval(self._timeout_after)
        self._calculation_timer.setSingleShot(True)
        self._init_gui()
        if self._has_preview:
            self._init_preview_worker()

    def cleanup(self):
        if hasattr(self, '_preview_thread'):
            self._preview_thread.quit()
            self._preview_thread.wait()

    def _init_gui(self):
        """Sets up the main GUI structure."""
        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QtGui.QSplitter()
        splitter.setOrientation(QtCore.Qt.Vertical)
        splitter.setContentsMargins(0, 0, 0, 0)

        upper_layout = QtGui.QVBoxLayout()
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(5)
        upper_widget = QtGui.QWidget()
        upper_widget.setLayout(upper_layout)
        lower_layout = QtGui.QVBoxLayout()
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_widget = QtGui.QWidget()
        lower_widget.setLayout(lower_layout)

        self._calc_list = OldCalcListWidget()
        calc_splitter = QtGui.QSplitter()
        calc_list_widget = QtGui.QWidget()
        calc_list_layout = QtGui.QVBoxLayout()
        calc_list_layout.setContentsMargins(0, 0, 0, 0)
        calc_list_label = QtGui.QLabel("List of calculations")
        calc_list_widget.setLayout(calc_list_layout)
        calc_list_layout.addWidget(calc_list_label)
        calc_list_layout.addWidget(self._calc_list)
        calc_splitter.addWidget(calc_list_widget)

        add_button = QtGui.QPushButton("New")
        remove_button = QtGui.QPushButton("Remove")

        button_layout = QtGui.QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addStretch(0)

        if self._has_preview:
            preview_layout = QtGui.QVBoxLayout()
            preview_layout.setContentsMargins(0, 0, 0, 0)
            self._preview_table = OldPreviewTable()
            self._preview_table.setSelectionMode(
                QtGui.QAbstractItemView.NoSelection)
            preview_table_label = QtGui.QLabel("Preview:")
            preview_widget = QtGui.QWidget()
            preview_layout.addWidget(preview_table_label)
            preview_layout.addWidget(self._preview_table)
            preview_widget.setLayout(preview_layout)
            calc_splitter.addWidget(preview_widget)

        upper_layout.addWidget(calc_splitter)
        upper_layout.addLayout(button_layout)

        edit_signals = QtGui.QLabel('Signal Name: ')
        self._signal_name = QtGui.QLineEdit('')

        # Calculation line edits
        calc_line_label = QtGui.QLabel("Calculation")
        self._calc_line = QtGui.QPlainTextEdit()

        # This should select the systems default monospace font
        f = QtGui.QFont('')
        f.setFixedPitch(True)
        self._calc_line.setFont(f)

        self._calc_line.setUndoRedoEnabled(True)
        # self._calc_line.setMaximumHeight(100)
        self._calc_line.setWordWrapMode(QtGui.QTextOption.NoWrap)
        if self._backend == 'python':
            self._highlighter = PythonHighlight(self._calc_line.document())

        line_edit_layout = QtGui.QVBoxLayout()
        line_edit_layout.addWidget(calc_line_label)
        line_edit_layout.addWidget(self._calc_line)

        signal_edit_layout = QtGui.QHBoxLayout()
        signal_edit_layout.addWidget(edit_signals)
        signal_edit_layout.addWidget(self._signal_name)

        signal_layout = QtGui.QHBoxLayout()

        # List of available Signals names
        self._signals_label = QtGui.QLabel("Signals")
        self._signals_label.setWordWrap(True)
        self._column_name_list = OldSignalListWidget()
        self._column_name_list.setMaximumWidth(2000)

        # List of available Signals names
        function_label = QtGui.QLabel("Common functions")
        function_label.setWordWrap(True)
        function_tree = OldTreeDragWidget()
        function_tree.setMaximumWidth(2000)

        signal_list_layout = QtGui.QVBoxLayout()
        signal_list_layout.addWidget(self._signals_label)
        signal_list_layout.addWidget(self._column_name_list)

        function_tree_layout = QtGui.QVBoxLayout()
        function_tree_layout.addWidget(function_label)
        function_tree_layout.addWidget(function_tree)

        signal_layout.addLayout(function_tree_layout)
        signal_layout.addLayout(signal_list_layout)

        signal_box_layout = QtGui.QVBoxLayout()
        signal_box_layout.setContentsMargins(5, 5, 5, 5)
        signal_box_layout.addLayout(signal_edit_layout)
        signal_box_layout.addLayout(line_edit_layout)

        signal_box = QtGui.QGroupBox('Edit Signal')
        signal_box.setLayout(signal_box_layout)

        self.search_field = QtGui.QLineEdit('')
        self.search_field.setPlaceholderText('Search function name')
        search_field_layout = QtGui.QHBoxLayout()
        search_field_layout.addWidget(self.search_field)

        lower_layout.addWidget(signal_box)
        lower_layout.addLayout(signal_layout)
        function_tree_layout.addLayout(search_field_layout)
        if self._multiple_input:
            lower_layout.addWidget(self.model.get_same_length_res_gui())

        splitter.addWidget(upper_widget)
        splitter.addWidget(lower_widget)
        splitter.setChildrenCollapsible(True)

        if self._backend == 'matlab':
            vlayout_matlab = QtGui.QVBoxLayout()
            layout.addLayout(vlayout_matlab)

        layout.addWidget(splitter)
        self.setLayout(layout)
        init_tree(function_tree, self._backend)
        self._init_gui_from_parameters()
        if self._has_preview:
            self._update_preview()

        self.tree_head = function_tree.invisibleRootItem()

        add_button.clicked.connect(self._new_calculation)
        remove_button.clicked.connect(self._remove_item)
        if self._backend == 'python':
            self._calc_line.textChanged.connect(self._highlighter.rehighlight)
        self._calc_line.textChanged.connect(self._calc_line_changed)
        if self._has_preview:
            self._calculation_timer.timeout.connect(self._update_preview)
        self._signal_name.textChanged.connect(self._signal_name_changed)
        self._calc_list.itemClicked.connect(self._edit_calc_item)
        self._calc_list.layout_changed.connect(self._change_list)
        self._column_name_list.itemDoubleClicked.connect(self._insert_signal)
        self.search_field.textEdited.connect(self._search_function)
        function_tree.itemDoubleClicked.connect(self._insert_function)

    def _init_gui_from_parameters(self):
        """Initialises GUI from context_node parameters."""
        self._calc_line.clear()
        self._calc_list.clear()
        self._column_name_list.clear()
        self._calc_list.addItems(self.model.get_calc_list())
        self._column_name_list.addItems(self.model.get_column_names())

    def _init_preview_worker(self):
        """Compute preview data."""
        prev_calc = self.model.get_preview_calculator()
        if self._has_preview:
            table_filelist = self.model.get_input()
            if table_filelist.is_valid() and len(table_filelist):
                table_file = table_filelist[0]
            else:
                table_file = table.File()
            # create partial function
            self._worker_preview_calc = functools.partial(
                prev_calc, table_file)

            self._preview_thread = QtCore.QThread()
            self._preview_worker = CalcPreviewWorker(self._worker_preview_calc)
            self._preview_worker.moveToThread(self._preview_thread)
            self._preview_thread.finished.connect(
                self._preview_worker.deleteLater)
            self.get_preview.connect(self._preview_worker.create_preview_table)
            self._preview_worker.preview_ready.connect(self._update_column)
            self._preview_thread.start()

            self._update_preview()

    def _insert_signal(self, item):
        self._calc_line.insertPlainText(u"${%s}" % item.text())

    def _insert_function(self, item):
        text = item.data(0, QtCore.Qt.UserRole)
        if text:
            self._calc_line.insertPlainText(text)

    def get_calculation(self):
        item = ""
        index = 0
        name = self._signal_name.text()
        calc_value = self.model.get_calc_line_value()
        if re.findall(r'\${([^{}]+)}', name) == []:
            name = '${' + name + '}'
        calculation = name + " = " + calc_value
        for i in range(self._calc_list.count()):
            item = six.text_type(self._calc_list.item(i).text())
            index = i
            if name == item.split('=')[0].strip():
                return calc_value, calculation, index
        if self._calc_list.count() == 0:
            return calc_value, calculation, index
        return calc_value, calculation, index + 1

    def _update_calc_list(self, calc_value, calculation, index):
        if calculation != '' and calc_value != '':
            if self._calc_list.item(index) is None:
                self._calc_list.addItem(calculation)
            else:
                self._calc_list.item(index).setText(calculation)
            items = [six.text_type(self._calc_list.item(i).text())
                     for i in range(self._calc_list.count())]
            self.model.set_calc_list(items)
            self._calc_list.setCurrentItem(self._calc_list.item(index))
            if self._has_preview:
                self._calculation_timer.start()

    def _new_calculation(self):
        """Adds a calculation to the calculation list widget.
        If signal name already exists the signal will be overwritten.
        """
        self._calc_line.clear()
        self._signal_name.setText('')
        self.model.set_calc_line_value('')

    def _calc_line_changed(self):
        """Calculation line changed."""
        text = self._calc_line.toPlainText()
        self.model.set_calc_line_value(six.text_type(text))
        calc_value, calculation, index = self.get_calculation()
        self._update_calc_list(calc_value, calculation, index)
        self._calc_list.setCurrentItem(self._calc_list.item(index))

    def _signal_name_changed(self):
        item = self._calc_list.currentItem()
        calc_value, calculation, index = self.get_calculation()
        if index != self._calc_list.row(item):
            self.remove_from_list(self._calc_list.item(index))
        if index == self._calc_list.count():
            index = self._calc_list.row(item)
        self._update_calc_list(calc_value, calculation, index)
        self._calc_list.setCurrentItem(self._calc_list.item(index))

    def _show_hide_func(self, state):
        if state == QtCore.Qt.Checked:
            self._show_hide_lists(True)
        else:
            self._show_hide_lists(False)

    def _show_hide_lists(self, state):
        self.model.set_show_func_value(state)
        if state:
            self._signals_label.show()
            self._column_name_list.show()
        else:
            self._signals_label.hide()
            self._column_name_list.hide()

    def remove_from_list(self, item):
        """Remove items from calculation list widget."""
        if item is not None:
            text = item.text()
            items = [six.text_type(self._calc_list.item(index).text())
                     for index in range(self._calc_list.count())]
            items.remove(text)
            self._calc_list.takeItem(self._calc_list.row(item))
            self._calc_list.update()
            self.model.set_calc_list(items)

    def _remove_item(self):
        """Remove items from calculation list widget."""
        item = self._calc_list.currentItem()
        self.remove_from_list(item)
        self._new_calculation()

    def _edit_calc_item(self):
        """Edits the marked calculation in calculation list widget."""
        item = self._calc_list.currentItem()
        var, calc = item.text().split('=', 1)
        var = var.strip().replace('${', '').replace('}', '')
        calc = calc.strip()
        self._signal_name.setText(var)
        self._calc_line.setPlainText(calc)

    def _change_list(self):
        """Update parameter calculation list widget
        when calculation list has changed
        """
        self.model.set_calc_list(
            [six.text_type(self._calc_list.item(index).text()) for index in
             range(self._calc_list.count())])
        if self._has_preview:
            self._calculation_timer.start()

    @QtCore.Slot()
    def _update_preview(self):
        """Updates the preview view."""
        if not self._in_tables.is_valid():
            return

        calc_list = self.model.get_calc_list()
        self._preview_table.clear()
        self._preview_table.setColumnCount(len(calc_list))
        self.get_preview.emit(calc_list)

    @QtCore.Slot(int, unicode, np.ndarray, bool)
    def _update_column(self, column_idx, column_name, data, is_error):
        row_count = 20

        # TODO: change this for all empty output
        self._preview_table.setRowCount(row_count + 1)

        header_item = QtGui.QTableWidgetItem()
        header_item.setText(column_name)
        self._preview_table.setHorizontalHeaderItem(column_idx, header_item)

        if data.ndim > 0:
            self._preview_table.set_column(data[:row_count], column_idx)
            if is_error:
                self._preview_table.item(0, column_idx).setBackground(
                    QtGui.QColor.fromRgb(228, 186, 189))
            else:
                self._preview_table.setItem(
                    row_count, column_idx, QtGui.QTableWidgetItem(
                        u"({} rows)".format(data.size)))
                self._preview_table.item(row_count, column_idx).setBackground(
                    QtGui.QColor.fromRgb(253, 246, 227))
        else:
            self._preview_table.setItem(
                0, column_idx, QtGui.QTableWidgetItem(six.text_type(data)))

    def set_timeout(self, timeout):
        self._timeout_after = int(timeout)
        self._calculation_timer.setInterval(self._timeout_after)

    def _search_function(self):
        term = self.search_field.text()
        recursive_hide(self.tree_head, term)


def recursive_hide(node, word):
    status = 0
    if node.childCount() < 1:
        # This is a leave
        text = node.text(0)
        data = node.data(0, QtCore.Qt.UserRole)
        if word not in data and word not in text:
            status = 1
    else:
        count = 0
        for index in range(0, node.childCount()):
            count += recursive_hide(node.child(index), word)
        if count == node.childCount():
            # All children are hidden
            status = 1

    node.setHidden(status)
    node.setExpanded(~status)
    if len(word) == 0:
        node.setExpanded(status)

    return status


class PythonHighlight(QtGui.QSyntaxHighlighter):
    def __init__(self, *args, **kwargs):
        super(PythonHighlight, self).__init__(*args, **kwargs)
        self._tokens = []
        self._highlighting = False

    def _format(self, token_type):
        base01 = QtGui.QColor("#586e75")  # Optional emphasized content
        base00 = QtGui.QColor("#657b83")  # Body text / main content
        base1 = QtGui.QColor("#93a1a1")  # Comments / secondary content
        base2 = QtGui.QColor("#eee8d5")  # Background highlights
        base3 = QtGui.QColor("#fdf6e3")  # Background
        yellow = QtGui.QColor("#b58900")
        orange = QtGui.QColor("#cb4b16")
        red = QtGui.QColor("#dc322f")
        magenta = QtGui.QColor("#d33682")
        violet = QtGui.QColor("#6c71c4")
        blue = QtGui.QColor("#268bd2")
        cyan = QtGui.QColor("#2aa198")
        green = QtGui.QColor("#859900")

        COLORS = {
            'other': base00,
            'keyword': orange,
            'builtin': yellow,
            'column': green,
            tokenize.ERRORTOKEN: red,
            tokenize.STRING: orange,
            tokenize.NUMBER: cyan,
            tokenize.COMMENT: base1,
            tokenize.AT: green}

        f = QtGui.QTextCharFormat()
        try:
            f.setForeground(COLORS[token_type])
        except KeyError:
            f.setForeground(COLORS['other'])

        return f

    def _tokenize_document(self):
        s = six.StringIO(self.document().toPlainText())
        self._tokens = []
        tokenize.tokenize(s.readline, self._add_token)

    def _add_token(self, token_type, token_text, start, end, line):
        self._tokens.append((token_type, token_text, start, end))

    def _start_and_length(self, tstart, tend, lines):
        block_start_row = self.previousBlockState() + 1
        tstart_row, tstart_col = tstart
        tend_row, tend_col = tend

        if tstart_row < block_start_row:
            # Token starts before this text block
            start_pos = 0
        elif tstart_row > block_start_row + len(lines):
            # Entire token is after this text block
            return None, None
        else:
            # Token end is inside this text block
            start_pos = 0
            for i, line in enumerate(lines, 1):
                if tstart_row > block_start_row + i:
                    start_pos += len(line)
                elif tstart_row == block_start_row + i:
                    start_pos += tstart_col

        if tend_row < block_start_row:
            # Entire token is before this text block
            return None, None
        elif tend_row > block_start_row + len(lines):
            # Token ends after this text block
            length = sum([len(line) for line in lines]) - start_pos
        else:
            # Token end is inside this text block
            end_pos = 0
            for i, line in enumerate(lines, 1):
                if tend_row > block_start_row + i:
                    end_pos += len(line)
                elif tend_row == block_start_row + i:
                    end_pos += tend_col
            length = end_pos - start_pos

        # The line with this position is not in this text block
        return start_pos, length

    def rehighlight(self):
        # Prevent highlighting calling itself
        if self._highlighting:
            return
        self._highlighting = True

        try:
            self._tokenize_document()
        except tokenize.TokenError:
            pass
        super(PythonHighlight, self).rehighlight()
        self._highlighting = False

    def highlightBlock(self, text):
        skip_to_pos = -1
        lines = text.split('\n')

        for token in self._tokens:
            token_type, token_text, tstart, tend = token
            start, length = self._start_and_length(tstart, tend, lines)
            if start is None or length is None:
                # This token is in another text block
                continue
            if start < skip_to_pos:
                # This token has already been taken care of
                continue

            # The column syntax ${mycol} isn't known to the tokenize module.
            # It also spans several tokens so it needs to be treated
            # separately.
            if token_text == '$' and text[start + 1:start + 2] == '{':
                match = re.search('}', text[start:])
                if match:
                    token_type = 'column'
                    length = match.start() + 1
                    skip_to_pos = start + length

            # The tokenize module doesn't distinguish between different types
            # of names.
            if token_type == tokenize.NAME:
                if keyword.iskeyword(token_text):
                    token_type = 'keyword'
                elif hasattr(builtins, token_text):
                    token_type = 'builtin'

            self.setFormat(start, length, self._format(token_type))

        self.setCurrentBlockState(self.previousBlockState() + len(lines))


def init_tree(function_tree, backend):
    """Initialises the function tree widget with common functions with
    tooltips.

    Parameters
    ---------
    function_tree : OldTreeDragWidget
        Function tree widget.
    backend : str or unicode
        Name of the backend. Either 'matlab' or 'python'.
    """
    function_tree.setDragEnabled(True)
    function_tree.setDropIndicatorShown(True)
    function_tree.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
    function_tree.setColumnCount(1)
    function_tree.headerItem().setHidden(True)

    def build_tree(root, content):
        if isinstance(content, list):
            for tree_text, eval_string, doc_string in content:
                _add_tree_item(root, tree_text, doc_string, eval_string)
        elif isinstance(content, dict):
            for tree_text, subcontent in six.iteritems(content):
                subroot = QtGui.QTreeWidgetItem(root)
                subroot.setText(0, tree_text)
                build_tree(subroot, subcontent)
        else:
            raise TypeError("Content contained ")

    available_plugins = sorted(plugins.available_plugins(backend),
                               key=operator.attrgetter("WEIGHT"))
    for plugin in available_plugins:
        build_tree(function_tree, plugin.gui_dict())


def _add_tree_item(parent, text, tool_tip, func_name, column=0):
    """Creates a new QtGui.QTreeWidgetItem and adds it as child to parent.

    Parameters:
    -----------
    parent : QtGui.QTreeWidgetItem
        The parent QtGui.QTreeWidgetItem node.
    column : int
        The column the text should be placed in.
    text : string
        The node text
    func_name : string
        The method syntax
    tool_tip : string
        The text at the tooltip

    Returns
    --------
    QtGui.QTreeWidgetItem
        The new QtGui.QTreeWidgetItem node.
    """
    item = QtGui.QTreeWidgetItem(parent)
    item.setText(column, text)
    item.setToolTip(column, tool_tip)
    item.setData(0, QtCore.Qt.UserRole, func_name)
    parent.addChild(item)
    return item


class PreviewTable(QtGui.QTableView):
    def __init__(self, parent=None):
        super(PreviewTable, self).__init__(parent)
        # TODO: enhance PreviewTable


class SignalTableWidget(QtGui.QTableWidget):
    def __init__(self, parent=None):
        super(SignalTableWidget, self).__init__(parent)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
        self._format = '${{{0}}}'

        self.setColumnCount(2)
        # self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setHorizontalHeaderLabels(['Name', 'Type'])
        self.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

    def current_items(self):
        selection_model = self.selectionModel()
        indexes = selection_model.selectedIndexes()
        return [self.itemFromIndex(i) for i in indexes if i.column() == 0]

    def get_items(self):
        return [self.item(r, 0) for r in range(self.rowCount())]

    def set_format(self, format_):
        self._format = format_

    def mimeTypes(self):
        return ['text/plain']

    def mimeData(self, items):
        data = ''.join([self._format.format(item.text()) for item in items
                        if item.column() == 0])
        self._mime_data = QtCore.QMimeData()
        self._mime_data.setData('text/plain', data.encode('utf8'))
        return self._mime_data


class TreeDragWidget(QtGui.QTreeWidget):
    """Extends QtGui.QTreeWidget and lets it use drag and drop."""

    def __init__(self, parent=None):
        super(TreeDragWidget, self).__init__(parent)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)

    def mimeTypes(self):
        return ['function/plain']

    def mimeData(self, items):
        tree_item = items[0]
        if tree_item.childCount() == 0:
            data = tree_item.data(0, QtCore.Qt.UserRole)
            # TODO: Perhaps a good idea, but I don't like the implementation
            # if '(' not in data:
            #     data = tree_item.text(0)
            self._mime_data = QtCore.QMimeData()
            self._mime_data.setData('function/plain', data.encode('utf8'))
            return self._mime_data


class CalcFieldWidget(QtGui.QPlainTextEdit):
    insert_function = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(CalcFieldWidget, self).__init__(parent=parent)
        # This should select the systems default monospace font
        f = QtGui.QFont('')
        f.setFixedPitch(True)
        self.setFont(f)

        self.setUndoRedoEnabled(True)
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)

    def canInsertFromMimeData(self, source):
        if source.hasFormat('function/plain'):
            return True
        else:
            res = super(CalcFieldWidget, self).canInsertFromMimeData(source)
            return res

    def insertFromMimeData(self, source):
        if source.hasFormat('function/plain'):
            text = source.data('function/plain').data()
            self.insert_function.emit(text)
        else:
            super(CalcFieldWidget, self).insertFromMimeData(source)


class ModelTableView(QtGui.QTableView):
    current_row_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(ModelTableView, self).__init__(parent=parent)
        # TODO (Benedikt): internal drag and drop disabled since it is not
        # working correctly
        # self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        # self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        # self.setDragDropMode(self.InternalMove)

        self.verticalHeader().setResizeMode(
            QtGui.QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

    def setModel(self, model):
        super(ModelTableView, self).setModel(model)
        selection_model = self.selectionModel()
        selection_model.currentRowChanged.connect(self.current_row_changed)

    # def dragEnterEvent(self, event):
    #     event.accept()
    #
    # def dropEvent(self, event):
    #     model = self.model()
    #     if (event.source() == self and
    #             (event.dropAction() == QtCore.Qt.MoveAction or
    #              self.dragDropMode() == QtGui.QAbstractItemView.InternalMove)):
    #         success, row, col, topIndex = self.drop_on(event)
    #
    #         if success:
    #             drop_row = row
    #             if drop_row == -1:
    #                 drop_row = model.rowCount()
    #             selected_rows = self.get_selected_rows_fast()
    #             top = selected_rows[0]
    #             offset = drop_row - top
    #             for i, row in enumerate(selected_rows):
    #                 r = row + offset
    #                 if r > model.rowCount() or r < 0:
    #                     r = 0
    #
    #                 item = model.item(row, 0)
    #                 moved_item = model.insert_item(item.name,
    #                                                item.calculation, r)
    #
    #                 selection_model = self.selectionModel()
    #                 selection_model.setCurrentIndex(moved_item.index(),
    #                                 QtGui.QItemSelectionModel.ClearAndSelect |
    #                                 QtGui.QItemSelectionModel.Rows)
    #             # oddly removing the dragged row is not needed
    #             event.accept()
    #     elif event.dropAction() == QtCore.Qt.CopyAction:
    #         success, row, col, topIndex = self.drop_on(event)
    #         if success:
    #             self.model().dropMimeData(event.mimeData(),
    #                                       event.dropAction(),
    #                                       row, col, topIndex)
    #
    #             event.accept()
    #     else:
    #         super(ModelTableView, self).dropEvent(event)

    # def get_selected_rows_fast(self):
    #     selected_rows = set()
    #     for index in self.selectedIndexes():
    #         selected_rows.add(index.row())
    #     return list(selected_rows)
    #
    # def dropping_on_itself(self, event, index):
    #     drop_action = event.dropAction()
    #
    #     if self.dragDropMode() == QtGui.QAbstractItemView.InternalMove:
    #         drop_action = QtCore.Qt.MoveAction
    #
    #     if (event.source() == self and
    #                 event.possibleActions() & QtCore.Qt.MoveAction and
    #                 drop_action == QtCore.Qt.MoveAction):
    #         selected_indexes = self.selectedIndexes()
    #         child = index
    #         while child.isValid() and child != self.rootIndex():
    #             if child in selected_indexes:
    #                 return True
    #             child = child.parent()
    #         return False

    # def drop_on(self, event):
    #     if event.isAccepted():
    #         return False, None, None, None
    #
    #     index = QtCore.QModelIndex()
    #     row = -1
    #     col = -1
    #
    #     if self.viewport().rect().contains(event.pos()):
    #         index = self.indexAt(event.pos())
    #         if not index.isValid() or not self.visualRect(index).contains(
    #                 event.pos()):
    #             index = self.rootIndex()
    #
    #     if self.model().supportedDropActions() & event.dropAction():
    #         if index != self.rootIndex():
    #             drop_indicator_pos = self.position(event.pos(),
    #                                                self.visualRect(index),
    #                                                index)
    #             if drop_indicator_pos == QtGui.QAbstractItemView.BelowItem:
    #                 row = index.row() + 1
    #                 col = index.column()
    #             else:
    #                 row = index.row()
    #                 col = index.column()
    #         if not self.dropping_on_itself(event, index):
    #             return True, row, col, index
    #
    #     return False, None, None, None
    #
    # def position(self, pos, rect, index):
    #     r = QtGui.QAbstractItemView.OnViewport
    #     margin = 2
    #     if pos.y() - rect.top() < margin:
    #         r = QtGui.QAbstractItemView.BelowItem
    #     elif rect.bottom() - pos.y() < margin:
    #         r = QtGui.QAbstractItemView.OnItem
    #     elif rect.contains(pos, True):
    #         r = QtGui.QAbstractItemView.OnItem
    #
    #     if r == QtGui.QAbstractItemView.OnItem and not (self.model().flags(
    #             index) & QtCore.Qt.ItemIsDragEnabled):
    #         if pos.y() < rect.center().y():
    #             r = QtGui.QAbstractItemView.AboveItem
    #         else:
    #             r = QtGui.QAbstractItemView.BelowItem
    #     return r

    def current_item(self):
        index = self.currentIndex()
        if not index.isValid():
            return None
        if index.column() == 0:
            item = self.model().itemFromIndex(index)
        else:
            item = self.model().item(index.row(), 0)
        return item


class CalculatorModelView(QtGui.QWidget):
    new_item_added = QtCore.Signal()

    def __init__(self, model, parent=None):
        super(CalculatorModelView, self).__init__(parent=parent)

        assert(isinstance(model, models.CalculatorItemModel))
        self._model = model

        self.view = ModelTableView(parent=self)

        self.view.setModel(self._model)

        toolbar = sywidgets.SyToolBar(self)
        toolbar.setIconSize(QtCore.QSize(18, 18))
        toolbar.add_action('Add',
                           'actions/list-add-symbolic.svg',
                           'Add column',
                           receiver=self.add_item)
        toolbar.add_action('Remove',
                           'actions/list-remove-symbolic.svg',
                           'Remove column',
                           receiver=self.remove_item)
        toolbar.add_action('Copy',
                           'actions/edit-copy-symbolic.svg',
                           'Copy column',
                           receiver=self.copy_item)

        toolbar.addStretch()
        toolbar.add_action('Move up',
                           'actions/go-up-symbolic.svg',
                           'Move row up',
                           receiver=self.move_item_up)
        toolbar.add_action('Move down',
                           'actions/go-down-symbolic.svg',
                           'Move row down',
                           receiver=self.move_item_down)

        layout = QtGui.QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        layout.addWidget(toolbar)
        self.setLayout(layout)

    def add_item(self):
        item = self._model.add_item()
        self.view.setCurrentIndex(item.index())
        self.new_item_added.emit()

    def remove_item(self):
        current_selected_index = self.view.currentIndex()
        self._model.remove_item(current_selected_index.row())

    def copy_item(self):
        current_selected_index = self.view.currentIndex()
        self._model.copy_item(current_selected_index.row())

    def move_item_up(self):
        self._move_item(-1)

    def move_item_down(self):
        self._move_item(1)

    def _move_item(self, direction):
        index = self.view.currentIndex()
        row = index.row()
        if direction > 0 and row == self._model.rowCount() - 1:
            return
        elif direction < 0 and row == 0:
            return
        items_row = self._model.takeRow(row)
        self._model.insertRow(row + direction, items_row)
        selection_model = self.view.selectionModel()
        selection_model.setCurrentIndex(items_row[0].index(),
                                    QtGui.QItemSelectionModel.ClearAndSelect |
                                    QtGui.QItemSelectionModel.Rows)
        items_row[0].emitDataChanged()


class ItemEditBox(QtGui.QGroupBox):

    def __init__(self, *args, **kwargs):
        self._backend = kwargs.pop('backend', None)
        super(ItemEditBox, self).__init__(*args, **kwargs)
        self._item = None
        self.highlighter = None
        self._init_gui()
        self.set_backend(self._backend)

    def _init_gui(self):

        self.column_name = QtGui.QLineEdit('')
        self.column_name.setPlaceholderText('Column name')

        calc_line_label = QtGui.QLabel('Calculation:')
        self.calc_field = CalcFieldWidget(parent=self)

        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.column_name)
        layout.addWidget(calc_line_label)
        layout.addWidget(self.calc_field)
        self.setLayout(layout)

        self.setTabOrder(self.column_name, self.calc_field)

    def set_backend(self, backend):
        self._backend = backend

        if self._backend == 'python':
            self.highlighter = PythonHighlight(self.calc_field.document())
            self.calc_field.textChanged.connect(self.highlighter.rehighlight)
        else:
            self.calc_field.textChanged.disconnect(
                self.highlighter.rehighlight)

    def set_item(self, item):
        if self._item is not None:
            self.column_name.textChanged.disconnect(self.column_name_changed)
            self.calc_field.textChanged.disconnect(self.calc_line_changed)
        self._item = item

        if item is not None:
            self.column_name.setText(self._item.name)
            self.calc_field.setPlainText(self._item.calculation)
            self.column_name.textChanged.connect(self.column_name_changed)
            self.calc_field.textChanged.connect(self.calc_line_changed)

    def column_name_changed(self):
        if self._item is not None:
            self._item.name = self.column_name.text()

    def calc_line_changed(self):
        if self._item is not None:
            self._item.calculation = self.calc_field.toPlainText()


class CalculatorWidget(ParameterView):
    def __init__(self, in_data, parameters, backend='python',
                 preview_calculator=None, parent=None):
        super(CalculatorWidget, self).__init__(parent=parent)

        self._status_message = ''

        if isinstance(in_data, table.File):
            self._in_tables = table.FileList()
            self._in_tables.append(in_data)
            self._multiple_input = False
        else:
            self._in_tables = in_data
            self._multiple_input = True

        self._parameter_root = parameters
        self._backend = backend
        self.model = models.CalculatorItemModel(
            self._in_tables, parameters, backend=backend,
            preview_calculator=preview_calculator)
        self.preview_model = models.PreviewModel(self.model)

        self.init_gui()
        self.init_gui_from_model()

    def init_gui(self):
        model_view = CalculatorModelView(self.model)
        self.model_view = model_view.view

        preview_view = PreviewTable()
        preview_view.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        preview_view.setModel(self.preview_model)

        hsplitter = QtGui.QSplitter()
        hsplitter.setOpaqueResize(QtCore.Qt.Horizontal)
        hsplitter.setContentsMargins(0, 0, 0, 0)
        hsplitter.addWidget(model_view)
        hsplitter.addWidget(preview_view)

        # edit signal widgets
        self.current_column = ItemEditBox('Edit Signal', backend=self._backend)

        # function widget
        function_label = QtGui.QLabel("Common functions")
        self.function_tree = TreeDragWidget()
        self.function_tree.setMaximumWidth(2000)

        self.search_field = QtGui.QLineEdit('')
        self.search_field.setPlaceholderText('Search function name')

        function_tree_layout = QtGui.QVBoxLayout()
        function_tree_layout.setContentsMargins(0, 0, 0, 0)
        function_tree_layout.setSpacing(5)
        function_tree_layout.addWidget(function_label)
        function_tree_layout.addWidget(self.function_tree)
        function_tree_layout.addWidget(self.search_field)

        # List of available Signals names
        signals_label = QtGui.QLabel("Signals")
        self.column_name_list = SignalTableWidget()
        self.column_name_list.setMaximumWidth(2000)

        self.search_signal_field = QtGui.QLineEdit('')
        self.search_signal_field.setPlaceholderText('Search column name')

        signal_list_layout = QtGui.QVBoxLayout()
        signal_list_layout.setContentsMargins(0, 0, 0, 0)
        signal_list_layout.setSpacing(5)
        signal_list_layout.addWidget(signals_label)
        signal_list_layout.addWidget(self.column_name_list)
        signal_list_layout.addWidget(self.search_signal_field)

        functions_n_signals = QtGui.QWidget()
        function_signal_layout = QtGui.QHBoxLayout()
        function_signal_layout.setContentsMargins(0, 5, 0, 5)
        function_signal_layout.addLayout(function_tree_layout)
        function_signal_layout.addLayout(signal_list_layout)
        functions_n_signals.setLayout(function_signal_layout)

        # add widgets to global vsplitter
        vsplitter = QtGui.QSplitter()
        vsplitter.setOrientation(QtCore.Qt.Vertical)
        vsplitter.setContentsMargins(0, 0, 0, 0)
        vsplitter.addWidget(hsplitter)
        vsplitter.addWidget(self.current_column)
        vsplitter.addWidget(functions_n_signals)

        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(vsplitter)
        if self._multiple_input:
            same_length_gui = self._parameter_root['same_length_res'].gui()
            layout.addWidget(same_length_gui)
            same_length_gui.valueChanged.connect(self.status_changed)
        self.setLayout(layout)

        self.model_view.current_row_changed.connect(self.update_current_item)
        self.function_tree.itemDoubleClicked.connect(self.insert_function)
        self.column_name_list.itemDoubleClicked.connect(self.insert_signal)
        self.search_field.textEdited.connect(self.search_function)
        self.search_signal_field.textEdited.connect(self.search_signal)
        self.current_column.calc_field.insert_function.connect(
            self.format_function)
        self.model.data_ready.connect(self.status_changed)

    def init_gui_from_model(self):
        if not self.model.rowCount():
            self.model.add_item()

        if self.model_view.model().rowCount():
            selection_model = self.model_view.selectionModel()
            first_idx = self.model_view.model().index(0, 0)
            selection_model.select(first_idx,
                                   QtGui.QItemSelectionModel.ClearAndSelect |
                                   QtGui.QItemSelectionModel.Rows)

        # init input column names
        self.column_name_list.setRowCount(
            len(self.model.input_columns_and_types))

        for idx, (cname, dtype) in enumerate(
                self.model.input_columns_and_types):
            name_item = QtGui.QTableWidgetItem(cname)
            type_item = QtGui.QTableWidgetItem(dtype)
            for item in [name_item, type_item]:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.column_name_list.setItem(idx, 0, name_item)
            self.column_name_list.setItem(idx, 1, type_item)

        # init function tree
        init_tree(self.function_tree, self._backend)
        self.tree_head = self.function_tree.invisibleRootItem()

    def save_parameters(self):
        self.model.save_parameters()

    def cleanup(self):
        self.model.cleanup_preview_worker()

    @property
    def valid(self):
        status, self._status_message = self.model.validate()
        return status

    @property
    def status(self):
        if self._status_message:
            return '<p>{}</p>'.format(self._status_message)
        return ''

    def insert_signal(self, item):
        item = self.column_name_list.get_items()[item.row()]
        self.current_column.calc_field.insertPlainText("${%s}" % item.text())

    def insert_function(self, item):
        text = item.data(0, QtCore.Qt.UserRole)
        self.format_function(text)

    def format_function(self, text):
        selected_items = self.column_name_list.current_items()
        if text:
            if '${signal0}' in text:
                if len(selected_items):
                    item = selected_items[0]
                    signal = '${{{0}}}'.format(item.text())
                else:
                    signal = '${}'
                text = text.replace('${signal0}', signal)
            if '${signal1}' in text:
                if len(selected_items) >= 2:
                    item = selected_items[1]
                    signal = '${{{0}}}'.format(item.text())
                else:
                    signal = '${}'
                text = text.replace('${signal1}', signal)
            self.current_column.calc_field.insertPlainText(text)

    def update_current_item(self):
        item = self.model_view.current_item()
        self.current_column.set_item(item)

    def search_function(self):
        term = self.search_field.text()
        recursive_hide(self.tree_head, term)

    def search_signal(self):
        pattern = self.search_signal_field.text()

        items = self.column_name_list.get_items()
        item_names = [item.text() for item in items]
        filtered_item_indexes = fuzzy_list_filter(pattern, item_names)

        for row in range(len(items)):
            if row in filtered_item_indexes:
                self.column_name_list.setRowHidden(row, False)
            else:
                self.column_name_list.setRowHidden(row, True)
