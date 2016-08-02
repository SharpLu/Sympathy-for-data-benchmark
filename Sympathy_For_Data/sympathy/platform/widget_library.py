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
import itertools

from sympathy.api import qt as qt_compat
from sympathy.utils import prim

QtCore = qt_compat.import_module('QtCore')
QtGui = qt_compat.import_module('QtGui')
qt_compat.backend.use_matplotlib_qt()

from matplotlib.backends.backend_qt4agg \
    import NavigationToolbar2QT as NavigationToolbar


toolbar_stylesheet = """
QToolBar {
    background: %s;
    border: 1px solid %s;
    spacing: 3px;
}

QToolButton {
    border-radius: 1px;
    background-color: %s;
}

QToolButton:checked {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 rgba(0,0,0,60), stop: 1 rgba(0,0,0,30));
}

QToolButton:pressed {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 rgba(140,190,255,100), stop: 1 rgba(140,190,255,50));
}

QToolButton::menu-button {
    border: none;
}

QToolButton::menu-arrow:open {
    top: 1px;
}
"""


class SyNavigationToolbar(NavigationToolbar):
    def __init__(self, canvas, parent, coordinates=True):
        super(SyNavigationToolbar, self).__init__(canvas, parent, coordinates)

        self.setStyleSheet(self.construct_style_sheet())

    def construct_style_sheet(self):
        return toolbar_stylesheet % (self.get_parent_color(), self.get_border_color(), self.get_parent_color())

    def get_parent_color(self):
        color = self.palette().color(self.backgroundRole())
        return color.name()

    def get_border_color(self):
        color = self.palette().color(QtGui.QPalette.Mid)
        return color.name()


class CheckableComboBox(QtGui.QComboBox):
    selectedItemsChanged = QtCore.Signal(bool)
    checked_items_changed = QtCore.Signal(list)

    def __init__(self):
        super(CheckableComboBox, self).__init__()
        self.setItemDelegate(QtGui.QStyledItemDelegate(self))

        self._listview = self.view()

        self._listview.pressed.connect(self.handleItemPressed)
        self._listview.clicked.connect(self.handleItemClicked)

    def handleItemClicked(self, index):
        self.handleItemPressed(index, alter_state=False)

    def handleItemPressed(self, index, alter_state=True):
        item = self.model().itemFromIndex(index)
        self.blockSignals(True)
        if alter_state:
            if item.checkState() == QtCore.Qt.Checked:
                item.setCheckState(QtCore.Qt.Unchecked)
                idx = self.select_current_index()
            else:
                item.setCheckState(QtCore.Qt.Checked)
                idx = index.row()
        else:
            if item.checkState():
                idx = index.row()
            else:
                idx = self.select_current_index()
        self.setCurrentIndex(idx)
        self.blockSignals(False)
        self.selectedItemsChanged.emit(True)
        self.currentIndexChanged.emit(idx)
        self.checked_items_changed.emit(self.checkedItemNames())

    def select_current_index(self):
        selected_items = self.checkedItems()
        if len(selected_items):
            idx = selected_items[-1].row()
        else:
            idx = 0
        return idx

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)
        select_all = menu.addAction('Select all')
        unselect_all = menu.addAction('Unselect all')
        invert_selection = menu.addAction('Invert selection')
        action = menu.exec_(event.globalPos())
        if action == select_all:
            for row_idx in xrange(self.model().rowCount()):
                self.set_checked_state(row_idx, True)
        elif action == unselect_all:
            for row_idx in xrange(self.model().rowCount()):
                self.set_checked_state(row_idx, False)
        elif action == invert_selection:
            for row_idx in xrange(self.model().rowCount()):
                state = self.get_checked_state(row_idx)
                self.set_checked_state(row_idx, not state)
        self.selectedItemsChanged.emit(True)

    def set_checked_state(self, idx, state):
        checked = QtCore.Qt.Checked if state else QtCore.Qt.Unchecked
        self.model().item(idx).setCheckState(checked)

    def get_checked_state(self, idx):
        return bool(self.model().item(idx).checkState())

    def checkedItems(self):
        selected_items = []
        for row_idx in xrange(self.model().rowCount()):
            item = self.model().item(row_idx)
            if item is not None and bool(item.checkState()):
                selected_items.append(item)
        return selected_items

    def checkedItemNames(self):
        return [item.text() for item in self.checkedItems()]

    def add_item(self, text, checked=False):
        item = QtGui.QStandardItem(text)
        item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                      QtCore.Qt.ItemIsEnabled)
        is_checked = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
        item.setData(is_checked, QtCore.Qt.CheckStateRole)
        last_idx = self.model().rowCount()
        self.model().setItem(last_idx, 0, item)


class MacStyledItemDelegate(QtGui.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        widget = QtGui.QCheckBox(index.data(), parent=parent)
        widget.stateChanged[bool].connect(self.stateChanged)
        return widget

    def paint(self, painter, option, index):
        option.showDecorationSelected = False
        super(MacStyledItemDelegate, self).paint(painter, option, index)

    def setEditorData(self, editor, index):
        editor.setCheckState(index.data(QtCore.Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.checkState(), QtCore.Qt.EditRole)

    @QtCore.Slot(bool)
    def stateChanged(self):
        self.commitData.emit(self.sender())


class LineEditButton(QtGui.QToolButton):
    def __init__(self, parent, iconname):
        super(LineEditButton, self).__init__(parent)
        pixmap = QtGui.QPixmap(iconname)
        self.setIcon(QtGui.QIcon(pixmap))
        self.setIconSize(QtCore.QSize(16, 16))  # pixmap.size()
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setPopupMode(QtGui.QToolButton.InstantPopup)
        self.setStyleSheet(
            """
            QToolButton { border: none; padding: 0px; background-color: white; }
            QToolButton:pressed { background-color: rgba(0,0,0,30); border: none; border-radius: 5px; }
            """)


class LineEdit(QtGui.QLineEdit):
    def __init__(self, parent=None, inactive="", clear_button=True):
        super(LineEdit, self).__init__(parent)

        self.left = QtGui.QWidget(self)
        self.left_layout = QtGui.QHBoxLayout(self.left)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.right = QtGui.QWidget(self)
        self.right_layout = QtGui.QHBoxLayout(self.right)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.setPlaceholderText(inactive)
        if clear_button:
            self.add_clear_button()

    def add_widget(self, widget, to_right=True):
        if to_right:
            layout = self.right_layout
            layout.insertWidget(1, widget)
        else:
            layout = self.left_layout
            layout.addWidget(widget)
        self.update_geometry()

    def remove_widget(self, widget):
        self.left_layout.removeWidget(widget)
        self.right_layout.removeWidget(widget)

    def update_geometry(self):
        frame_width = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        self.setStyleSheet(
            "QLineEdit { padding-left: %spx; padding-right: %spx; } " % (
                self.left.sizeHint().width() + frame_width + 1,
                self.right.sizeHint().width() + frame_width + 1)
        )
        msz = self.minimumSizeHint()
        self.setMinimumSize(
            max(msz.width(),
                self.right.sizeHint().height() + frame_width * 2 + 2),
            max(msz.height(),
                self.right.sizeHint().height() + frame_width * 2 + 2))

    def resizeEvent(self, event):
        frame_width = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        rect = self.rect()
        left_hint = self.left.sizeHint()
        right_hint = self.right.sizeHint()
        self.left.move(frame_width + 1, (rect.bottom() + 1 - left_hint.height()) / 2)
        self.right.move(rect.right() - frame_width - right_hint.width(),
                        (rect.bottom() + 1 - right_hint.height()) / 2)

    def add_clear_button(self):
        self.clear_button = LineEditButton(self,
                                           prim.get_icon_path('actions/edit-delete-symbolic.svg'))
        self.add_widget(self.clear_button)
        self.clear_button.clicked.connect(self.clear)
        # TODO (BZ): allow show/hide of clear button and trigger textChanged to outside
        # self.textChanged.connect(self.update_clear_button)

    def update_clear_button(self, text):
        self.clear_button.setVisible(not text == '')


class SyToolBar(QtGui.QToolBar):
    def __init__(self, parent=None):
        super(SyToolBar, self).__init__(parent)
        self.setMinimumHeight(22)
        self.setMaximumHeight(38)
        self.setIconSize(QtCore.QSize(26, 26))

        self._exclusive_checked_buttons = {}

        self.setStyleSheet(self.construct_style_sheet())

    def construct_style_sheet(self):
        return toolbar_stylesheet % (self.get_parent_color(), self.get_border_color(), self.get_parent_color())

    def get_parent_color(self):
        color = self.palette().color(self.backgroundRole())
        return color.name()

    def get_border_color(self):
        color = self.palette().color(QtGui.QPalette.Mid)
        return color.name()

    def add_action(self, text, icon_name, tooltip_text=None,
                   is_checkable=False, is_checked=False, is_exclusive=False,
                   receiver=None, signal_type=None):
        """
        Creates a new action with the given `text` and `tooltip_text`.
        The action is added to the end of the toolbar. The `signal_type`
        sets how the action's signal calls the receiver.
        """
        icon = QtGui.QIcon(prim.get_icon_path(icon_name))
        a = self.addAction(icon, text)
        if tooltip_text is not None:
            a.setToolTip(tooltip_text)
        if is_checkable:
            a.setCheckable(is_checkable)
            a.setChecked(is_checked)
            if is_exclusive:
                self._exclusive_checked_buttons[a] = receiver
                a.toggled.connect(self._update_buttons_checked)
        if receiver is not None and not is_exclusive:
            if signal_type is None:
                a.triggered.connect(receiver)
            else:
                signal = getattr(a, signal_type)
                signal.connect(receiver)
        return a

    @QtCore.Slot(bool)
    def _update_buttons_checked(self, state):
        sender = self.sender()
        if state:
            for action, callback in self._exclusive_checked_buttons.iteritems():
                action.setChecked(sender == action)
            callback = self._exclusive_checked_buttons[sender]
            if callback is not None:
                callback()
        elif not state and len(self._exclusive_checked_buttons):
            actions = itertools.cycle(self._exclusive_checked_buttons.iterkeys())
            current_action = actions.next()
            while current_action != sender:
                current_action = actions.next()
            next_action = actions.next()
            self.blockSignals(True)
            next_action.setChecked(True)
            self.blockSignals(False)
            callback = self._exclusive_checked_buttons[next_action]
            if callback is not None:
                callback()

    def addStretch(self):
        spacer = QtGui.QWidget(parent=self)
        spacer.setMinimumWidth(0)
        policy = QtGui.QSizePolicy()
        policy.setHorizontalStretch(0)
        policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        spacer.setSizePolicy(policy)
        self.addWidget(spacer)


class BasePreviewTable(QtGui.QTableView):
    contextMenuClicked = QtCore.Signal(unicode, int, int)

    def __init__(self, parent=None):
        super(BasePreviewTable, self).__init__(parent)

        self._context_menu_actions = []

        self.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(
            QtGui.QAbstractItemView.SelectItems)
        self.setSelectionMode(
            QtGui.QAbstractItemView.NoSelection)
        self.ScrollHint(
            QtGui.QAbstractItemView.EnsureVisible)
        self.setCornerButtonEnabled(True)
        self.setShowGrid(True)
        self.setAlternatingRowColors(True)
        self.setMinimumHeight(100)

        header = self.horizontalHeader()
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.header_context_menu)

    def header_context_menu(self, pos):
        header = self.horizontalHeader()

        action = self.menu.exec_(header.mapToGlobal(pos))
        if action:
            column_idx = header.logicalIndexAt(pos)
            callback = self._context_menu_actions[action]
            self.contextMenuClicked.emit(callback, -1, column_idx)

    def contextMenuEvent(self, event):
        if not self._context_menu_actions:
            return

        global_pos = event.globalPos()
        pos = self.viewport().mapFromGlobal(global_pos)
        qindex = self.indexAt(pos)
        row_idx = qindex.row()
        column_idx = qindex.column()

        self.menu = QtGui.QMenu(self)
        current_menu_items = {}

        for action_param in self._context_menu_actions:
            title, func, icon_name, validate_func = action_param

            is_valid = validate_func(row_idx, column_idx)
            if is_valid:
                if icon_name is not None:
                    icon = QtGui.QIcon(prim.get_icon_path(icon_name))
                    action = self.menu.addAction(icon, title)
                else:
                    action = self.menu.addAction(title)
                current_menu_items[action] = func

        action = self.menu.exec_(global_pos)
        if action:
            callback = current_menu_items[action]
            self.contextMenuClicked.emit(callback, row_idx, column_idx)
        event.accept()

    def add_context_menu_action(self, title, function, icon_name=None,
                                validate_callback=lambda r, c: True):
        self._context_menu_actions.append((title, function, icon_name, validate_callback))


class EnhancedPreviewTable(QtGui.QWidget):
    def __init__(self, model=None, filter_function=None, parent=None):
        super(EnhancedPreviewTable, self).__init__(parent)

        if model is None:
            model = QtCore.QAbstractItemModel()
        self._model = model
        self._filter_function = filter_function

        self._init_gui()

    def _init_gui(self):
        self._preview_table = BasePreviewTable()
        self._preview_table.setModel(self._model)

        # Toolbar
        self._toolbar = SyToolBar()
        # Search field
        self._filter_lineedit = LineEdit(inactive='Search')
        self._filter_lineedit.setMinimumWidth(50)
        self._filter_lineedit.setMaximumWidth(250)
        policy = QtGui.QSizePolicy()
        policy.setHorizontalStretch(1)
        policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        self._filter_lineedit.setSizePolicy(policy)

        self._toolbar.addWidget(self._filter_lineedit)
        self._toolbar.addStretch()

        # Legend
        self._legend_layout = QtGui.QHBoxLayout()
        self._legend_layout.addStretch()

        # Setup layout
        layout = QtGui.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._toolbar)
        layout.addWidget(self._preview_table)
        layout.addLayout(self._legend_layout)

        self.setLayout(layout)

        # Connect signals
        self._filter_lineedit.textChanged[unicode].connect(
            self._filter_columns)

    def preview_table(self):
        return self._preview_table

    def toolbar(self):
        return self._toolbar

    def _filter_columns(self, pattern):
        items = self._model.column_names()
        item_count = len(items)

        patterns = pattern.split(',')
        filtered_item_indexes = set()
        filter_func = self._filter_function
        if filter_func is None:
            return

        for pat in patterns:
            filtered_item_indexes.update(filter_func(pat, items))

        for col in xrange(item_count):
            if col in filtered_item_indexes:
                self._preview_table.setColumnHidden(col, False)
            else:
                self._preview_table.setColumnHidden(col, True)

    def reapply_filter(self):
        filter_pattern = self._filter_lineedit.text()
        self._filter_lineedit.textChanged.emit(filter_pattern)

    def set_model(self, model):
        self._model = model

    def set_filter_function(self, func):
        self._filter_function = func

    def add_widget_to_legend(self, widget, on_left=False):
        legend_layout = self._legend_layout
        if on_left:
            legend_layout.insertWidget(0, widget)
        else:
            legend_layout.addWidget(widget)

    def add_widget_to_layout(self, widget, on_top=False):
        layout = self.layout()
        if on_top:
            layout.insertWidget(0, widget)
        else:
            layout.addWidget(widget)

    def add_layout_to_layout(self, layout, on_top=False):
        main_layout = self.layout()
        if on_top:
            main_layout.insertLayout(0, layout)
        else:
            main_layout.addLayout(layout)


class RowColumnLegend(QtGui.QGroupBox):
    def __init__(self, row=0, column=0, parent=None):
        super(RowColumnLegend, self).__init__(parent)
        self._row = row
        self._column = column
        self._init_gui()

    def _init_gui(self):
        self._row_column_label = QtGui.QLabel()
        self._row_column_label.setMaximumHeight(16)

        row_count_layout = QtGui.QHBoxLayout()
        row_count_layout.setContentsMargins(0, 0, 0, 0)
        row_count_layout.setAlignment(QtCore.Qt.AlignCenter)
        icon_label = QtGui.QLabel()
        icon = QtGui.QPixmap(prim.get_icon_path(
            'actions/view-grid-symbolic.svg'))
        icon_label.setPixmap(icon)
        row_count_layout.addWidget(icon_label)
        row_count_layout.addWidget(self._row_column_label)

        self.setLayout(row_count_layout)
        self._update_row_column_label()

    def _update_row_column_label(self):
        text = u'{} \u00D7 {}'.format(self._row, self._column)
        self._row_column_label.setText(text)
        tooltip = u'{} row{}<br>{} column{}'.format(
            self._row, '' if self._row == 1 else 's',
            self._column, '' if self._column == 1 else 's')
        self.setToolTip(tooltip)

    def set_row(self, row):
        self._row = row
        self._update_row_column_label()

    def set_column(self, column):
        self._column = column
        self._update_row_column_label()

    def set_row_column(self, row, column):
        self._row = row
        self._column = column
        self._update_row_column_label()
