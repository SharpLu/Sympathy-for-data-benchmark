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
import os.path
import re
import platform

from sympathy.platform import qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module('QtGui')


def mock_wrap(cls):
    """
    For avoiding problems related to subclassing mocked class.
    This is used for being able to import modules without having the imports
    installed.
    See http://www.voidspace.org.uk/python/mock/.
    """
    return cls if isinstance(cls, type) else cls()


@mock_wrap
class ClampedButton(QtGui.QPushButton):
    def __init__(self, text, parent=None):
        super(ClampedButton, self).__init__(text, parent)

        font = self.font()
        fm = QtGui.QFontMetrics(font)
        rect = fm.boundingRect(text)
        self.setMaximumWidth(rect.width() + 32)

        # For OSX this is the minimum size allowed for a button with rounded
        # corners.
        if platform.system() == 'Darwin':
            self.setMinimumWidth(50)
            self.setMinimumHeight(30)


@mock_wrap
class ParameterWidget(QtGui.QWidget):
    def __init__(self, parameter_value, editor=None,
                 parent=None):
        super(ParameterWidget, self).__init__(parent)
        self._parameter_value = parameter_value
        self._editor = editor

    @qt_compat.Slot(int)
    def set_visible(self, value):
        self.setVisible(value)
        self._editor.setVisible(value)

    @qt_compat.Slot(int)
    def set_enabled(self, value):
        self.setEnabled(value)
        self._editor.setEnabled(value)

    @qt_compat.Slot(int)
    def set_disabled(self, value):
        self.setDisabled(value)
        self._editor.setDisabled(value)

    def editor(self):
        return self._editor

    def set_value(self, value):
        self._editor.set_value(value)


@mock_wrap
class ParameterValueWidget(ParameterWidget):
    def __init__(self, parameter_value, editor,
                 parent=None):
        if editor is None:
            editor = ParameterEditorValueWidget(parameter_value, {})
        super(ParameterValueWidget, self).__init__(
            parameter_value, editor, parent)
        self._value_label = None
        self.__init_gui()
        assert(self.editor()._value_lineedit is not None)

    def label_widget(self):
        return self._value_label

    def lineedit_widget(self):
        return self.editor()._value_lineedit

    def __init_gui(self):
        hlayout = QtGui.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        if self._parameter_value.label:
            self._value_label = QtGui.QLabel(self._parameter_value.label)
            hlayout.addWidget(self._value_label)
            hlayout.addItem(QtGui.QSpacerItem(10, 1))
        if self._parameter_value.description:
            self.setToolTip(self._parameter_value.description)
        hlayout.addWidget(self._editor)
        self.setLayout(hlayout)

        self.__init_gui_from_parameters()

        self._editor.valueChanged[unicode].connect(self._text_changed)

    def __init_gui_from_parameters(self):
        self._editor.set_value(self._parameter_value.value)

    def _text_changed(self, text):
        raise NotImplementedError(
            "Override when extending!")

    @qt_compat.Slot(int)
    def set_visible(self, value):
        super(ParameterValueWidget, self).set_visible(value)
        self.label_widget().setVisible(value)

    @qt_compat.Slot(int)
    def set_enabled(self, value):
        super(ParameterValueWidget, self).set_enabled(value)
        self.label_widget().setEnabled(value)

    @qt_compat.Slot(int)
    def set_disabled(self, value):
        super(ParameterValueWidget, self).set_disabled(value)
        self.label_widget().setDisabled(value)


class ParameterNumericValueWidget(ParameterWidget):
    def __init__(self, parameter_value, editor=None,
                 parent=None):
        if editor is None:
            editor = ParameterEditorValueWidget(parameter_value, {})
        super(ParameterNumericValueWidget, self).__init__(
            parameter_value, editor, parent)
        self._value_label = None
        self._layout = None
        self.__init_gui()
        assert(self._layout is not None)

    def label_widget(self):
        return self._value_label

    def __init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        self._layout = QtGui.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        if self._parameter_value.label:
            self._value_label = QtGui.QLabel(self._parameter_value.label)
            self._layout.addWidget(self._value_label)
            self._layout.addItem(QtGui.QSpacerItem(10, 1))
        if self._parameter_value.description:
            self.setToolTip(self._parameter_value.description)

        self._layout.addWidget(self._editor)

        vlayout.addItem(self._layout)
        self.setLayout(vlayout)

        self.__init_gui_from_parameters()

    def __init_gui_from_parameters(self):
        self._editor.set_value(self._parameter_value.value)


class ParameterStringWidget(ParameterValueWidget):
    valueChanged = qt_compat.Signal(unicode)

    def __init__(self, parameter_value, editor=None, parent=None):
        super(ParameterStringWidget, self).__init__(
            parameter_value, editor, parent)

    def _text_changed(self, text):
        self._parameter_value.value = unicode(text)
        self.valueChanged.emit(unicode(text))


class ParameterBooleanWidget(ParameterWidget):
    stateChanged = qt_compat.Signal(int)
    valueChanged = qt_compat.Signal(bool)

    def __init__(self, parameter_value, parent=None):
        super(ParameterBooleanWidget, self).__init__(
            parameter_value, None, parent)
        self.__init_gui()
        assert(self._editor is not None)

    def __init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        self._editor = QtGui.QCheckBox()
        if self._parameter_value.label:
            self._editor.setText(self._parameter_value.label)
        if self._parameter_value.description:
            self._editor.setToolTip(
                self._parameter_value.description)
        vlayout.addWidget(self._editor)
        self.setLayout(vlayout)

        self.__init_gui_from_parameters()

        self._editor.stateChanged[int].connect(self._state_changed)

    def __init_gui_from_parameters(self):
        try:
            self._editor.setChecked(self._parameter_value.value)
        except:
            self._editor.setChecked(QtCore.Qt.Unchecked)

    def _state_changed(self, state):
        self._parameter_value.value = state > 0
        self.stateChanged.emit(state)
        self.valueChanged.emit(state > 0)


@mock_wrap
class ParameterEditorWidget(QtGui.QWidget):
    valueChanged = qt_compat.Signal(unicode)

    def __init__(self, parameter_list, editor_dict, customization=None,
                 parent=None):
        super(ParameterEditorWidget, self).__init__(parent)
        self._customization = customization or {}
        self._parameter_list = parameter_list
        self._editor_dict = editor_dict
        self._init_customizations()

    def _init_customizations(self):
        for key in self._customization:
            try:
                self._customization[key] = self._editor_dict[key]
            except KeyError:
                pass

    @property
    def parameter_model(self):
        return self._parameter_list


@mock_wrap
class ParameterEditorValueWidget(ParameterEditorWidget):
    def __init__(self, parameter_value, editor_dict, parent=None):
        customization = {'placeholder': ''}

        super(ParameterEditorValueWidget, self).__init__(
            parameter_value, editor_dict, customization,
            parent=parent)
        self.__init_gui()

    def __init_gui(self):
        self._layout = QtGui.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._value_lineedit = QtGui.QLineEdit()
        self._layout.addWidget(self._value_lineedit)
        self.setLayout(self._layout)

        self._value_lineedit.textChanged[unicode].connect(
            self._value_changed)

        self._init_gui_from_parameters()

    def _init_gui_from_parameters(self):
        self._value_lineedit.setPlaceholderText(
            self._customization['placeholder'])

    def set_value(self, value):
        self._value_lineedit.setText(unicode(value))

    def _value_changed(self, value):
        if self._parameter_list.type == 'float':
            try:
                self._parameter_list.value = float(value)
            except ValueError:
                self._parameter_list.value = 0.0
        elif self._parameter_list.type == 'integer':
            try:
                self._parameter_list.value = int(value)
            except ValueError:
                self._parameter_list.value = 0
        elif self._parameter_list.type == 'string':
            self._parameter_list.value = value
        else:
            raise Exception("Unknown parameter type")
        self.valueChanged.emit(self._parameter_list.value)


@mock_wrap
class ParameterEditorSpinBoxWidget(ParameterEditorWidget):
    def __init__(self, parameter_value, editor_dict, customization,
                 value_spinbox, parent=None):
        self._value_spinbox = value_spinbox
        super(ParameterEditorSpinBoxWidget, self).__init__(
            parameter_value, editor_dict, customization, parent)
        self.__init_gui()

    def __init_gui(self):
        # The following must be true in order to execute.
        assert(hasattr(self, '_value_spinbox'))
        assert(self._value_spinbox is not None)

        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)

        vlayout.addWidget(self._value_spinbox)
        self.setLayout(vlayout)

        self._init_gui_from_parameters()

    def set_value(self, value):
        """Give the spinbox a new value."""
        self._value_spinbox.setValue(value)

    def set_range(self, minimum, maximum):
        """Set the minimum and maximum values."""
        self._value_spinbox.setRange(minimum, maximum)

    def _init_gui_from_parameters(self):
        self._value_spinbox.setMaximum(self._customization['max'])
        self._value_spinbox.setMinimum(self._customization['min'])
        self._value_spinbox.setSingleStep(self._customization['step'])


class ParameterEditorIntegerSpinBoxWidget(ParameterEditorSpinBoxWidget):
    valueChanged = qt_compat.Signal(int)

    def __init__(self, parameter_value, editor_dict, parent=None):
        customization = {
            'max': 100,
            'min': 0,
            'step': 1}
        value_spinbox = QtGui.QSpinBox()

        super(ParameterEditorIntegerSpinBoxWidget, self).__init__(
            parameter_value, editor_dict, customization, value_spinbox, parent)
        self._value_spinbox.valueChanged[int].connect(
            self._value_changed)

    @qt_compat.Slot(int)
    def _value_changed(self, value):
        self._parameter_list.value = value
        self.valueChanged.emit(value)


class ParameterEditorFloatSpinBoxWidget(ParameterEditorSpinBoxWidget):
    valueChanged = qt_compat.Signal(float)

    def __init__(self, parameter_value, editor_dict, parent=None):
        customization = {
            'max': 100.0,
            'min': 0.0,
            'step': 1.0,
            'decimals': 2}
        value_spinbox = QtGui.QDoubleSpinBox()

        super(ParameterEditorFloatSpinBoxWidget, self).__init__(
            parameter_value, editor_dict, customization, value_spinbox, parent)
        self._value_spinbox.valueChanged[float].connect(
            self._value_changed)
        self.__init_gui_from_parameters()

    def __init_gui_from_parameters(self):
        self._value_spinbox.setDecimals(self._customization['decimals'])
        super(ParameterEditorFloatSpinBoxWidget,
              self)._init_gui_from_parameters()

    @qt_compat.Slot(float)
    def _value_changed(self, value):
        self._parameter_list.value = value
        self.valueChanged.emit(value)


class ParameterEditorFileDialogWidget(ParameterEditorValueWidget):
    dialogChanged = qt_compat.Signal(unicode)

    def __init__(self, parameter_string, editor_dict, parent=None):
        super(ParameterEditorFileDialogWidget, self).__init__(
            parameter_string, editor_dict, parent)
        self.relative = False
        self.__init_gui()

    def __init_gui(self):
        self._dialog_button = ClampedButton(u'\u2026')
        self._layout.addWidget(self._dialog_button)

        completer = QtGui.QCompleter(self)
        # QDirModel is deprecated and should be replaced by QFileSystemModel.
        # The new class is however not working properly with QCompleter for
        # unknown reasons. QFileSystemModel is asynchronous while QDirModel
        # is synchronous. See:
        # http://blog.qt.io/blog/2010/01/08/qdirmodel-is-now-obsolete-qfilesystemmodel-is-taking-the-job/
        completer_model = QtGui.QDirModel(completer)
        completer.setModel(completer_model)
        self._value_lineedit.setCompleter(completer)

        self._dialog_button.clicked.connect(self._dialog_click)
        self.dialogChanged[unicode].connect(self._value_lineedit.setText)

    def _dialog_click(self):
        directory = os.path.dirname(self.parameter_model.value)
        if not qt_compat.USES_PYSIDE:
            fq_filename = QtGui.QFileDialog.getOpenFileName(
                self, "Select file", directory,
                ";;".join(self._editor_dict['filter']))
        else:
            fq_filename, _ = QtGui.QFileDialog.getOpenFileName(
                self, "Select file", directory,
                ";;".join(self._editor_dict['filter']))
        if fq_filename:
            if self.relative:
                try:
                    filename = os.path.relpath(fq_filename)
                except:
                    filename = fq_filename
                self.dialogChanged.emit(filename)
            else:
                self.dialogChanged.emit(fq_filename)


class ParameterEditorDirectoryDialogWidget(ParameterEditorValueWidget):
    dialogChanged = qt_compat.Signal(unicode)

    def __init__(self, parameter_string, editor_dict, parent=None):
        super(ParameterEditorDirectoryDialogWidget, self).__init__(
            parameter_string, editor_dict, parent)
        self.relative = False
        self.__init_gui()

    def __init_gui(self):
        self._dialog_button = ClampedButton(u'\u2026')
        self._layout.addWidget(self._dialog_button)

        completer = QtGui.QCompleter(self)
        # QDirModel is deprecated and should be replaced by QFileSystemModel.
        # The new class is however not working properly with QCompleter for
        # unknown reasons. QFileSystemModel is asynchronous while QDirModel
        # is synchronous. See:
        # http://blog.qt.io/blog/2010/01/08/qdirmodel-is-now-obsolete-qfilesystemmodel-is-taking-the-job/
        completer_model = QtGui.QDirModel(completer)
        completer.setModel(completer_model)
        self._value_lineedit.setCompleter(completer)

        self._dialog_button.clicked.connect(self._dialog_click)
        self.dialogChanged[unicode].connect(self._value_lineedit.setText)

    def _dialog_click(self):
        directory = self.parameter_model.value
        selected_dir = QtGui.QFileDialog.getExistingDirectory(
            self, "Select directory", directory)

        if selected_dir:
            if self.relative:
                try:
                    path = os.path.relpath(selected_dir)
                except:
                    path = selected_dir
                self.dialogChanged.emit(path)
            else:
                self.dialogChanged.emit(selected_dir)


class ParameterEditorComboboxWidget(ParameterEditorWidget):
    currentIndexChanged = qt_compat.Signal(int)
    editTextChanged = qt_compat.Signal(unicode)

    def __init__(self, parameter_list, editor_dict, parent=None):
        super(ParameterEditorComboboxWidget, self).__init__(
            parameter_list, editor_dict, parent=parent)
        self.__init_gui()

    def __init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        self._list_combobox = QtGui.QComboBox()
        vlayout.addWidget(self._list_combobox)
        self.setLayout(vlayout)
        # GUI must be initialized from parameters before signals are
        # connected to ensure correct behavior.
        self.__init_gui_from_parameters()

        self._list_combobox.currentIndexChanged[int].connect(
            self._index_changed)
        self._list_combobox.editTextChanged[unicode].connect(
            self._edit_text_changed)

    def __init_gui_from_parameters(self):
        available_elements = self._parameter_list.list
        self._list_combobox.addItems(
            available_elements)
        name = self._parameter_list.value_names
        index = 0
        if name and name[0] in available_elements:
            index = available_elements.index(name[0])
            self._parameter_list.selected = name[0]
            self._parameter_list.value = [index]
        else:
            indexes = self._parameter_list.value
            if indexes:
                index = indexes[0]
        self._list_combobox.setCurrentIndex(index)

    def _index_changed(self, index):
        self._parameter_list.value = [index]
        self.currentIndexChanged.emit(index)
        self.valueChanged.emit(self._parameter_list.selected)

    def _edit_text_changed(self, text):
        self._parameter_list.selected = unicode(text)
        self.editTextChanged.emit(text)
        self.valueChanged.emit(self._parameter_list.selected)

    def setCurrentIndex(self, index):
        self._list_combobox.setCurrentIndex(index)

    def combobox(self):
        return self._list_combobox

    def clear(self):
        self._list_combobox.clear()
        self._parameter_list.value = [0]
        self._parameter_list.list = []

    def addItems(self, items):
        self._parameter_list.list.extend(items)
        self._list_combobox.addItems(items)


class SpaceHandlingListWidget(QtGui.QListWidget):
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            selection = self.selectedItems()
            if len(selection) > 0:
                if selection[0].checkState() == QtCore.Qt.Checked:
                    new_state = QtCore.Qt.Unchecked
                else:
                    new_state = QtCore.Qt.Checked
                for item in selection:
                    item.setCheckState(new_state)
        else:
            super(SpaceHandlingListWidget, self).keyPressEvent(event)


class ParameterBasicListWidget(ParameterEditorWidget):
    itemChanged = qt_compat.Signal(QtGui.QListWidgetItem)

    def __init__(self, parameter_list, editor_dict, parent=None):
        super(ParameterBasicListWidget, self).__init__(
            parameter_list, editor_dict, parent=parent)
        self.__init_gui()

    def __init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)

        # Widgets
        self._list_widget = SpaceHandlingListWidget()
        vlayout.addWidget(self._list_widget)
        self.setLayout(vlayout)

    def addItems(self, items):
        self._list_widget.blockSignals(True)
        self._parameter_list.list.extend(items)
        self._list_widget.addItems(items)
        self._list_widget.blockSignals(False)


class ParameterEditorListWidget(ParameterEditorWidget):
    itemChanged = qt_compat.Signal(QtGui.QListWidgetItem)

    def __init__(self, parameter_list, editor_dict, parent=None):
        customization = {
            'selection': '',
            'alternatingrowcolors': True,
            'filter': False,
            'buttons': False,
            'invertbutton': False,
            'passthrough': False}

        super(ParameterEditorListWidget, self).__init__(
            parameter_list, editor_dict, customization, parent)
        self.__init_gui()

    def __init_gui(self):
        self._regex_escape = r'()[].*\\+${}^-,*?'

        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        # Widgets
        self._list_widget = SpaceHandlingListWidget()
        self._filter_widget = QtGui.QLineEdit()
        self._clear_button = QtGui.QPushButton('Clear')
        self._all_button = QtGui.QPushButton('All')
        self._invert_button = QtGui.QPushButton('Invert')
        self._passthrough_checkbox = QtGui.QCheckBox('Enable pass-through')

        if self._customization['filter']:
            hlayout = QtGui.QHBoxLayout()
            hlayout.setContentsMargins(0, 0, 0, 0)
            hlayout.addWidget(QtGui.QLabel('Filter:'))
            hlayout.addWidget(self._filter_widget)
            vlayout.addLayout(hlayout)

        vlayout.addWidget(self._list_widget)

        if self._customization['buttons']:
            hlayout = QtGui.QHBoxLayout()
            hlayout.setContentsMargins(0, 0, 0, 0)
            hlayout.addWidget(self._all_button)
            hlayout.addWidget(self._clear_button)
            if self._customization['invertbutton']:
                hlayout.addWidget(self._invert_button)
            vlayout.addLayout(hlayout)

        if self._customization['passthrough']:
            vlayout.addWidget(self._passthrough_checkbox)

        self.setLayout(vlayout)

        # GUI must be initialized from parameters before signals are
        # connected to ensure correct behavior.
        self._init_editor()
        self._init_gui_from_parameters()

        self._list_widget.itemChanged.connect(self._item_state_changed)
        self._filter_widget.textChanged.connect(self._filter_changed)
        self._clear_button.clicked.connect(self._clear_changed)
        self._all_button.clicked.connect(self._all_changed)
        self._invert_button.clicked.connect(self._invert_changed)
        self._passthrough_checkbox.stateChanged[int].connect(
            self._passthrough_changed)

    def _init_editor(self):
        if self._customization['selection'] == 'multi':
            self._list_widget.setSelectionMode(
                QtGui.QAbstractItemView.ExtendedSelection)

        self._list_widget.setAlternatingRowColors(
            bool(self._customization['alternatingrowcolors']))

    def _init_gui_from_parameters(self):
        # Sort the list and put the selected items first.
        selected_items = self._get_and_sort_selected_items()
        if not str(self._customization['selection']) == 'multi':
            if len(selected_items) > 0:
                selected_items = [selected_items[0]]
            else:
                selected_items = []

        self._list_widget.blockSignals(True)
        self._check_items(selected_items)
        self._list_widget.blockSignals(False)

    def _get_and_sort_selected_items(self):
        """ Get and sort selected and non-selected items. """
        all_items = self._parameter_list.list
        if (len(self._parameter_list.value_names) == 0 and
                    len(self._parameter_list.value) > 0) and len(all_items) > 0:
            self._parameter_list.value_names = [
                self._parameter_list.list[v]
                for v in self._parameter_list.value]
        selected_items = sorted(self._parameter_list.value_names)
        not_selected_items = sorted(list(
            set(all_items).difference(set(selected_items))))
        sorted_all_items = selected_items + not_selected_items
        # Update the underlying data model with the new order.
        self._parameter_list.list = sorted_all_items
        self._list_widget.clear()
        self._list_widget.addItems(selected_items)
        self._list_widget.addItems(not_selected_items)
        self._parameter_list.value_names = selected_items

        self._parameter_list.value = [self._parameter_list.list.index(x)
                                      for x in selected_items]

        return selected_items

    def _check_items(self, selected_items):
        for row in xrange(self._list_widget.count()):
            item = self._list_widget.item(row)
            if unicode(item.text()) in selected_items:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)

        passthrough_state = (
            QtCore.Qt.Checked if self._parameter_list.passthrough
            else QtCore.Qt.Unchecked)
        self._passthrough_checkbox.setCheckState(passthrough_state)
        self._passthrough_changed(passthrough_state)

    def _item_state_changed(self, item):
        row = self._list_widget.row(item)
        text = unicode(item.text())
        if unicode(self._customization['selection']) == 'multi':
            if item.checkState() == QtCore.Qt.Checked:
                self._parameter_list.value.append(row)
                self._parameter_list.value.sort()
                self._parameter_list.value_names.append(text)
                self._parameter_list.value_names.sort()
            else:
                # Cannot unchek all items..
                if len(self._parameter_list.value) > 0:
                    if row in self._parameter_list.value:
                        self._parameter_list.value.remove(row)
                    if text in self._parameter_list.value_names:
                        self._parameter_list.value_names.remove(text)
                else:
                    self._list_widget.blockSignals(True)
                    self._check_items(text)
                    self._list_widget.blockSignals(False)
        else:
            self._list_widget.blockSignals(True)
            if len(self._parameter_list.value) > 0:
                self._list_widget.item(
                    self._parameter_list.value[0]).setCheckState(
                    QtCore.Qt.Unchecked)
            self._parameter_list.value = [row]
            self._parameter_list.value_names = [text]
            self._list_widget.item(row).setCheckState(QtCore.Qt.Checked)
            self._list_widget.blockSignals(False)
        self.itemChanged.emit(item)

    def _filter_changed(self, text):
        if unicode(text):
            escaped_text = [r'\\' + char
                            if char in self._regex_escape
                            else char
                            for char in unicode(text)]
            try:
                filter_ = re.compile('.*'.join(escaped_text), re.IGNORECASE)
            except Exception:
                filter_ = re.compile('.*')
            display = [row for row in xrange(self._list_widget.count())
                       if len(filter_.findall(
                    self._list_widget.item(row).text())) > 0]
        else:
            display = range(self._list_widget.count())

        for row in xrange(self._list_widget.count()):
            if row in display:
                self._list_widget.item(row).setHidden(False)
            else:
                self._list_widget.item(row).setHidden(True)

    def _clear_changed(self):
        for row in xrange(self._list_widget.count()):
            item = self._list_widget.item(row)
            if not item.isHidden():
                item.setCheckState(QtCore.Qt.Unchecked)

    def _all_changed(self):
        for row in xrange(self._list_widget.count()):
            item = self._list_widget.item(row)
            if not item.isHidden():
                item.setCheckState(QtCore.Qt.Checked)

    def _invert_changed(self):
        for row in xrange(self._list_widget.count()):
            item = self._list_widget.item(row)
            if not item.isHidden():
                if item.checkState() == QtCore.Qt.Checked:
                    item.setCheckState(QtCore.Qt.Unchecked)
                else:
                    item.setCheckState(QtCore.Qt.Checked)

    def _passthrough_changed(self, new_state):
        passthrough = new_state == QtCore.Qt.Checked

        self._parameter_list.passthrough = passthrough
        self._list_widget.setEnabled(not passthrough)
        self._filter_widget.setEnabled(not passthrough)
        self._clear_button.setEnabled(not passthrough)
        self._all_button.setEnabled(not passthrough)
        self._invert_button.setEnabled(not passthrough)

    def clear(self):
        self._list_widget.blockSignals(True)
        self._list_widget.clear()
        self._parameter_list.value = [0]
        self._parameter_list.list = []
        self._parameter_list.value_names = []
        self._list_widget.blockSignals(False)

    def addItems(self, items):
        self._list_widget.blockSignals(True)
        self._parameter_list.list.extend(items)
        selected_items = self._get_and_sort_selected_items()
        self._check_items(selected_items)
        self._list_widget.blockSignals(False)
        self._filter_changed(self._filter_widget.text())


def editor_factory(editor_type, editor_dict, parameter_model):
    if editor_type == "combobox":
        return ParameterEditorComboboxWidget(
            parameter_model, editor_dict)
    elif editor_type == "listview":
        return ParameterEditorListWidget(
            parameter_model, editor_dict)
    elif editor_type == "basiclist":
        return ParameterBasicListWidget(
            parameter_model, editor_dict)
    elif editor_type == "filename":
        return ParameterEditorFileDialogWidget(
            parameter_model, editor_dict)
    elif editor_type == "dirname":
        return ParameterEditorDirectoryDialogWidget(
            parameter_model, editor_dict)
    elif editor_type == "spinbox":
        if parameter_model.type == 'integer':
            return ParameterEditorIntegerSpinBoxWidget(
                parameter_model, editor_dict)
        elif parameter_model.type == 'float':
            return ParameterEditorFloatSpinBoxWidget(
                parameter_model, editor_dict)
        else:
            return None
    elif editor_type == "lineedit":
        return ParameterEditorValueWidget(
            parameter_model, editor_dict)
    else:
        return None


class ParameterListWidget(ParameterWidget):
    def __init__(self, parameter_list, editor, parent=None):
        self._parameter_list = parameter_list
        self._list_label = None
        super(ParameterListWidget, self).__init__(
            parameter_list, editor, parent)
        self.__init_gui()

    def label_widget(self):
        return self._list_label

    def __init_gui(self):
        horizontal = isinstance(self._editor,
                                ParameterEditorComboboxWidget)
        if horizontal:
            layout = QtGui.QHBoxLayout()
        else:
            layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._parameter_list.label:
            self._list_label = QtGui.QLabel(self._parameter_list.label)
            layout.addWidget(self._list_label)
            layout.addItem(QtGui.QSpacerItem(10, 1))
        if self._parameter_list.description:
            self.setToolTip(self._parameter_list.description)
        layout.addWidget(self._editor)
        self.setLayout(layout)


class ParameterGroupWidget(QtGui.QWidget):
    def __init__(self, parameter_group, parent=None):
        super(ParameterGroupWidget, self).__init__(parent)
        self._parameter_group = parameter_group
        self._group_vlayout = None
        self._groupbox = None
        self._tab_widget = None
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        self._group_vlayout = QtGui.QVBoxLayout()
        self._groupbox = QtGui.QGroupBox(self._parameter_group.label)
        self._groupbox.setLayout(self._group_vlayout)
        vlayout.addWidget(self._groupbox)
        self.setLayout(vlayout)

    def group_layout(self):
        return self._group_vlayout

    def add_page(self, page_widget, name):
        if self._tab_widget is None:
            self._tab_widget = QtGui.QTabWidget()
            self._group_vlayout.addWidget(self._tab_widget)
        self._tab_widget.addTab(page_widget, name)

    def add_group(self, group_widget):
        self._group_vlayout.addWidget(group_widget)

    def add_widget(self, widget):
        self._group_vlayout.addWidget(widget)

    @qt_compat.Slot(int)
    def set_enabled(self, value):
        self._groupbox.setEnabled(value)

    @qt_compat.Slot(int)
    def set_disabled(self, value):
        self._groupbox.setDisabled(value)
