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
Slice the rows in Tables or elements in lists of Tables or ADAFs.

The slice pattern is expressed with standard Python syntax, [start:stop:step].
See example below to get a clear view how it works for a list.
::

    >>> li = ['elem0', 'elem1', 'elem2', 'elem3', 'elem4']
    >>> li[1:3]
    ['elem1', 'elem2']
    >>> li[1:-1]
    ['elem1', 'elem2', 'elem3']
    >>> li[0:3]
    ['elem0', 'elem1', 'elem2']
    >>> li[:3]
    ['elem0', 'elem1', 'elem2']
    >>> li[3:]
    ['elem3', 'elem4']
    >>> li[:]
    ['elem0', 'elem1', 'elem2', 'elem3', 'elem4']
    >>> li[::2]
    ['elem0', 'elem2', 'elem4']
    >>> li[:4:2]
    ['elem0', 'elem2']
    >>> li[1::2]
    ['elem1', 'elem3']
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)
from six import text_type
import numpy
import re
import traceback

from sympathy.api import qt as qt_compat
from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api import ParameterView
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import NoDataError
QtGui = qt_compat.import_module('QtGui')  # noqa


class SliceError(Exception):
    pass


class GetSlice(object):

    def __getitem__(self, index):
        return index

    @staticmethod
    def from_string(string):
        """
        Construct a slice object from index string.

        >>> GetSlice.from_string('[:]')
        slice(None, None, None)

        >>> GetSlice.from_string('[:1:]')
        slice(None, 1, None)

        >>> GetSlice.from_string('[::1]')
        slice(None, None, 1)

        >>> GetSlice.from_string('[0:-1:-1]')
        slice(0, -1, -1)
        """
        # Compact but insecure method, mitigated by limiting characters.
        if re.match(r'\[[\[\]0-9:, -]*\]', string):
            try:
                return eval('GetSlice(){}'.format(string))
            except SyntaxError:
                pass

    @staticmethod
    def valid_string(string, dims=2, allow_int=True):
        """Validates input string index and returns true if the index was
        valid.
        """
        index = GetSlice.from_string(string)
        if index or index == 0:
            if not allow_int and isinstance(index, int):
                return False
            return len(index) <= dims if isinstance(index, tuple) else True
        else:
            return False


def slice_base_parameters():
    parameters = synode.parameters()
    parameters.set_string('slice', value='[:]')
    parameters.set_integer('limit', value=100)
    return parameters


class SliceDataTable(synode.Node):
    """
    Slice rows in Table.

    :Inputs:
        **InTable** : Table
            Table with data.
    :Outputs:
        **OutTable** : Table
            Table consisting of the rows that been sliced out from the
            incoming Table according to the defined pattern. The number
            of columns are conserved during the slice operation.
    :Configuration:
        **Slice**
            Use standard Python syntax to define pattern for slice operation,
            [start:stop:step].
        **Limit preview to**
            Specify the maximum number of rows in the preview table.
        **Preview** : Button
            Push to visualise the effect of the defined slice.
    :Opposite node:
    :Ref. nodes: :ref:`Slice data Tables`
    """

    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    name = 'Slice data Table'
    nodeid = 'org.sysess.sympathy.slice.slicedatatable'
    version = '1.0'
    icon = 'select_table_rows.svg'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([Port.Table('Input Table', name='port1')])
    outputs = Ports([Port.Table('Sliced output Table', name='port2')])

    parameters = slice_base_parameters()

    def execute(self, node_context):
        itable = node_context.input['port1']
        otable = node_context.output['port2']
        index = node_context.parameters['slice'].value
        slice_index = GetSlice.from_string(index)

        otable.update(itable[slice_index])
        otable.set_name(itable.get_name())
        otable.set_table_attributes(itable.get_table_attributes())

    def verify_parameters(self, node_context):
        return GetSlice.valid_string(node_context.parameters['slice'].value)

    def exec_parameter_view(self, node_context):
        itable = node_context.input['port1']
        if not itable.is_valid():
            itable = None
        return SliceWidget(node_context, itable)


class SliceDataTables(synode.Node):
    """
    Slice rows in Tables - all Tables are sliced in the same way.

    :Inputs:
        **InTable** : Tables
            Tables with data.
    :Outputs:
        **OutTable** : Tables
            Tables consisting of the rows that been sliced out from the
            incoming Tables according to the defined pattern. The number
            of columns are conserved during the slice operation.
    :Configuration:
        **Slice**
            Use standard Python syntax to define pattern for slice operation,
            [start:stop:step].
        **Limit preview to**
            Specify the maximum number of rows in the preview table.
        **Preview** : Button
            Push to visualise the effect of the defined slice.
    :Opposite node:
    :Ref. nodes: :ref:`Slice data Table`
    """

    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    name = 'Slice data Tables'
    nodeid = 'org.sysess.sympathy.slice.slicedatatables'
    version = '1.0'
    icon = 'select_table_rows.svg'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([Port.Tables('Input Tables', name='port1')])
    outputs = Ports([Port.Tables('Sliced output Tables', name='port2')])

    parameters = slice_base_parameters()
    parameters.set_integer('group_index', value=0)

    def execute(self, node_context):
        itables = node_context.input['port1']
        otables = node_context.output['port2']
        index = node_context.parameters['slice'].value
        slice_index = GetSlice.from_string(index)
        for itable in itables:
            otable = itable[slice_index]
            otable.set_name(itable.get_name())
            otable.set_table_attributes(itable.get_table_attributes())
            otables.append(otable)

    def verify_parameters(self, node_context):
        return GetSlice.valid_string(node_context.parameters['slice'].value)

    def exec_parameter_view(self, node_context):
        itables = node_context.input['port1']
        return SlicesWidget(node_context, itables)


class SliceWidget(ParameterView):

    def __init__(self, node_context, itable, dims=2, allow_int=True,
                 parent=None):
        super(SliceWidget, self).__init__(parent=parent)
        self._node_context = node_context
        self._itable = itable
        self._parameters = node_context.parameters
        self._dims = dims
        self._allow_int = allow_int
        self._init_gui()
        self._connect_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        limit_hlayout = QtGui.QHBoxLayout()

        self.slice_label = QtGui.QLabel('Slice <I>[start:stop:step]</I>')
        self.slice_lineedit = QtGui.QLineEdit()
        self.limit_label = QtGui.QLabel('Limit preview to:')
        self.limit_spinbox = QtGui.QSpinBox()
        self.preview_button = QtGui.QPushButton('Preview')
        self.preview_table = QtGui.QTableWidget()

        limit_hlayout.addWidget(self.limit_label)
        limit_hlayout.addWidget(self.limit_spinbox)

        vlayout.addWidget(self.slice_label)
        vlayout.addWidget(self.slice_lineedit)
        vlayout.addLayout(limit_hlayout)
        vlayout.addWidget(self.preview_button)
        vlayout.addWidget(self.preview_table)

        self.limit_spinbox.setMinimum(1)
        self.limit_spinbox.setMaximum(1000)
        self.limit_spinbox.setValue(self._parameters['limit'].value)

        self.slice_lineedit.clear()
        self.slice_lineedit.setText(self._parameters['slice'].value)
        self.slice(self._parameters['slice'].value)

        self.preview_table.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        self.preview()

        self.setLayout(vlayout)

    def _connect_gui(self):
        self.limit_spinbox.valueChanged[int].connect(self.limit)
        self.slice_lineedit.textChanged[str].connect(self.slice)
        self.preview_button.clicked.connect(self.preview)

    @property
    def valid(self):
        return GetSlice.valid_string(self._parameters['slice'].value,
                                     self._dims, self._allow_int)

    def slice(self, text):
        self._parameters['slice'].value = text
        if self.valid:
            self.slice_lineedit.setStyleSheet('QLineEdit { color : back; }')
        else:
            self.slice_lineedit.setStyleSheet('QLineEdit { color : red; }')

        self.status_changed.emit()

    def limit(self, value):
        self._parameters['limit'].value = int(value)

    def clear_preview(self, err_msg=''):
        self.preview_table.clear()
        self.preview_table.setColumnCount(1)
        self.preview_table.setRowCount(1)
        if err_msg:
            self.preview_table.setItem(0, 0, QtGui.QTableWidgetItem(err_msg))

    def preview(self):
        # Fail immediately if there is no input data
        if self._itable is None:
            self.clear_preview('No input data')
            return

        try:
            index = self._parameters['slice'].value
            limit = self._parameters['limit'].value

            slice_index = GetSlice.from_string(index)
            slice_data = self._itable[slice_index]

            if not GetSlice.valid_string(index, self._dims):
                raise SliceError

            rows = min(slice_data.number_of_rows(), limit)
            col_names = slice_data.column_names()
            cols = slice_data.number_of_columns()

            self.preview_table.clear()
            self.preview_table.setColumnCount(cols)
            self.preview_table.setRowCount(rows)
            self.preview_table.setHorizontalHeaderLabels(col_names)

            for col, col_name in enumerate(col_names):
                for row, data in zip(range(rows),
                                     slice_data.get_column_to_array(col_name)):
                    self.preview_table.setItem(
                        row,
                        col,
                        QtGui.QTableWidgetItem(text_type(data)))

        except SliceError:
            self.clear_preview('Invalid slice')
        except:
            traceback.print_exc()
            self.clear_preview('Failed to create preview')


class SlicesWidget(ParameterView):

    def __init__(self, node_context, itables, parent=None):
        super(SlicesWidget, self).__init__(parent=parent)
        self._node_context = node_context
        self._parameters = node_context.parameters
        self._single = None
        self._itables = itables
        self._init_gui()
        self._connect_gui()

    @property
    def valid(self):
        return self._single.valid

    def _init_gui(self):
        self.vlayout = QtGui.QVBoxLayout()
        group_hlayout = QtGui.QHBoxLayout()

        self.group_label = QtGui.QLabel('Preview group nr:')
        self.group_spinbox = QtGui.QSpinBox()

        group_hlayout.addWidget(self.group_label)
        group_hlayout.addWidget(self.group_spinbox)

        self.vlayout.addLayout(group_hlayout)

        self.group_spinbox.setMinimum(0)
        if self._itables.is_valid():
            self.group_spinbox.setMaximum(max(0, len(self._itables) - 1))
        else:
            self.group_spinbox.setMaximum(0)
        self.group_spinbox.setValue(self._parameters['group_index'].value)

        self.group(self._parameters['group_index'].value)
        self.setLayout(self.vlayout)

    def _connect_gui(self):
        self.group_spinbox.valueChanged[int].connect(self.group)
        self._single.status_changed.connect(self.status_changed)

    def group(self, value):
        try:
            self._single.hide()
        except:
            pass
        self._parameters['group_index'].value = int(value)

        if self._itables.is_valid() and len(self._itables):
            itable = self._itables[int(value)]
        else:
            itable = None

        self._single = SliceWidget(self._node_context, itable)
        self.vlayout.addWidget(self._single)


class SliceListTables(synode.Node):
    """
    Slice elements in a list of Tables.

    :Inputs:
        **InTable** : Tables
            List of Tables.
    :Outputs:
        **OutTable** : Tables
            List of Tables consisting of the Tables that been sliced out
            from the incoming list according to the defined pattern.
    :Configuration:
        **Slice**
            Use standard Python syntax to define pattern for slice operation,
            [start:stop:step].
        **Limit preview to**
            Specify the maximum number of rows in the preview table.
        **Preview** : Button
            Push to visualise the effect of the defined slice.
    :Opposite node:
    :Ref. nodes:
    """

    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    name = 'Slice List of Tables'
    icon = 'list_slice.svg'
    nodeid = 'org.sysess.sympathy.slice.slicelisttables'
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.Tables('Input Table', name='port1')])
    outputs = Ports([Port.Tables('Sliced output Tables', name='port2')])

    parameters = slice_base_parameters()

    def execute(self, node_context):
        slice_index = GetSlice.from_string(
            node_context.parameters['slice'].value)
        itables = node_context.input['port1']
        otables = node_context.output['port2']
        if isinstance(slice_index, int):
            otables.append(itables[slice_index])
        else:
            for itable in list(itables)[slice_index]:
                otables.append(itable)

    def verify_parameters(self, node_context):
        return GetSlice.valid_string(node_context.parameters['slice'].value, 1)

    def exec_parameter_view(self, node_context):
        if node_context.input['port1'].is_valid():
            itable = table.File()
            itable.set_column_from_array(
                '0',
                numpy.arange(len(node_context.input['port1'])))
        else:
            itable = None
        return SliceWidget(node_context, itable, 1)


class SliceListADAFs(synode.Node):
    """
    Slice elements in a list of ADAFs.

    :Inputs:
        **InTable** : ADAFs
            List of ADAFs.
    :Outputs:
        **OutTable** : ADAFs
            List of ADAFs consisting of the ADAFs that been sliced out
            from the incoming list according to the defined pattern.
    :Configuration:
        **Slice**
            Use standard Python syntax to define pattern for slice operation,
            [start:stop:step].
        **Limit preview to**
            Specify the maximum number of rows in the preview table.
        **Preview** : Button
            Push to visualise the effect of the defined slice.
    :Opposite node:
    :Ref. nodes:
    """

    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    name = 'Slice List of ADAFs'
    icon = 'list_slice.svg'
    nodeid = 'org.sysess.sympathy.slice.slicelistadafs'
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.ADAFs('Input ADAFs', name='port1')])
    outputs = Ports([Port.ADAFs('Sliced output ADAFs', name='port2')])

    parameters = slice_base_parameters()

    def execute(self, node_context):
        slice_index = GetSlice.from_string(
            node_context.parameters['slice'].value)
        itables = node_context.input['port1']
        otables = node_context.output['port2']
        if isinstance(slice_index, int):
            otables.append(itables[slice_index])
        else:
            for itable in list(itables)[slice_index]:
                otables.append(itable)

    def verify_parameters(self, node_context):
        return GetSlice.valid_string(node_context.parameters['slice'].value)

    def exec_parameter_view(self, node_context):
        if node_context.input['port1'].is_valid():
            itable = table.File()
            itable.set_column_from_array(
                '0',
                numpy.arange(len(node_context.input['port1'])))
        else:
            itable = None
        return SliceWidget(node_context, itable, 1)


class SliceList(synode.Node):
    """
    Slice elements in a list.

    :Configuration:
        **Slice**
            Use standard Python syntax to define pattern for slice operation,
            [start:stop:step].
        **Limit preview to**
            Specify the maximum number of rows in the preview table.
        **Preview** : Button
            Push to visualise the effect of the defined slice.
    :Opposite node:
    :Ref. nodes:
    """

    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2015 System Engineering Software Society"
    name = 'Slice List'
    icon = 'slice_list.svg'
    nodeid = 'org.sysess.sympathy.slice.slicelist'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.List)

    inputs = Ports([
        Port.Custom('[<a>]', 'Input List', name='list')])
    outputs = Ports([
        Port.Custom('[<a>]', 'Sliced output List', name='list')])

    parameters = slice_base_parameters()

    def execute(self, node_context):
        slice_index = GetSlice.from_string(
            node_context.parameters['slice'].value)
        itables = node_context.input['list']
        otables = node_context.output['list']
        for itable in list(itables)[slice_index]:
            otables.append(itable)

    def verify_parameters(self, node_context):
        return GetSlice.valid_string(
            node_context.parameters['slice'].value, 1, allow_int=False)

    def exec_parameter_view(self, node_context):
        try:
            itable = table.File()
            itable.set_column_from_array(
                '0',
                numpy.arange(len(node_context.input['list'])))
        except NoDataError:
            itable = None
        return SliceWidget(node_context, itable, 1, allow_int=False)
