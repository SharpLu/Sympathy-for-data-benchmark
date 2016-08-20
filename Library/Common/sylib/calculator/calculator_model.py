# Copyright (c) 2015, System Engineering Software Society
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
import os
import re
import datetime
import traceback

import six
import numpy as np
import pandas

from sympathy.api import node as synode
from sympathy.api import qt
from sylib.calculator import plugins
from sympathy.platform.exceptions import sywarn
from sympathy.typeutils import table
from sympathy.utils.dtypes import get_pretty_type

QtCore = qt.QtCore  # noqa
QtGui = qt.QtGui  # noqa


def line_parser(varname, calc, all_columns):
    """Make valid python code from the calculation string by replacing e.g.
    ${a} with col_0.

    Expands wilcards into multiple calculations. We support three cases:
      0: Only ever one match for all columns
      1: One with many matches, the rest with one
      2: All with the same number of matches

    Returns
    -------
    tuple
        A tuple with three elements:
            0. A dictionary mapping old column names to the new col_0 names.
            1. A list of calculations with replaced column names.
            2. A list of outgoing column names.

    Raises
    ------
    KeyError
        if a calculation uses a column name that isn't in all_columns.
    """
    if calc is None:
        return None, None, None
    columns = re.findall(r'\${([^{}]+)}', calc)
    outputs = []

    global col_ctr, column_names
    col_ctr = 0
    column_names = {}

    def replacer(match_):
        global col_ctr, column_names
        if isinstance(match_, six.string_types):
            match = match_
        else:
            match = match_.groups()[0]
        if match in column_names:
            name = column_names[match]
        else:
            name = 'col_{0}'.format(col_ctr)
            column_names[match] = name
            col_ctr += 1
        return name

    calcs = []
    filtered_columns = []
    for column in columns:
        filtered_column = [n for n in all_columns
                           if n == column]

        # Raise KeyError if there is no match
        if not filtered_column:
            raise KeyError(column)

        filtered_columns.append((column, filtered_column))
    lengths = set([len(match) for c, match in filtered_columns])
    unique_matches = sorted((tuple(x) for c, x in filtered_columns),
                            key=lambda m: len(m), reverse=True)

    match_case = -1
    if len(lengths) == 1:
        if min(lengths) == 1:
            match_case = 0
        else:
            match_case = 2
    elif len(lengths) == 2:
        if min(lengths) == 1:
            match_case = 1
        elif min(lengths) == max(lengths):
            if len(unique_matches) == 1:
                match_case = 2

    # Construct the replaced calculations
    if match_case > 0:
        col_name, match_columns = max(
            filtered_columns, key=lambda m: len(m[1]))
        for column in set(match_columns):
            function_call = calc.replace(
                '${{{0}}}'.format(col_name), replacer(column))
            function_call = re.sub(r'\${([^{}]+)}', replacer, function_call)
            calcs.append(function_call)
            outputs.append(varname.replace('*', column))
    else:
        if match_case == 0:
            function_call = re.sub(r'\${([^{}]+)}', replacer, calc)
            calcs.append(function_call)
            outputs.append(varname)
        elif match_case == -1:
            calcs.append(calc)
            outputs.append(varname)

    return column_names, calcs, outputs


def sort_calculation_queue(graph_unsorted):
    """
    Sort the calculation queue.

    Returns
    -------
    list
    """
    graph_sorted = []
    while graph_unsorted:
        acyclic = False
        for node, edges in graph_unsorted.items():
            for edge in edges:
                if edge in graph_unsorted:
                    break
            else:
                acyclic = True
                graph_unsorted.pop(node)
                graph_sorted.append(node)

        if not acyclic:
            raise RuntimeError('A cyclic dependency occurred')
    return graph_sorted[::-1]


def get_calculation_order(calc_list):
    original_order = [get_varname_and_calc(calc_line) for calc_line in
                      calc_list]
    calc_list = dict(original_order)
    original_order = [l[0] for l in original_order]
    graph_unsorted = {var: set() for var in calc_list.keys()}
    for var, calc in calc_list.items():
        columns = re.findall(r'\${([^{}]+)}', calc)
        for col in columns:
            if col in graph_unsorted and col != var:
                graph_unsorted[col].add(var)

    try:
        graph_sorted = sort_calculation_queue(graph_unsorted)
    except RuntimeError:
        sywarn('There are cyclic dependencies in your columns!')
        return [], []

    reverse_sorting = [graph_sorted.index(node) for node in original_order]
    calc_sorting = [original_order.index(node) for node in graph_sorted]
    return calc_sorting, reverse_sorting


def get_varname_and_calc(calc_line):
    var, calc = calc_line.split('=', 1)
    var = var.strip()
    varname_match = re.match(r'\${([^{}]+)}', var)
    if varname_match:
        varname = varname_match.group(1)
    else:
        # TODO: smarter way to choose backup varname
        varname = var
    calc = calc.strip()
    return varname, calc


def python_calculator(in_table, calc_text, extra_globals=None):
    varname, calc = get_varname_and_calc(calc_text)
    column_names, calcs, outputs = line_parser(
        varname, calc, in_table.column_names() + extra_globals.keys())
    variables = {}
    for old_name in column_names:
        if old_name in extra_globals:
            variables[column_names[old_name]] = extra_globals[old_name]
        else:
            variables[column_names[old_name]] = in_table.get_column_to_array(
                old_name)
    variables.update(extra_globals or {})

    output_data = []
    for calc, col_name in zip(calcs, outputs):
        # Add col_0, col_1, etc to global variables:
        output = advanced_eval(calc, variables)
        if not isinstance(output, np.ndarray):
            output = np.array([output])
        output_data.append((col_name, output))
    return output_data


def advanced_eval(calc, globals_dict=None):
    """
    Evaluate expression in a standardized python environment with a few
    imports:
     - datetime
     - numpy as np
     - os
     - pandas
     - re

    globals_dict argument can be used to extend the environment.
    """
    context = {'datetime': datetime,
               'np': np,
               'os': os,
               'pandas': pandas,
               're': re}
    if globals_dict:
        context.update(globals_dict)
    for plugin in plugins.available_plugins():
        context.update(plugin.globals_dict())

    return eval(calc, context, {})


class CalculatorModel(object):
    """Model"""

    def __init__(self, in_tables, parameters, backend='python',
                 preview_calculator=None, parent=None):
        self._in_tables = in_tables
        self._parameter_root = synode.parameters(parameters)
        self._preview_calculator = preview_calculator

        if self._in_tables.is_valid():
            columns = set()
            for in_table in self._in_tables:
                columns.update(in_table.column_names())
            column_names = sorted(columns, key=lambda s: s.lower())
        else:
            column_names = []
        self._parameter_root.set_list('column_names', column_names)

        self._line_value = ""
        self._calc_list = self._parameter_root['calc_list'].list
        self._column_name_list = self._parameter_root['column_names'].list

        self.same_length_res = self._parameter_root['same_length_res'].value
        self._same_length_res_gui = (
            self._parameter_root['same_length_res'].gui())

    def get_calc_line_value(self):
        return self._line_value

    def same_len_res(self):
        return self.same_length_res

    def get_same_length_res_gui(self):
        return self._same_length_res_gui

    def get_calc_list(self):
        return self._calc_list

    def get_preview_calculator(self):
        return self._preview_calculator

    def get_input(self):
        return self._in_tables

    def get_column_names(self):
        return self._column_name_list

    def set_show_func_value(self, value):
        self._parameter_root['show_func'].value = value

    def set_calc_line_value(self, value):
        self._line_value = value

    def set_calc_list(self, value):
        self._calc_list = value
        self._parameter_root['calc_list'].list = self._calc_list


class CalculatorCalculationItem(QtGui.QStandardItem):
    """
    A helper model item for showing the items in the calculation column.
    """

    def __init__(self, calculation, parent=None):
        super(CalculatorCalculationItem, self).__init__(calculation,
                                                        parnet=parent)
        self._valid = True
        self._is_computing = False

    @property
    def valid(self):
        return self._valid

    @valid.setter
    def valid(self, state):
        self._valid = bool(state)
        self.emitDataChanged()

    @property
    def is_computing(self):
        return self._is_computing

    @is_computing.setter
    def is_computing(self, state):
        self._is_computing = bool(state)
        self.emitDataChanged()

    def data(self, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.BackgroundRole:
            if not self._valid:
                return QtGui.QColor.fromRgb(228, 186, 189)  # redish color
            elif self.is_computing:
                return QtGui.QColor.fromRgb(254, 217, 166)  # yellowish color
            else:
                return None
        elif role == QtCore.Qt.ToolTipRole:
            return self.text()
        else:
            return super(CalculatorCalculationItem, self).data(role)


class CalculatorModelItem(QtGui.QStandardItem):
    """
    A model item for calculated columns.
    """

    def __init__(self, name, calculation='', calc_item=None, parent=None):
        super(CalculatorModelItem, self).__init__(parent=parent)
        self._is_valid = True
        self._calc_is_valid = True
        self._is_computing = False
        self._name = ''
        self._old_name = ''
        self._calculation = ''
        self.message = ''
        self._child_columns = set()
        self.used_columns = []
        self._attributes = {}
        self._column_data = np.array([])
        self._calc_item = calc_item

        self.name = name
        self.calculation = calculation

    def text(self):
        return self._name

    def data(self, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            return self.name
        elif role == QtCore.Qt.BackgroundRole:
            if not self.valid:
                return QtGui.QColor.fromRgb(228, 186, 189)  # redish color
            elif self.is_computing:
                return QtGui.QColor.fromRgb(254, 217, 166)  # yellowish color
            else:
                return None
        elif role == QtCore.Qt.ToolTipRole:
            text = '{0} = {1}'.format(self.name, self.calculation)

            if len(self.used_columns):
                text += '\n\nUsed columns:\n'
                text += '\n'.join(['- {}'.format(i) for i in self.used_columns])

            if len(self._child_columns):
                text += '\n\nDependent columns:\n'
                text += '\n'.join(['- {}'.format(i.name)
                                   for i in self._child_columns])
            return text
        else:
            return None

    def flags(self):
        return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled |
                QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsSelectable)

    @property
    def valid(self):
        return self._is_valid

    @valid.setter
    def valid(self, state):
        self._is_valid = bool(state)
        self.emitDataChanged()

    @property
    def calculation_valid(self):
        return self._calc_is_valid

    @calculation_valid.setter
    def calculation_valid(self, state):
        self._calc_is_valid = bool(state)
        self._calc_item.valid = self._calc_is_valid
        self.emitDataChanged()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._old_name = self._name
        self._name = name
        self.validate_name()

    @property
    def calculation(self):
        return self._calculation

    @calculation.setter
    def calculation(self, func):
        old_func = self._calculation
        self._calculation = func
        self.validate_calculation()
        if isinstance(self._calc_item, QtGui.QStandardItem):
            self._calc_item.setText(func)
        if self._calculation != old_func and self.model() is not None:
            self.model().recompute_item(self)

    @property
    def dependent_columns(self):
        return self._child_columns

    @property
    def column_data(self):
        return self._column_data

    @column_data.setter
    def column_data(self, data):
        self._column_data = data
        self.emitDataChanged()

    @property
    def is_computing(self):
        return self._is_computing

    @is_computing.setter
    def is_computing(self, state):
        self._is_computing = bool(state)
        self._calc_item.is_computing = self._is_computing
        self.emitDataChanged()

    @property
    def attributes(self):
        return self._attributes

    def set_attribute(self, name, value):
        self._attributes[name] = value
        self.emitDataChanged()

    def remove_attribute(self, name):
        self._attributes.pop(name)
        self.emitDataChanged()

    def validate(self):
        self.validate_name()
        self.validate_calculation()

    def validate_name(self):
        self._child_columns = set()
        if self.name == '':
            self.valid = False
        elif self.model() is not None:
            model = self.model()
            if self.name in model.get_other_column_names(self):
                self.valid = False
            model.reevaluate_items_after_name_change(self._old_name)
            items = model.reevaluate_items_after_name_change(self._name)
            for item in items:
                self.add_child(item)
            else:
                self.valid = True

    def validate_calculation(self):
        if self.model() is None:
            return
        if self.calculation == '':
            self.message = 'Empty calculation'
            self.calculation_valid = False
            return

        # parse calculation function
        column_names = re.findall(r'\${([^{}]+)}', self.calculation)
        # check if used columns are a subset of available ones
        is_subset = set(column_names).issubset(self.model().available_columns)
        if is_subset:
            self.message = ''
        else:
            self.message = 'Missing column names in input data!'
        self.calculation_valid = is_subset
        # add `self` to used_column items
        self.register_at_parent_items(column_names)
        # check if used columns are all valid
        for used_col in self.used_columns:
            item = self.model().get_item_by_name(used_col)
            if item is not None:
                if not item.calculation_valid:
                    self.calculation_valid = False
                    break
        # propagate validation to dependent columns
        for dep_item in self.dependent_columns:
            if self.calculation_valid:
                dep_item.validate_calculation()
            else:
                dep_item.calculation_valid = False

    def register_at_parent_items(self, used_columns):
        # remove `self` from previously used columns
        for old_used_col in self.used_columns:
            item = self.model().get_item_by_name(old_used_col)
            if isinstance(item, CalculatorModelItem):
                item.remove_child(self)
        self.used_columns = used_columns
        # add `self` to used columns
        all_column_names = self.model().column_names
        for used_col in self.used_columns:
            if used_col in all_column_names:
                item = self.model().get_item_by_name(used_col)
                if isinstance(item, CalculatorModelItem):
                    item.add_child(self)

        is_cycle, dependent_items = self.model().get_dependencies(self)
        self.calculation_valid = not is_cycle

    def add_child(self, child):
        if child is not self:
            self._child_columns.add(child)

    def remove_child(self, child):
        if child in self._child_columns:
            self._child_columns.remove(child)

    def __eq__(self, other):
        return self.index() == other.index()

    def __ne__(self, other):
        return self.index() != other.index()


class CalculatorItemModel(QtGui.QStandardItemModel):
    get_preview = QtCore.Signal(list)
    data_ready = QtCore.Signal()
    """
    Calculator Model.
    """
    def __init__(self, in_tables, parameters, backend='python',
                 preview_calculator=None, parent=None):
        """
        Initialize :class:CalculatorModel

        Parameters
        ----------
        in_tables : table.FileList
        parameters : dict
        backend : unicode or str
        preview_calculator : function or None
        parent : None or QtGui.QObject
        """
        super(CalculatorItemModel, self).__init__(parent=parent)

        self._in_tables = in_tables
        self._parameter_root = parameters
        self._backend = backend
        self._preview_calculator = preview_calculator
        self._calculation_queue = set()
        self._input_column_names_and_types = []

        if not self._in_tables.is_valid():
            self._in_tables = table.FileList()

        self.init_preview_worker()
        self.calc_timer = QtCore.QTimer()
        self.calc_timer.setInterval(1000)  # 1s timeout before calc runs
        self.calc_timer.setSingleShot(True)

        # connect signals
        self.itemChanged.connect(self.item_updated)
        self.calc_timer.timeout.connect(self.compute_items)

        # populate model with data from in_tables
        self.init_from_parameters()

    def init_from_parameters(self):
        input_column_names_and_types = set()
        for in_table in self._in_tables:
            for cname in in_table.column_names():
                dtype = in_table.get_column_to_array(cname).dtype
                dtype = get_pretty_type(dtype)
                input_column_names_and_types.add((cname, dtype))
        self._input_column_names_and_types = sorted(
            input_column_names_and_types, key=lambda s: s[0].lower())

        for item in self._parameter_root['calc_list'].list:
            name, calculation = item.split('=', 1)
            name = name.strip()
            if name.startswith('${') and name.endswith('}'):
                name = name[2:-1]
            self.add_item(name, calculation.strip())

        for item in self.get_items_gen():
            # item.validate()
            self.recompute_item(item)

    def init_preview_worker(self):
        table_filelist = self._in_tables
        if table_filelist.is_valid() and len(table_filelist) > 0:
            table_file = table_filelist[0]
        else:
            table_file = table.File()
        # create partial function
        prev_calc = self._preview_calculator
        self._worker_preview_calc = functools.partial(prev_calc, table_file)

        self._preview_thread = QtCore.QThread()
        self._preview_worker = CalculatorModelPreviewWorker(
            self._worker_preview_calc)
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_thread.finished.connect(self._preview_worker.deleteLater)
        self.get_preview.connect(self._preview_worker.create_preview_table)
        self._preview_worker.preview_ready.connect(self._update_item)
        self._preview_thread.start()

    def cleanup_preview_worker(self):
        self._preview_thread.quit()
        self._preview_thread.wait()

    def flags(self, index):
        if index.isValid():
            return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled |
                    QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsSelectable)
        else:
            return super(CalculatorItemModel, self).flags(index)

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def mimeTypes(self):
        return ['text/plain']

    def dropMimeData(self, mime_data, action, row, column, parent):
        if action == QtCore.Qt.IgnoreAction:
            return True
        if not mime_data.hasFormat('text/plain'):
            return False

        if row != -1:
            begin_row = row
        elif parent.isValid():
            begin_row = parent.row()
        else:
            begin_row = self.rowCount()

        encoded_data = mime_data.data('text/plain').data()
        item_names = re.findall(r'\${([^{}]+)}', encoded_data)
        for r, item_name in enumerate(item_names):
            self.insert_item(item_name, '${{{0}}}'.format(item_name),
                             begin_row + r)
        return True

    @property
    def input_tables(self):
        return self._in_tables

    @property
    def first_input_table(self):
        return self._in_tables[0]

    @property
    def column_names(self):
        return [self.item(r).name for r in range(self.rowCount())]

    @property
    def available_columns(self):
        input_column_names = [i[0] for i in self._input_column_names_and_types]
        all_columns = sorted(input_column_names + self.column_names,
                             key=lambda s: s.lower())
        return all_columns

    @property
    def input_columns_and_types(self):
        return self._input_column_names_and_types

    @property
    def input_column_names(self):
        return [i[0] for i in self.input_columns_and_types]

    def get_other_column_names(self, reference_item, only_valid=True):
        if only_valid:
            column_names = [item.name for item in self.get_items_gen() if
                            item is not reference_item and item.valid]
        else:
            column_names = [item.name for item in self.get_items_gen() if
                            item is not reference_item]
        return column_names

    def get_items_gen(self):
        return (self.item(row) for row in range(self.rowCount()))

    def get_item_by_name(self, name):
        items = self.findItems(name, flags=QtCore.Qt.MatchExactly, columns=0)
        if items:
            return items[0]

    def build_item(self, name='', calculation=''):
        calculation_item = CalculatorCalculationItem(calculation, parent=self)
        name_item = CalculatorModelItem(name, calculation, calculation_item,
                                        parent=self)
        return name_item, calculation_item

    def add_item(self, name=None, calculation=None):
        """Add a column to the model and the preview table."""
        if name is None:
            name = 'New Column {}'.format(self.rowCount())
        if calculation is None:
            calculation = ''
        item_row = self.build_item(name, calculation)
        self.appendRow(item_row)
        item_row[0].validate()
        self.reevaluate_items_after_name_change(item_row[0].name)
        if self.rowCount() < 2:
            self.setHeaderData(0, QtCore.Qt.Horizontal, 'Column name')
            self.setHeaderData(1, QtCore.Qt.Horizontal, 'Calculation')
        return item_row[0]

    def insert_item(self, name='', calculation='', row=0):
        item_row = self.build_item(name, calculation)
        self.insertRow(row, item_row)
        item_row[0].validate()
        self.reevaluate_items_after_name_change(item_row[0].name)
        return item_row[0]

    def copy_item(self, row):
        item = self.item(row, 0)
        new_item = self.insert_item('{} Copy'.format(item.name),
                                    item.calculation, row + 1)
        self.recompute_item(new_item)

    def remove_item(self, row):
        """Remove a column from the model."""
        item = self.item(row, 0)
        name = item.name
        for i in self.get_items_gen():
            i.remove_child(item)
        self.removeRow(row)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.reevaluate_items_after_name_change(name)

    def reevaluate_items_after_name_change(self, name):
        items_using_name = set()
        for item in self.get_items_gen():
            for col in item.used_columns:
                if name == col:
                    item.validate_calculation()
                    self.recompute_item(item)
                    items_using_name.add(item)
        return items_using_name

    def recompute_item(self, item):
        if isinstance(item, CalculatorModelItem) and item.calculation_valid:
            is_cycle, all_dependencies = self.get_dependencies(item)
            if not is_cycle:
                self.add_item_to_calculation_queue(item)
                for dep_item in all_dependencies:
                    dep_item.validate_calculation()
                    if dep_item.calculation_valid:
                        self.add_item_to_calculation_queue(dep_item)
                self.calc_timer.start()
            else:
                self.calc_timer.stop()
                self._calculation_queue = set()

    def add_item_to_calculation_queue(self, item):
        item.is_computing = True
        self._calculation_queue.add(item)

    def get_dependencies(self, item):
        """
        Find cycles in the item dependencies.

        Returns if a cycle is found (True) and all dependent items.

        Parameters
        ----------
        item : CalculatorModelItem
            The root item where to start searching.

        Returns
        -------
        bool
            True if a cycle was found.
        set
            Child items.

        """
        # build graph
        g = {i: tuple(i.dependent_columns) for i in self.get_items_gen()}

        path = set()
        visited = set()

        def visit(item):
            if item in visited:
                return False
            visited.add(item)
            path.add(item)
            for child in g.get(item, ()):
                if child in path or visit(child):
                    return True
            path.remove(item)
            return False

        return visit(item), visited

    def compute_items(self):
        input_column_names = [i[0] for i in self.input_columns_and_types
                              if i[0] not in self.column_names]
        try:
            graph_unsorted = {i: tuple(i.dependent_columns) for
                              i in self._calculation_queue}
            queue = sort_calculation_queue(graph_unsorted)
        except RuntimeError:
            sywarn('There are cyclic dependencies in your columns!')
            for item in self._calculation_queue:
                item.is_computing = False
                item.calculation_valid = False
            self._calculation_queue = set()
            return

        calculation_list = []
        for item in queue:
            # filter out input_column_names
            used_columns = [name for name in item.used_columns if name not
                            in input_column_names]
            used_items = [self.get_item_by_name(name) for name in used_columns]
            used_item_data = {i.name: i.column_data.copy() for i in
                              used_items if i is not None}
            used_item_data.pop(item.name, None)  # remove reference to itself
            calculation_list.append((item.name, item.calculation, item.row(),
                                     used_item_data))
        self._calculation_queue = set()
        self.get_preview.emit(calculation_list)

    @QtCore.Slot(int, unicode, np.ndarray, bool)
    def _update_item(self, column_idx, column_name, data, is_error):
        item = self.item(column_idx)
        item.is_computing = False
        # check if the data can be stored in a sytable
        try:
            dummy_output_table = table.File()
            dummy_output_table.set_column_from_array(item.name, data)
            item.column_data = data
            item.message = ''
        except Exception as e:
            item.message = e
            is_error = True
        item.calculation_valid = not is_error

    def check_item_messages(self):
        """Return first message of items."""
        for item in self.get_items_gen():
            if item.message:
                return item.message
        return ''

    def check_column_length(self):
        """Return True if all columns have the same length."""
        col_lens = np.array([len(i.column_data) for i in self.get_items_gen()])
        if len(col_lens):
            return np.all((col_lens - col_lens[0]) == 0)
        return True

    def check_valid_names(self):
        """Return True if all column names are valid."""
        col_names_valid = [i.valid for i in self.get_items_gen()]
        return np.all(col_names_valid)

    def check_calculation(self):
        """Return True if all column names are valid."""
        calculations_valid = [i.calculation_valid
                              for i in self.get_items_gen()]
        return np.all(calculations_valid)

    def validate(self):
        item_message = self.check_item_messages()
        if item_message:
            return False, item_message
        elif not self.check_valid_names():
            return False, 'Some column names are invalid'
        elif not self.input_columns_and_types:
            return True, 'No input data available'
        elif not self.check_calculation():
            return False, 'One or more calculations are invalid'
        elif (not self.check_column_length() and
                self._parameter_root['same_length_res'].value):
            return False, 'The calculated columns do not have the same length'
        return True, ''

    def item_updated(self):
        self.data_ready.emit()

    def save_parameters(self):
        calc_list = ['${{{}}} = {}'.format(item.name, item.calculation) for
                     item in self.get_items_gen()]
        self._parameter_root['calc_list'].list = calc_list


class CalculatorModelPreviewWorker(QtCore.QObject):
    preview_ready = QtCore.Signal(int, unicode, np.ndarray, bool)

    def __init__(self, calc_function):
        super(CalculatorModelPreviewWorker, self).__init__()
        self._calc_function = calc_function

    def create_preview_table(self, *args):
        outputs = {}
        calc_list = args[0]

        for name, func, col_idx, extra_columns in calc_list:
            is_error_column = False
            # update extra data with previously computed column data
            extra_columns.update(outputs)
            try:
                calc = "${" + name + "}" + " = " + func
                calc_res = self._calc_function(calc, extra_columns)
                col_name = calc_res[0][0]
                result = calc_res[0][1]
                outputs[col_name] = result
            except Exception as e:
                # Show the exception in the preview
                error_lines = traceback.format_exception_only(type(e), e)
                try:
                    col_name = calc.split("=")[0].strip()
                    if (col_name.startswith("${") and
                            col_name.endswith("}") and len(col_name) >= 4):
                        col_name = col_name[2:-1]
                except:
                    col_name = 'Calc {0}'.format(col_idx)
                result = np.array(error_lines[-1:])
                is_error_column = True
            self.preview_ready.emit(col_idx, col_name, result, is_error_column)


class PreviewModel(QtCore.QAbstractTableModel):
    def __init__(self, source_model, parent=None):
        super(PreviewModel, self).__init__(parent=parent)

        assert(isinstance(source_model, CalculatorItemModel))
        self.source_model = source_model

        self.source_model.dataChanged.connect(self.update_model)
        self.source_model.data_ready.connect(self.modelReset)

    def update_model(self, topleft_index, bottomright_index):
        if topleft_index.parent() == bottomright_index.parent():
            self.modelReset.emit()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal:
            item = self.source_model.item(section, 0)
            if role == QtCore.Qt.DisplayRole:
                return item.name
            elif role == QtCore.Qt.ToolTipRole:
                return item.name
            elif role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignLeft
            elif role == QtCore.Qt.BackgroundRole:
                if item.valid:
                    return None
                else:
                    return QtGui.QColor.fromRgb(228, 186, 189)  # redish color
        return super(PreviewModel, self).headerData(section, orientation, role)

    def rowCount(self, qmodel_index=None):
        source_items = self.source_model.get_items_gen()
        columns_len = [len(item._column_data) for item in source_items]
        if columns_len:
            row_count = max(columns_len)
        else:
            row_count = 0
        return row_count

    def columnCount(self, qmodel_index=None):
        return self.source_model.rowCount()

    def data(self, qmodel_index, role=QtCore.Qt.DisplayRole):
        if not qmodel_index.isValid():
            return None
        row = qmodel_index.row()
        col = qmodel_index.column()
        column_item = self.source_model.item(col, 0)
        data = column_item._column_data
        display_data = data[row] if row < len(data) else None
        if role == QtCore.Qt.DisplayRole:
            return six.text_type(display_data)
        elif role == QtCore.Qt.ToolTipRole:
            if display_data is not None:
                return six.text_type(display_data)
            else:
                return ''
        elif role == QtCore.Qt.BackgroundRole:
            if not column_item.calculation_valid:
                return QtGui.QColor.fromRgb(251, 180, 174)  # redish color
            elif column_item.is_computing:
                return QtGui.QColor.fromRgb(254, 217, 166)  # yellowish color
            else:
                return None
        return None

    def flags(self, qmodel_index):
        return (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsDragEnabled)
