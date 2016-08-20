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
With the considered node it is possible to convert the data types of a number
of selected columns in the incoming Table. In general, the columns in the
internal :ref:`Table` type can have the same data types that exist for numpy
arrays, except for numpy object type. For this node the list of available data
types to convert to is restricted.

The following data types are available for conversion:
    - bool
    - float
    - int
    - str
    - unicode
    - datetime


Converting strings to datetimes
-------------------------------
Converting a str/unicode column to datetime might require some extra thought if
the strings include time-zone information. The datetimes stored by Sympathy
have no time zone information (due to limitations in the underlying data
libraries), but Sympathy is able to use the time-zone information when creating
the datetime columns. This can be done in two different ways, which we call
"UTC" and "naive".

datetime (UTC)
##############
The option *datetime (UTC)* will calculate the UTC-time corresponding to each
datetime in the input column. This is especially useful when your data contains
datetimes from different time zones (a common reason for this is daylight
savings time), but when looking in the viewer, exports etc. the datetimes will
not be the same as in the input.

For example the string ``'2016-01-01T12:00:00+0100'`` will be stored as
``2016-01-01T11:00:00`` which is the corresponding UTC time.

There is currently no standard way of converting these UTC datetimes back to
the localized datetime strings with time-zone information.

datetime (naive)
################
The option *datetime (naive)* simply discards any time-zone information. This
corresponds pretty well to how we "naively" think of time when looking at a
clock on the wall.

For example the string ``'2016-01-01T12:00:00+0100'`` will be stored as
``2016-01-01T12:00:00``.
"""
import pytz
import dateutil.parser
from collections import defaultdict

import numpy as np

from sympathy.api import qt as qt_compat
QtCore = qt_compat.QtCore  # noqa
QtGui = qt_compat.import_module('QtGui')  # noqa
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api import exceptions
from sympathy.api import table


def _matplotlib_dates():
    from matplotlib import dates as _mpl_dates
    return _mpl_dates


def _str_to_datetime_utc(x, replace=False):
    try:
        dt = dateutil.parser.parse(x)
    except ValueError:
        raise exceptions.SyDataError(
            '"{}" is not a supported time format.'.format(x))

    if dt.tzinfo is None:
        return np.datetime64(pytz.UTC.localize(dt))

    if replace:
        return np.datetime64(dt.replace(tzinfo=pytz.UTC))

    return np.datetime64(dt)


def _str_to_datetime_naive(x):
    return _str_to_datetime_utc(x, replace=True)


def to_string(column):
    return np.vectorize(str)(column)


def to_unicode(column):
    return np.vectorize(unicode)(column)


def to_datetime_common(column):
    if column.dtype.kind == 'M':
        return column
    elif column.dtype.kind == 'f':
        return np.array([_matplotlib_dates().num2date(x)
                         for x in column.tolist()],
                        dtype='datetime64[us]')
    else:
        return None


def to_datetime_utc(column):
    result = to_datetime_common(column)
    if result is not None:
        return result
    return np.vectorize(_str_to_datetime_utc)(column).astype('datetime64[us]')


def to_datetime_naive(column):
    result = to_datetime_common(column)
    if result is not None:
        return result
    return np.vectorize(_str_to_datetime_naive)(column).astype(
        'datetime64[us]')


def to_int(column):
    return column.astype(np.int)


def atof(x):
    return np.float(x.replace(',', '.'))


def to_float(column):
    if column.dtype.kind == 'M':
        return np.array([_matplotlib_dates().date2num(x)
                         for x in column.tolist()])

    try:
        return column.astype(np.float)
    except ValueError:
        converted_array = np.vectorize(atof)(column)
        return converted_array


def to_bool(column):
    return np.greater_equal(column, 1).astype(np.bool)


TYPE_NAMES = {'b': 'bool',
              'f': 'float',
              'i': 'int',
              'S': 'str',
              'U': 'unicode',
              'Mu': 'datetime (UTC)',
              'Mn': 'datetime (naive)'}

CONVERSION_OLD_TYPES_NEW_TYPES = {
    'bool': 'b',
    'float': 'f',
    'int': 'i',
    'str': 'S',
    'unicode': 'U',
    'datetime': 'Mu'}

CONVERSIONS = {'b': defaultdict(lambda: to_bool),
               'f': defaultdict(lambda: to_float),
               'i': defaultdict(lambda: to_int),
               'S': defaultdict(lambda: to_string),
               'U': defaultdict(lambda: to_unicode),
               'Mu': defaultdict(lambda: to_datetime_utc),
               'Mn': defaultdict(lambda: to_datetime_naive)}


# def extract(column, dtype):
#     return (column, (dtype, CONVERSIONS))


def convert_table_base(input_table, output_table, conversion):
    """
    Convert table using convert_table with CONVERSIONS as only column
    conversion dictionary.

    Add data from input_table to output_table converting it according to
    conversion.
    """
    conversion_base = dict(((k, (v, CONVERSIONS))
                            for k, v in conversion.items()))
    return convert_table(input_table, output_table, conversion_base)


def convert_table(input_table, output_table, conversion, keep_other=True):
    """
    Add data from input_table to output_table converting it according to
    conversion.

    >>> input_table = table.File()
    >>> output_table = table.File()
    >>> input_table.set_column_from_array('col1', np.array([1.1]))
    >>> input_table.set_column_from_array('col2', np.array([1]))
    >>> input_table.set_column_from_array('col3', np.array(['hi']))
    >>> conversion = {'col1': ('i', CONVERSIONS), 'col2': ('b', CONVERSIONS)}
    >>> convert_table(input_table, output_table, conversion)
    >>> print str(input_table)
    col1 float64
    col2 int64
    col3 |S2
    >>> '{0:0.1f}'.format(output_table.get_column_to_array('col1')[0])
    '1.1'
    >>> output_table.get_column_to_array('col2')[0]
    True
    >>> output_table.get_column_to_array('col3')[0]
    'hi'
    """
    columns = input_table.column_names()
    converted_columns = conversion.keys()

    for column in columns:
        if column in converted_columns:
            # Convert column
            output_table.set_column_from_array(column, convert_column(
                input_table.get_column_to_array(column), conversion[column]))
        elif keep_other:
            # Copy column
            output_table.update_column(column, input_table)

        output_table.set_attributes(input_table.get_attributes())
        output_table.set_name(input_table.get_name())


def convert_column(column, conversion):
    """
    Convert column with conversion.
    Return converted column.
    """
    target, convert = conversion
    origin = column.dtype.kind
    return convert[target][origin](column)


class ConvertTableColumns(synode.Node):
    """
    Convert selected columns in Table to new specified data types.

    :Inputs:
        **port1** : Table
            Table with data.
    :Outputs:
        **port2** : Table
            Table with converted columns.
    :Configuration:
        **Select columns** :
            Select column to convert.
        **Select type** :
            Select type to convert selected column to.
        **Add** : button
            Add selected combination of type and columns to the Conversions
            window.
        **Remove** : button
            Remove selected item in Conversions window.
        **Preview** : button
            Test listed conversions in the Conversions window.
        **Conversions** :
            Visualise definded conversions to perform when node is executed.
    """

    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(c) 2013 System Engineering Software Society"
    version = '1.0'

    name = 'Convert columns in Table'
    description = 'Convert selected columns in Table to new data types.'
    nodeid = 'org.sysess.sympathy.data.table.converttablecolumns'
    icon = 'select_table_columns.svg'
    tags = Tags(Tag.DataProcessing.TransformData)

    inputs = Ports([Port.Table(
        'Input Table', name='port1', requiresdata=True)])
    outputs = Ports([Port.Table('Table with converted columns', name='port2')])

    parameters = synode.parameters()
    editor = synode.Util.selectionlist_editor('multi').value()
    editor['buttons'] = True
    editor['invertbutton'] = True
    parameters.set_list(
        'in_column_list', label='Select columns',
        description='Select the columns to use', value=[],
        editor=editor)
    parameters.set_list(
        'in_type_list', label='Select type',
        description='Select the type to use', value=[],
        editor=synode.Util.selectionlist_editor('single').value())
    parameters.set_list(
        'out_column_list', label='Convert columns',
        description='Selected columns to convert', value=[],
        editor=synode.Util.selectionlist_editor('multi').value())
    parameters.set_list(
        'out_type_list', label='Convert types',
        description='Selected types to use', value=[],
        editor=synode.Util.selectionlist_editor('multi').value())

    def update_parameters(self, old_params):
        for i, v in enumerate(old_params['out_type_list'].value):
            if v in CONVERSION_OLD_TYPES_NEW_TYPES:
                old_params['out_type_list'].value[i] = (
                    CONVERSION_OLD_TYPES_NEW_TYPES[v])

    def exec_parameter_view(self, node_context):
        input_table = node_context.input['port1']
        if not input_table.is_valid():
            input_table = table.File()

        return ConvertTableColumnsWidget(
            input_table, node_context.parameters)

    def execute(self, node_context):
        self.run(node_context.parameters, node_context.input['port1'],
                 node_context.output['port2'], True)

    def run(self, parameters, input_table, output_table, keep_other):
        columns = parameters['out_column_list'].value
        types = parameters['out_type_list'].value
        conversion = dict([(column, (dtype, CONVERSIONS))
                           for column, dtype in
                           zip(columns, types)])
        convert_table(input_table, output_table, conversion, keep_other)


class ConvertTablesColumns(ConvertTableColumns):
    name = 'Convert columns in Tables'
    description = 'Convert selected columns in Tables to new data types.'
    nodeid = 'org.sysess.sympathy.data.table.converttablescolumns'

    inputs = Ports([Port.Tables(
        'Input Table', name='port1', requiresdata=True)])
    outputs = Ports([Port.Tables(
        'Tables with converted columns', name='port2')])

    def exec_parameter_view(self, node_context):
        input_tables = node_context.input['port1']
        if not input_tables.is_valid():
            input_table = table.File()
        else:
            try:
                input_table = input_tables[0]
            except IndexError:
                input_table = table.File()

        return ConvertTableColumnsWidget(
            input_table, node_context.parameters)

    def execute(self, node_context):
        input_tables = node_context.input['port1']
        output_tables = node_context.output['port2']
        for input_table in input_tables:
            output_table = table.File()
            self.run(node_context.parameters, input_table, output_table, True)
            output_tables.append(output_table)


class ConvertTableColumnsWidget(QtGui.QWidget):
    def __init__(self, input_table, parameters, parent=None):
        super(ConvertTableColumnsWidget, self).__init__(parent)
        self._parameters = parameters
        self._input_table = input_table
        self._init_parameters()
        self._init_gui()
        self._connect_gui()

    def _init_parameters(self):
        self._convert_items = {}
        self._parameters['in_column_list'].value_names = []
        self._parameters['in_column_list'].value = []
        self._parameters['in_column_list'].list = (
            self._input_table.column_names())
        self._parameters['in_type_list'].list = TYPE_NAMES.values()
        self._parameters['in_type_list'].value_names = []
        self._parameters['in_type_list'].value = []

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        selection_hlayout = QtGui.QHBoxLayout()
        button_hlayout = QtGui.QHBoxLayout()

        self.add_button = QtGui.QPushButton('Add')
        self.remove_button = QtGui.QPushButton('Remove')
        self.preview_button = QtGui.QPushButton('Preview')

        self.type_list = self._parameters['in_type_list'].gui()
        self.column_list = self._parameters['in_column_list'].gui()
        self.convert_list = QtGui.QListWidget()

        self.convert_label = QtGui.QLabel('Conversions')
        self.preview_label = QtGui.QLabel('Not previewed')

        self.convert_list.setSelectionMode(
            QtGui.QAbstractItemView.ExtendedSelection)

        self.convert_list.setAlternatingRowColors(True)

        for column, dtype in zip(self._parameters['out_column_list'].value,
                                 self._parameters['out_type_list'].value):
            label = u'{dtype} / {column}'.format(
                column=column, dtype=TYPE_NAMES[dtype])
            item = QtGui.QListWidgetItem(label)
            self.convert_list.addItem(item)
            self._convert_items[column] = item

        selection_hlayout.addWidget(self.column_list)
        selection_hlayout.addWidget(self.type_list)

        button_hlayout.addWidget(self.add_button)
        button_hlayout.addWidget(self.remove_button)
        button_hlayout.addWidget(self.preview_button)
        button_hlayout.addWidget(self.preview_label)

        vlayout.addLayout(selection_hlayout)
        vlayout.addLayout(button_hlayout)
        vlayout.addWidget(self.convert_label)
        vlayout.addWidget(self.convert_list)

        self.setLayout(vlayout)

    def _connect_gui(self):
        self.add_button.clicked.connect(self.add)
        self.remove_button.clicked.connect(self.remove)
        self.preview_button.clicked.connect(self.preview)

    def add(self):
        columns = self._parameters['in_column_list'].value_names
        type_name = self._parameters['in_type_list'].selected
        dtype = None
        for k, v in TYPE_NAMES.items():
            if v == type_name:
                dtype = k
                break
        if dtype is None:
            return

        for column in columns:
            label = u'{dtype} / {column}'.format(
                column=column, dtype=type_name)

            if column in self._convert_items:
                item = self._convert_items[column]
                index = self.convert_list.row(item)
                self._parameters['out_column_list'].value[index] = column
                self._parameters['out_type_list'].value[index] = dtype
                item.setText(label)
            else:
                item = QtGui.QListWidgetItem(label)
                self._convert_items[column] = item
                self._parameters['out_column_list'].value.append(column)
                self._parameters['out_type_list'].value.append(dtype)
                self.convert_list.addItem(item)

    def remove(self):
        for item in self.convert_list.selectedItems():
            index = self.convert_list.row(item)
            column = self._parameters['out_column_list'].value[index]
            del self._convert_items[column]
            del self._parameters['out_column_list'].value[index]
            del self._parameters['out_type_list'].value[index]
            self.convert_list.takeItem(index)

    def preview(self):
        input_table = self._input_table
        output_table = table.File()
        node = ConvertTableColumns()
        try:
            node.run(
                self._parameters, input_table, output_table, False)
            self.preview_label.setText('Ok!')
            self.preview_label.setStyleSheet('QLabel { color : black; }')
        except:
            self.preview_label.setText('Failed.')
            self.preview_label.setStyleSheet('QLabel { color : red; }')
