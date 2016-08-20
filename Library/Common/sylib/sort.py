from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui') # noqa
from sympathy.api.exceptions import SyConfigurationError
from . import util


class SortWidget(QtGui.QWidget):

    def __init__(self, input_list, node_context, parent=None):
        super(SortWidget, self).__init__(parent)
        self._node_context = node_context
        self._input_list = input_list
        self._parameters = node_context.parameters
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        compare_label = QtGui.QLabel('Compare function for sorting:')
        example1_label = QtGui.QLabel(
            "Example, sorting input produced by Random ADAFs:\n"
            "lambda adaf: adaf.meta['meta_col0'].value()")

        example1_label.setWordWrap(True)

        self._compare_text = QtGui.QTextEdit("")
        reverse_gui = self._node_context.parameters['reverse'].gui()

        self._preview_button = QtGui.QPushButton("Preview sorting")
        self._preview_table = QtGui.QTableWidget()

        compare_vlayout = QtGui.QVBoxLayout()
        compare_vlayout.addWidget(reverse_gui)
        compare_vlayout.addWidget(compare_label)
        compare_vlayout.addWidget(self._compare_text)

        preview_vlayout = QtGui.QVBoxLayout()
        preview_vlayout.addWidget(self._preview_button)
        preview_vlayout.addWidget(self._preview_table)

        sorting_hlayout = QtGui.QHBoxLayout()
        sorting_hlayout.addLayout(compare_vlayout)
        sorting_hlayout.addLayout(preview_vlayout)

        vlayout.addLayout(sorting_hlayout)
        vlayout.addWidget(example1_label)

        self._init_gui_from_parameters()

        self.setLayout(vlayout)
        self._compare_text.textChanged.connect(self._compare_function_changed)
        self._preview_button.clicked.connect(self._preview_update)

    def _init_gui_from_parameters(self):

        self._compare_text.setText(
            self._parameters['sort_function'].value)

    def _compare_function_changed(self):
        text = self._compare_text.toPlainText()
        self._parameters['sort_function'].value = unicode(text)

    def _preview_update(self):
        try:
            self._preview_table.clear()

            sort_ind = sorted_list(
                self._parameters['sort_function'].value,
                self._input_list,
                reverse=self._node_context.parameters['reverse'].value,
                enum=True)

            self._preview_table.setRowCount(2)
            self._preview_table.setColumnCount(len(sort_ind))
            self._preview_table.setVerticalHeaderLabels(
                ['Previous indices', 'Sorted indices'])
            self._preview_table.setHorizontalHeaderLabels(
                [' '] * len(sort_ind))
            for ind, new_ind in enumerate(sort_ind):
                self._preview_table.setItem(0, ind, QtGui.QTableWidgetItem(
                    str(ind)))
                self._preview_table.setItem(1, ind, QtGui.QTableWidgetItem(
                    str(new_ind)))
            self._preview_table.resizeColumnsToContents()
        except:
            self._preview_table.clear()
            self._preview_table.setRowCount(1)
            self._preview_table.setColumnCount(1)
            self._preview_table.setItem(
                0, 0, QtGui.QTableWidgetItem(
                    'Sorting function not valid'))


def sorted_list(sort_function_str, input_list, enum=False, reverse=False):
    if len(input_list) == 0:
        return []

    try:
        key_func = util.base_eval(
            unicode(sort_function_str))

        if enum:
            enumerated = sorted(
                enumerate(input_list),
                key=lambda (i, item): key_func(item),
                reverse=reverse)
            return [x for x, y in enumerated]
        else:
            return sorted(
                input_list,
                key=key_func,
                reverse=reverse)

    except (KeyError, NameError):
        raise
        raise SyConfigurationError('Sort function not properly configured.')
