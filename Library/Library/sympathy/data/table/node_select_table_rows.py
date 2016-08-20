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
In the standard library there exist three nodes where rows in one or several
Tables can be selected with help of defind constraint relations. The Tables in
the outputs will have lesser or equal number of rows as the incoming Tables.

The rows to select are determined by constraint relations that are applied
to one or many selected columns in the Table. The intersection of the results
from the applied relations is used to filter the rows of the whole incoming
Table.

The following operators are recognised by the node:
    - equal (==)
    - less than (<)
    - less than or equal (<=)
    - greater than (>)
    - greater than or equal (>=)
    - not equal (!=).

For two of the nodes, :ref:`Select rows in Table` and
:ref:`Select rows in Tables`, the configuration GUI is used to
set up a single constraint relation that can be applied to one or many
columns of the incoming Table.

In the third node, :ref:`Select rows in Table with Table`, the constraint
relations are predefined in an additional incoming Table. Three columns in
this Table includes column names, comparison operators and constraint values,
respectively. The comparison operators that can be used are listed above and
remember to use the string expressions, as an example use equal instead of ==.
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)
import collections
import numpy as np
from six import text_type

from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api import qt as qt_compat
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api import node_helper
from sympathy.api.exceptions import SyConfigurationError
from sylib import util

QtGui = qt_compat.import_module('QtGui')  # noqa
QtCore = qt_compat.QtCore  # noqa


comparisons = collections.OrderedDict([
    ('equal', '=='),
    ('less than', '<'),
    ('less than or equal', '<='),
    ('greater than', '>'),
    ('greater than or equal', '>='),
    ('not equal', '!=')])


def get_predicate(relation, constraint):
    comparison = comparisons[relation]
    predicate_fn = 'lambda x: x {} {}'.format(comparison, constraint)
    ctx = {}
    try:
        constraint_value = util.base_eval(constraint, {'x': None})
    except NameError:
        # Assume that the constraint is a string.
        constraint_value = constraint
        ctx = {'constraint_value': constraint_value}
        predicate_fn = 'lambda x: x {0} constraint_value'.format(
            comparison)
    except:
        # Assume that the constraint depends on x.
        pass
    return util.base_eval(predicate_fn, ctx)


def get_parameter_predicate(parameters):
    if parameters['use_custom_predicate'].value:
        return util.base_eval(parameters['predicate'].value)
    return get_predicate(parameters['relation'].selected,
                         parameters['constraint'].value)


def filter_rows(in_table, parameters):
    columns = parameters['columns'].value_names
    predicate = get_parameter_predicate(parameters)
    nbr_rows = in_table.number_of_rows()

    selection = np.ones(nbr_rows, dtype=bool)
    if nbr_rows:
        try:
            for column_name in columns:
                selection = selection & predicate(
                    in_table.get_column_to_series(column_name))
        except TypeError:
            raise SyConfigurationError(
                'Value error in the filter constraint or custom filter ' +
                'expression. Please review the configuration.')

    return selection


def filter_rows_memopt(in_table, out_table, parameters):
    selection = filter_rows(in_table, parameters)
    out_table.update(in_table[np.array(selection)])


def get_selection_from_context(node_context):
    column_index = int(node_context.parameters['column']['value'][0])
    column_name = text_type(
        node_context.parameters['column']['list'][column_index])

    relation_index = int(
        node_context.parameters['relation']['value'][0])
    relation = text_type(
        node_context.parameters['relation']['list'][relation_index])

    constraint = node_context.parameters['constraint']['value']
    if constraint.isdigit():
        constraint = float(constraint)
    else:
        constraint = text_type(constraint)
    return column_name, relation, constraint


class SelectRowsWidget(QtGui.QWidget):
    def __init__(self, in_table, parameters, parent=None):
        super(SelectRowsWidget, self).__init__(parent)
        self._in_table = in_table
        self._parameters = parameters
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()

        self._use_custom_predicate_pw = (
            self._parameters['use_custom_predicate'].gui())
        self._predicate_pwidget = (
            self._parameters['predicate'].gui())

        preview_button = QtGui.QPushButton("Preview")
        self._preview_table = QtGui.QTableWidget()
        limit_label = QtGui.QLabel('Previewed rows:')
        self.limit_spinbox = QtGui.QSpinBox()
        preview_layout = QtGui.QHBoxLayout()
        preview_layout.addWidget(preview_button)
        preview_layout.addWidget(limit_label)
        preview_layout.addWidget(self.limit_spinbox)

        vlayout.addWidget(self._parameters['columns'].gui())
        self._relation = self._parameters['relation'].gui()
        vlayout.addWidget(self._relation)
        self._constraint = self._parameters['constraint'].gui()
        vlayout.addWidget(self._constraint)

        vlayout.addWidget(self._use_custom_predicate_pw)
        vlayout.addWidget(self._predicate_pwidget)
        vlayout.addLayout(preview_layout)
        vlayout.addWidget(self._preview_table)

        self.limit_spinbox.setMinimum(1)
        self.limit_spinbox.setMaximum(1000)
        self.limit_spinbox.setValue(self._parameters['limit'].value)

        self._post_init_gui_from_parameters()

        self.setLayout(vlayout)

        self._relation.editor().currentIndexChanged[int].connect(
            self._relation_changed)
        self._constraint.valueChanged[text_type].connect(
            self._constraint_changed)
        self._use_custom_predicate_pw.stateChanged[int].connect(
            self._use_custom_predicate_changed)
        preview_button.clicked[bool].connect(
            self._preview_clicked)
        self.limit_spinbox.valueChanged[int].connect(self._limit)
        self._predicate_pwidget.valueChanged[str].connect(
            self._predicate_changed)

    def _post_init_gui_from_parameters(self):
        self._use_custom_predicate_changed()
        relation = self._parameters['relation'].selected
        constraint = self._parameters['constraint'].value
        if not self._parameters['use_custom_predicate'].value:
            self._set_predicate(relation, constraint)

    def _set_predicate(self, relation, constraint):
        self._predicate_pwidget.set_value(
            'lambda x: x {0} {1}'.format(comparisons[relation], constraint))

    def _relation_changed(self, index):
        relation = self._parameters['relation'].selected
        constraint = self._parameters['constraint'].value
        self._set_predicate(relation, constraint)

    def _constraint_changed(self, constraint):
        relation = (
            self._parameters['relation'].selected)
        self._set_predicate(relation, constraint)

    def _use_custom_predicate_changed(self):
        use_custom_predicate = (
            self._parameters['use_custom_predicate'].value)
        self._constraint.setEnabled(not use_custom_predicate)
        self._relation.setEnabled(not use_custom_predicate)
        self._predicate_pwidget.setEnabled(use_custom_predicate)

    def _predicate_changed(self):
        color = QtGui.QColor(0, 0, 0, 0)
        try:
            get_parameter_predicate(self._parameters)
        except SyntaxError:
            color = QtCore.Qt.red
        palette = self._predicate_pwidget.palette()
        palette.setColor(self._predicate_pwidget.backgroundRole(), color)
        self._predicate_pwidget.setPalette(palette)

    def _limit(self, value):
        self._parameters['limit'].value = int(value)

    def _preview_clicked(self):
        try:
            in_table = self._in_table['Input']
        except KeyError:
            in_table = None
        if in_table is None or in_table.is_empty():
            self._preview_table.clear()
            return

        rows = min(in_table.number_of_rows(), self._parameters['limit'].value)
        col_names = in_table.column_names()
        cols = in_table.number_of_columns()
        self._preview_table.clear()
        out_table = table.File()
        try:
            self._preview_table.setColumnCount(cols)
            self._preview_table.setRowCount(rows)
            self._preview_table.setHorizontalHeaderLabels(col_names)
            filter_rows_memopt(in_table, out_table, self._parameters)

            for col, col_name in enumerate(col_names):
                for row, data in zip(
                        range(rows), out_table.get_column_to_array(col_name)):
                    self._preview_table.setItem(
                        row, col, QtGui.QTableWidgetItem(text_type(data)))
        except SyntaxError:
            self._preview_table.setColumnCount(1)
            self._preview_table.setRowCount(1)
            self._preview_table.setItem(
                0, 0, QtGui.QTableWidgetItem('Invalid filter!'))


class SelectRowsOperation(node_helper.TableOperation):
    """
    Select rows in Tables by applying a comparison relation to a number
    columns in the incoming Tables.

    :Inputs:
        **TableInput** : Tables
            Tables with data.
    :Outputs:
        **TableOutput** : Tables
            Tables with the result from the selection of rows. There will be
            lesser or equal number of rows compared to the incoming Tables.
            The number of columns is the same.
    :Configuration:
        **Columns for comparison relations** :
            Select columns for comparison relation.
        **Comparison operator**:
            Select comparison operator for relation.
        **Filter constraint** :
            Specify constraint value for comparison relation.
        **Use custom filter** :
            Select if one would like to use custom filter.
        **Custom filter** :
            Write a custom filter as a Python lambda function.
        **Preview** : button
            When pressed the effects of the defined comparison relation is
            calculated and visualised in preview window.
        **Preview window** :
            Visualisation of the effects of the defined comparison relation.
    :Ref. nodes: :ref:`Select rows in Table` and
                 :ref:`Select rows in Table with Table`
    """

    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2014 System Engineering Software Society"
    version = '1.1'
    description = 'Reduction of rows in Table according to specified filter.'

    icon = 'select_table_rows.svg'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = ['Input']
    outputs = ['Output']
    has_custom_widget = True

    @staticmethod
    def get_parameters(parameter_group):
        editor = synode.Util.selectionlist_editor('multi').value()
        editor['filter'] = True
        parameter_group.set_list(
            'columns', label='Columns to filter',
            description='Columns to filter',
            editor=editor)

        parameter_group.set_list(
            'relation', plist=comparisons.keys(),
            label='Relation',
            description='Relation to use as constraint',
            editor=synode.Util.combo_editor().value())

        parameter_group.set_string(
            'constraint', label='Filter constraint',
            description='Value to use as constraint',
            value='x')

        parameter_group.set_boolean(
            'use_custom_predicate', label='Use custom filter',
            description='Write a custom predicate')

        parameter_group.set_string(
            'predicate', label='Custom filter',
            description='Filter function')

        parameter_group.set_integer(
            'limit', label='Preview rows', description='Rows to display',
            value=100)

    def custom_widget(self, in_table, parameters):
        return SelectRowsWidget(in_table, parameters)

    def adjust_table_parameters(self, in_table, parameters):
        columns = []
        try:
            if in_table['Input'].is_valid():
                input_table = in_table['Input']
                columns = input_table.column_names()
        except KeyError:
            columns = []
        parameters['columns'].list = sorted(columns)

    def execute_table(self, in_table, out_table, parameters):
        """Execute"""
        in_table = in_table['Input']
        if not in_table.is_empty():
            out_table = out_table['Output']
            try:
                filter_rows_memopt(in_table, out_table, parameters)
            except (SyntaxError, TypeError):
                raise SyConfigurationError(
                    'Value error in the filter constraint or custom filter ' +
                    'expression. Please review the configuration.')

            out_table.set_table_attributes(in_table.get_table_attributes())
            out_table.set_name(in_table.get_name())


SelectTableRows = node_helper.table_node_factory(
    b'SelectTableRows', SelectRowsOperation,
    'Select rows in Table',
    'org.sysess.sympathy.data.table.selecttablerows')


SelectTablesRows = node_helper.tables_node_factory(
    b'SelectTablesRows', SelectRowsOperation,
    'Select rows in Tables',
    'org.sysess.sympathy.data.table.selecttablerowss')


SelectADAFsRows = node_helper.adafs_node_factory(
    b'SelectADAFsRows', SelectRowsOperation,
    'Select rows in ADAFs',
    'org.sysess.sympathy.data.table.selectadafrows', 'Time series')


class SelectTableRowsFromTable(synode.Node):
    """
    Select rows in Table by using an additional Table with predefined
    comparison relations.

    :Inputs:
        **Selection** : Table
            Table with three columns that defines a set of comparison
            relations. Each row in the set will set up a comparison relation
            with a column name, a comparison operator and a constraint value.
        **TableInput** : Table
            Table with the data.
    :Outputs:
        **TableOutput** : Table
            Table with the result from the selection of rows. There will be
            lesser or equal number of rows compared to the TableInput. The
            number of columns is the same.
    :Configuration:
        **Column with columns names**
            Select column in the Selection Table that includes listed
            column names.
        **Column with comparison operators**
            Select column in the Selection Table that includes listed
            comparison operators.
        **Column with constraint values**
            Select column in the Selection Table that includes listed
            constraint values.
    :Ref. nodes: :ref:`Select rows in Table` and :ref:`Select rows in Tables`
    """

    name = 'Select rows in Table with Table'
    description = ('Select rows in Table by using an additional selection '
                   'Table with predefined comparison relations.')
    icon = 'select_table_rows.svg'

    nodeid = 'org.sysess.sympathy.data.table.selecttablerowsfromtable'
    author = 'Greger Cronquist <greger.cronquist@sysess.org>'
    copyright = '(c) 2013 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.Select)

    parameters = synode.parameters()

    parameters.set_list(
        'column',
        label="Column with column names",
        description=('Select column in the selection Table that '
                     'includes listed column names.'),
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'relation',
        label="Column with comparison operators",
        description=('Select column in the selection Table that '
                     'includes listed comparison operators.'),
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'constraint',
        label="Column with constraint values",
        description=('Select column in the selection Table that '
                     'includes listed constraint values.'),
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'reduction', label="Reduction:",
        plist=['all', 'any'], value=[0],
        description=(
            'If there are multiple selection criteria, do ALL of them need to '
            'be fulfilled for a data row to be selected, or is it enough that '
            'ANY single criterion is fulfilled?'),
        editor=synode.Util.combo_editor().value())

    inputs = Ports([Port.Table('Selection', name='port1'),
                    Port.Table('Input Table', name='port2')])
    outputs = Ports([Port.Table('Table with rows in Selection', name='port1')])

    def adjust_parameters(self, node_context):
        input_table = node_context.input[0]
        columns = []
        if input_table.is_valid():
            columns = sorted(input_table.column_names())

        parameters = node_context.parameters
        len_columns = len(columns)
        selected_column = parameters['column'].selected

        column_value = [0] if len_columns > 0 else None

        if selected_column in columns:
            column_value = [columns.index(selected_column)]

        parameters.set_list(
            'column', columns,
            label="Column with column names",
            description=('Select column in the selection Table that '
                         'includes listed column names.'),
            value=column_value,
            editor=synode.Util.combo_editor().value())

        selected_relation = parameters['relation'].selected
        relation_value = [1] if len_columns > 1 else None

        if selected_relation in columns:
            relation_value = [columns.index(selected_relation)]

        parameters.set_list(
            'relation', columns,
            label="Column with comparison operators",
            description=('Select column in the selection Table that '
                         'includes listed comparison operators.'),
            value=relation_value,
            editor=synode.Util.combo_editor().value())

        selected_constraint = parameters['constraint'].selected
        constraint_value = [2] if len_columns > 2 else None

        if selected_constraint in columns:
            constraint_value = [columns.index(selected_constraint)]

        parameters.set_list(
            'constraint', columns,
            label="Column with constraint values",
            description=('Select column in the selection Table that '
                         'includes listed constraint values.'),
            value=constraint_value,
            editor=synode.Util.combo_editor().value())

        return node_context

    def _generate_selection(self, node_context):
        for param in ['column', 'relation', 'constraint']:
            try:
                assert(self._parameters[param].selected)
            except AssertionError:
                raise SyConfigurationError('Check configuration parameters.')

        tablefile = node_context.input['port1']
        selection = tablefile.to_dataframe()

        column_names = selection[self._parameters['column'].selected]
        relations = selection[self._parameters['relation'].selected]
        constraints = selection[self._parameters['constraint'].selected]
        return zip(column_names, relations, constraints)

    def _filter_single_file(self, tablefile, node_context):
        """Return dataframe with selected rows."""
        indices = []

        for column_name, relation, constraint in self._generate_selection(
                node_context):

            indices.append(get_predicate(relation, constraint)(
                tablefile.get_column_to_array(column_name)))

        if self._parameters['reduction'].selected == 'any':
            index = np.logical_or.reduce(indices)
        else:
            index = np.logical_and.reduce(indices)

        filtered_file = table.File()
        for cname in tablefile.column_names():
            filtered_file.set_column_from_array(
                cname, tablefile.get_column_to_array(cname)[index])

        filtered_file.set_attributes(tablefile.get_attributes())
        return filtered_file

    def execute(self, node_context):
        """Execute"""
        self._parameters = node_context.parameters

        tablefile = node_context.input['port2']
        if tablefile.is_empty():
            return
        if node_context.input['port1'].is_empty():
            node_context.output['port1'].source(tablefile)
            return
        filtered_table = self._filter_single_file(tablefile, node_context)
        node_context.output['port1'].source(filtered_table)


class SelectTablesRowsFromTable(SelectTableRowsFromTable):
    """
    Select rows in Table by using an additional Table with predefined
    comparison relations.

    :Ref. nodes: :ref:`Select rows in Table with Table`
    """

    name = 'Select rows in Tables with Table'
    description = ('Select rows in Tables by using an additional selection '
                   'Table with predefined comparison relations.')

    nodeid = 'org.sysess.sympathy.data.table.selecttablesrowsfromtable'

    inputs = Ports([Port.Table('Selection', name='port1'),
                    Port.Tables('Input Tables', name='port2')])
    outputs = Ports([Port.Tables(
        'Tables with rows in Selection', name='port1')])

    def execute(self, node_context):
        self._parameters = node_context.parameters

        input_list = node_context.input['port2']
        output_list = node_context.output['port1']

        for tablefile in input_list:
            filtered_table = self._filter_single_file(tablefile, node_context)
            output_list.append(filtered_table)
