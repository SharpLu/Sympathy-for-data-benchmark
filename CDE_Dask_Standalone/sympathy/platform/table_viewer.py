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
import re

from sympathy.api import qt as qt_compat

QtCore = qt_compat.import_module('QtCore')
QtGui = qt_compat.import_module('QtGui')
qt_compat.backend.use_matplotlib_qt()

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib import offsetbox
from sympathy.platform import widget_library as sywidgets

from sympathy.api import table
from .viewerbase import ViewerBase
from ..utils.dtypes import DTYPES, get_pretty_type, get_parent_dtype

DTYPE_COLOR = [QtGui.QColor.fromHsvF(
    float(i) / float(len(DTYPES)), 0.18, 0.9)
               for i in range(len(DTYPES))]
COLUMN_COLORS = {kind: color for kind, color in zip(
    DTYPES.iterkeys(), DTYPE_COLOR)}

DATA_FONT = QtGui.QFont('Courier')


def fuzzy_list_filter(pattern, items):
    regex_escape = '()[].*\\+${}^-,*?|'

    if pattern:
        escaped_pattern = [
            '\\' + char if char in regex_escape else char
            for char in pattern]
        try:
            filter_ = re.compile('.*'.join(escaped_pattern), re.IGNORECASE)
        except Exception:
            filter_ = re.compile('.*')
        display = [row for row, item in enumerate(items)
                   if filter_.search(unicode(item))]
    else:
        display = range(len(items))

    return display


class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        super(TableModel, self).__init__(parent)
        self._show_colors = True

        self._table = None
        self._round_fn = lambda x: x
        self._headers = None
        self._row_count = 0
        self._column_count = 0

        # max row number due to qt bug
        self._max_row_limit = 71582788

        self._cache = {}
        # self._cnt = 0

    def table(self):
        return self._table

    def set_table(self, table_):
        if table is None:
            return
        self._table = table_
        self._headers = table_.column_names()

        self._row_count = self._table.number_of_rows()
        self._column_count = self._table.number_of_columns()

        self._cache = {}
        self._update_cache(0, 0)
        self.reset()

    def set_decimals(self, round_fn):
        self._round_fn = round_fn

    def format_data(self, data, tooltip=False):
        if data.dtype.kind == 'f' and not tooltip:
            data = self._round_fn(data)
        elif data.dtype.kind == 'M':
            data = data.tolist().isoformat()
        elif data.dtype.kind == 'S':
            # repr will show printable ascii characters as usual but will
            # replace any non-ascii or non-printable characters with an escape
            # sequence. The slice removes the quotes added by repr.
            data = repr(data)[1:-1]
        return data

    def column_names(self):
        if self._table is None:
            return []
        else:
            return self._table.column_names()

    def set_show_colors(self, show):
        self._show_colors = show

    def rowCount(self, qmodelindex):
        if self._row_count > self._max_row_limit:
            return self._max_row_limit
        return self._row_count

    def columnCount(self, qmodelindex):
        return self._column_count

    def data(self, qmodelindex, role):
        if not qmodelindex.isValid():
            return None
        row = qmodelindex.row()
        col = qmodelindex.column()
        # self._cnt = self._cnt + 1
        # if self._cnt % 10000 == 0:
        #     print self._cnt
        if role == QtCore.Qt.DisplayRole:
            if row < self._max_row_limit - 1:
                try:
                    data = self._cache[(row, col)]
                except KeyError:
                    self._update_cache(row, col)
                    data = self._cache[(row, col)]
                element = unicode(self.format_data(data))
            else:
                element = unicode('Data truncated!')
            return element
        elif role == QtCore.Qt.ToolTipRole:
            # Escape HTML characters in a way that is compatible with QToolTip.
            if row < self._max_row_limit - 1:
                text = unicode(self.format_data(self._cache[(row, col)],
                                                tooltip=True))
            else:
                text = unicode('Data truncated since maximum view limit reached!')
            return QtGui.QTextDocumentFragment.fromPlainText(text).toHtml()
        elif role == QtCore.Qt.BackgroundRole:
            if self._show_colors:
                if row < self._max_row_limit - 1:
                    return self._column_color(col)
                return QtGui.QColor.fromRgb(228, 186, 189)
            else:
                return None
        elif role == QtCore.Qt.FontRole:
            return DATA_FONT
        return None

    def _create_column_tooltip_string(self, column_name):
        column_type = self._table.column_type(column_name)
        tooltip_string = u'"{}"\n\nType: {} ({})'.format(
            column_name, get_pretty_type(column_type), column_type)
        attrs = self._table.get_column_attributes(column_name)
        attrs_string = u'\n'.join(
            [u'{}: {}'.format(k, v) for k, v in attrs.iteritems()])
        if attrs_string:
            tooltip_string += u'\n\nAttributes:\n{}'.format(attrs_string)
        return tooltip_string

    def _column_color(self, column):
        column_type = self._table.column_type(self._headers[column])
        return COLUMN_COLORS.get(get_parent_dtype(column_type), None)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self._headers[section]
            elif role == QtCore.Qt.ToolTipRole:
                return self._create_column_tooltip_string(
                    self._headers[section])
            elif role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignLeft
            elif role == QtCore.Qt.BackgroundRole:
                return self._column_color(section)

        return super(TableModel, self).headerData(section, orientation, role)

    def attributes(self):
        attrs = self._table.get_table_attributes() or {}
        return [u'{}: {}'.format(k, v) for k, v in attrs.iteritems()]

    def _update_cache(self, row, col, row_cache_size=1000,
                      col_cache_size=100, max_cache_size=1000000):
        import itertools

        lt = lambda x, y: x < y
        gt = lambda x, y: x > y
        bound_fn = lambda rel, val, bound: val if rel(val, bound) else bound
        lower_bound = lambda val, bound: bound_fn(gt, val, bound)
        upper_bound = lambda val, bound: bound_fn(lt, val, bound)

        start_row = lower_bound(row - row_cache_size / 2, 0)
        end_row = upper_bound(row + row_cache_size / 2, self._row_count)

        start_col = lower_bound(col - col_cache_size / 2, 0)
        end_col = upper_bound(col + col_cache_size / 2, self._column_count)

        rows_to_cache = xrange(start_row, end_row)
        cols_to_cache = xrange(start_col, end_col)

        real_row_col = itertools.product(rows_to_cache, cols_to_cache)
        norm_row_col = itertools.product(
            xrange(end_row - start_row), xrange(end_col - start_col))

        table_sliced = self._table[start_row:end_row, start_col:end_col]
        if len(self._cache) > max_cache_size:
            self._cache = {}

        columns = [table_sliced.get_column_to_array(name)
                   for name in table_sliced.column_names()]

        self._cache.update({((row, col), columns[n_col][n_row])
                            for (row, col), (n_row, n_col) in itertools.izip(
            real_row_col, norm_row_col)})


class AttributeModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        super(AttributeModel, self).__init__(parent)

        self._attributes = None
        self._headers = None
        self._row_count = 0
        self._column_count = 0

    def set_attributes(self, attributes_):
        if not isinstance(attributes_, dict):
            return
        self._attributes = [(key, value) for key, value in attributes_.iteritems()]

        self._headers = ['Name', 'Value']
        self._column_count = 2
        self._row_count = len(self._attributes)
        self.reset()

    def columnCount(self, qmodelindex):
        return self._column_count

    def rowCount(self, qmodelindex):
        return self._row_count

    def data(self, qmodelindex, role):
        if not qmodelindex.isValid():
            return None
        row = qmodelindex.row()
        col = qmodelindex.column()
        # self._cnt = self._cnt + 1
        # if self._cnt % 10000 == 0:
        #     print self._cnt
        if role == QtCore.Qt.DisplayRole:
            data = self._attributes[row][col]
            return data
        elif role == QtCore.Qt.ToolTipRole:
            # Escape HTML characters in a way that is compatible with QToolTip.
            return QtGui.QTextDocumentFragment.fromPlainText(
                unicode(self._attributes[row][col])).toHtml()

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self._headers[section]
            elif role == QtCore.Qt.ToolTipRole:
                return self._headers[section]
            elif role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignLeft
                # elif role == QtCore.Qt.BackgroundRole:
                #     return self._column_color(section)

        return super(AttributeModel, self).headerData(section, orientation, role)


class TableViewerPreviewTable(sywidgets.EnhancedPreviewTable):
    def __init__(self, model=None, filter_function=None, parent=None):
        super(TableViewerPreviewTable, self).__init__(model, filter_function, parent)

    def table(self):
        return self._model.table()

    def resize_columns(self):
        table_ = self.table()
        if table_ is not None:
            header = self._preview_table.horizontalHeader()
            fontmetric = QtGui.QFontMetrics(self._preview_table.font())
            for index in xrange(table_.number_of_columns()):
                cell_index = self._model.index(0, index)
                cell_text = self._model.data(
                    cell_index, QtCore.Qt.DisplayRole)
                cell_width = fontmetric.width(cell_text) + 25
                header.resizeSection(index, cell_width)

    def show_decimals(self, decimals):
        if len(decimals) > 0:
            s = u'{: 1.%sf}' % decimals
        else:
            s = u'{}'

        def inner(value):
            return s.format(value)

        self._model.set_decimals(inner)
        self._model.reset()
        # (Bene) the Qt resize is extremely costly for large tables
        # self._preview_table.resizeColumnsToContents()

    def set_model(self, model):
        self._preview_table.setModel(model)

    def _init_gui(self):
        super(TableViewerPreviewTable, self)._init_gui()

        self._preview_table.setMinimumHeight(300)
        self.row_column_legend = sywidgets.RowColumnLegend()
        self.add_widget_to_legend(self.row_column_legend, on_left=True)

    def set_row_column_legend(self, row, column):
        self.row_column_legend.set_row_column(row, column)


class TableViewer(ViewerBase):
    def __init__(self, table_=None, console=None, plot=False,
                 show_title=True, parent=None):
        super(TableViewer, self).__init__(parent)
        self._model = TableModel(self)
        self._attribute_model = AttributeModel(self)

        self._plot_x_model = QtGui.QStandardItemModel()
        self._plot_y_model = QtGui.QStandardItemModel()

        # self.has_plot = plot
        self.has_plot = plot
        self._show_title = show_title

        self._console = console
        self._init_gui()

        self.update_data(table_)

    def update_data(self, table_):
        if table_ is not None:
            self._data_preview.show_decimals('4')
            self._model.set_table(table_)
            self.set_table_name(table_.get_name())
            self._attribute_model.set_attributes(
                self._model.table().get_table_attributes() or {})
            self._data_preview.set_row_column_legend(table_.number_of_rows(),
                                                     table_.number_of_columns())
            # Resize headers to text size
            # self._preview_table.horizontalHeader().setResizeMode(
            #     QtGui.QHeaderView.Stretch)
        self._data_preview.resize_columns()
        # Keep any old filter active
        self._data_preview.reapply_filter()
        if self.has_plot:
            self._plot.update_model(self._model)

    def set_table_name(self, name):
        if name is None:
            name = ''
        self._table_name_label.setText(name)
        self._table_name_label.setToolTip(name)

    def show_colors(self, show):
        self._legend.setVisible(show)
        self._model.set_show_colors(show)
        self._model.layoutChanged.emit()

    def show_plot(self, show):
        if self.has_plot:
            self._plot.setVisible(show)

    def toggle_attributes(self, value):
        if value:
            model = self._attribute_model
        else:
            model = self._model
        self._data_preview.set_model(model)
        self._data_preview.resize_columns()

    def clear(self):
        self._model.set_table(table.File())
        self._attribute_model.set_attributes({})

    def handel_preview_table_context_menu(self, function_name, row_idx, column_idx):
        function = getattr(self, function_name, None)
        if function is not None:
            function(row_idx, column_idx)

    def plot_as_x(self, row, column):
        self._toggle_plot_action.setChecked(True)
        column_names = self._model.column_names()
        self._plot.add_column_to_plot(column_names[column], as_y=False)

    def plot_as_y(self, row, column):
        self._toggle_plot_action.setChecked(True)
        column_names = self._model.column_names()
        self._plot.add_column_to_plot(column_names[column])

    def show_stats(self, row, column):
        self._toggle_plot_action.setChecked(True)
        column_names = self._model.column_names()
        self._plot.show_stats_for(column_names[column])

    def validate_as_x(self, row, column):
        column_names = self._model.column_names()
        column_name = column_names[column]
        col_dtype = self._model.table().column_type(column_name)
        if col_dtype.kind not in ['S', 'U']:
            return True
        return False

    def validate_as_y(self, row, column):
        column_names = self._model.column_names()
        column_name = column_names[column]
        col_dtype = self._model.table().column_type(column_name)
        if col_dtype.kind not in ['S', 'U', 'M']:
            return True
        return False

    def _init_gui(self):

        self._data_preview = TableViewerPreviewTable(model=self._model,
                                                     filter_function=fuzzy_list_filter)

        self._table_name_label = QtGui.QLabel()
        self._title_layout = QtGui.QHBoxLayout()
        self._title_layout.addWidget(QtGui.QLabel("Name: "))
        self._title_layout.addWidget(self._table_name_label)
        self._title_layout.addStretch()

        self._legend = Legend()

        if self._show_title:
            self._data_preview.add_layout_to_layout(self._title_layout, on_top=True)
        self._data_preview.add_widget_to_legend(self._legend)

        hsplitter = QtGui.QSplitter()
        hsplitter.addWidget(self._data_preview)
        hsplitter.setCollapsible(0, False)

        # Figure
        if self.has_plot:
            self._plot = ViewerPlot(self._model,
                                    self._plot_x_model,
                                    self._plot_y_model)
            hsplitter.addWidget(self._plot)
            hsplitter.setCollapsible(1, False)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(hsplitter)
        if self._console is not None:
            layout.addWidget(self._console)
        self.setLayout(layout)

        table_toolbar = self._data_preview.toolbar()
        self._toggle_attributes_action = table_toolbar.add_action(
            text='Show &attributes',
            icon_name='actions/edit-select-all-symbolic.svg',
            tooltip_text='Show attributes',
            is_checkable=True,
            receiver=self.toggle_attributes,
            signal_type='toggled')

        self._toggle_colors_action = table_toolbar.add_action(
            text='Show &colors',
            icon_name='actions/view-color-symbolic.svg',
            tooltip_text='Show colors',
            is_checkable=True,
            is_checked=True,
            receiver=self.show_colors,
            signal_type='toggled')

        if self.has_plot:
            self._toggle_plot_action = table_toolbar.add_action(
                text='Show &plot',
                icon_name='actions/view-plot-line-symbolic.svg',
                tooltip_text='Show plot',
                is_checkable=True,
                is_checked=True,
                receiver=self.show_plot,
                signal_type='toggled')
            self._toggle_plot_action.setChecked(False)  # hide to start with

            # init context menus
            self._data_preview.preview_table().add_context_menu_action(
                'Plot as x',
                'plot_as_x',
                'actions/view-plot-x-axis-symbolic.svg',
                validate_callback=self.validate_as_x)
            self._data_preview.preview_table().add_context_menu_action(
                'Plot as y',
                'plot_as_y',
                'actions/view-plot-y-axis-symbolic-add.svg',
                validate_callback=self.validate_as_y)
            self._data_preview.preview_table().add_context_menu_action(
                'Show histogram',
                'show_stats',
                'actions/view-plot-hist-symbolic-dark.svg',
                validate_callback=self.validate_as_y)

            self._data_preview.preview_table().contextMenuClicked.connect(
                self.handel_preview_table_context_menu)

    def custom_menu_items(self):
        menu_items = [self._toggle_colors_action]
        if self.has_plot:
            menu_items.append(self._toggle_plot_action)
        return menu_items


class Legend(QtGui.QWidget):
    def __init__(self, parent=None):
        super(Legend, self).__init__(parent)
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        groupbox = QtGui.QGroupBox('')

        hlayout = QtGui.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setAlignment(QtCore.Qt.AlignCenter)
        for row, (dtype, text) in enumerate(DTYPES.iteritems()):
            icon = ColorBoxLegend(COLUMN_COLORS[dtype], label=text[0])
            icon.setToolTip(text)
            hlayout.addWidget(icon, 0, row)
        groupbox.setLayout(hlayout)
        layout.addStretch()
        layout.addWidget(groupbox)
        self.setLayout(layout)

        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        text = self.toolTip()
        QtGui.QToolTip.showText(pos, text)
        super(Legend, self).mouseMoveEvent(event)


class ColorBoxLegend(QtGui.QWidget):
    def __init__(self, color, label=None, parent=None):
        super(ColorBoxLegend, self).__init__(parent)
        self.color = color
        self.setMinimumHeight(16)
        self.setMinimumWidth(16)
        self.setMaximumWidth(16)
        self.setMaximumHeight(16)

        self._label_str = label
        self._label = QtGui.QLabel('')
        self._label.setFont(self._get_font())
        self._label.setAlignment(QtCore.Qt.AlignCenter)

        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 2, 0, 0)
        layout.addWidget(self._label)
        self.setLayout(layout)

        self.set_label(self._label_str)

    def set_label(self, label):
        if label is None:
            return
        self._label.setText(unicode(label))

    def _get_font(self):
        font = self._label.font()
        font.setItalic(True)
        return font

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), self.color)
        p.setPen(QtCore.Qt.black)
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))


class ViewerPlot(QtGui.QWidget):
    def __init__(self, data_model=None, x_model=None, y_model=None, parent=None):
        super(ViewerPlot, self).__init__(parent)

        self._model = data_model
        self._x_model = x_model
        self._y_model = y_model

        # show lines or histogram
        self._line_plot_active = True
        self._line_legend = None
        self._selected_x_cache = None
        # _large_data_limit define the upper limit before the user
        # needs to check the `plot_larger_data_check` checkbox to allow plotting
        self._large_data_limit = 10000000
        # _max_data_points defines the maximum number of data points before
        # we resample to data to short plot time
        self._max_data_points = 10000

        self._init_gui()

    def _init_gui(self):
        self.setContentsMargins(1, 1, 1, 1)

        plot_toolbar = sywidgets.SyToolBar()
        self.x_label = QtGui.QLabel('X:')
        self.x_value = QtGui.QComboBox()
        self.x_value.setModel(self._x_model)
        self.x_value.setToolTip('Select the column used for the x values')
        y_label = QtGui.QLabel('Y:')
        self.y_value = sywidgets.CheckableComboBox()
        self.y_value.setModel(self._y_model)
        self.y_value.setToolTip('Select the columns used for the y values. '
                                'Multiple columns can be selected.')

        resample_label = QtGui.QLabel('Resample:')
        self.resample_value = QtGui.QSpinBox()
        self.resample_value.setMinimum(1)
        self.resample_value.setMaximum(100000)
        self.resample_value.setToolTip('The step size used for resampling of large datasets.')

        self.plot_large_data_check = QtGui.QCheckBox('Plot large data')

        plot_toolbar.addWidget(self.x_label)
        plot_toolbar.addWidget(self.x_value)
        self._y_label_action = plot_toolbar.addWidget(y_label)
        self._y_value_action = plot_toolbar.addWidget(self.y_value)
        plot_toolbar.addSeparator()
        plot_toolbar.addWidget(resample_label)
        plot_toolbar.addWidget(self.resample_value)
        self._plot_large_data_action = plot_toolbar.addWidget(self.plot_large_data_check)
        self._plot_large_data_action.setVisible(False)
        plot_toolbar.addSeparator()

        self.show_line_action = plot_toolbar.add_action(
            text='Show line plot',
            icon_name='actions/view-plot-line-symbolic.svg',
            tooltip_text='Show line plot',
            is_checkable=True,
            is_checked=True,
            is_exclusive=True,
            receiver=self._on_show_line,
            signal_type='toggled')

        self.show_hist_action = plot_toolbar.add_action(
            text='Show histogram',
            icon_name='actions/view-plot-hist-symbolic.svg',
            tooltip_text='Show histogram',
            is_checkable=True,
            is_exclusive=True,
            receiver=self._on_show_hist,
            signal_type='toggled')

        plot_toolbar.addStretch()

        # figure
        self.figure = Figure()
        self._set_figure_background_color()
        self.canvas = FigureCanvas(self.figure)
        frame = QtGui.QFrame()
        frame.setFrameStyle(QtGui.QFrame.StyledPanel)
        frame_layout = QtGui.QVBoxLayout()
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame.setLayout(frame_layout)
        frame_layout.addWidget(self.canvas)
        policy = QtGui.QSizePolicy()
        policy.setHorizontalStretch(1)
        policy.setVerticalStretch(1)
        policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        policy.setVerticalPolicy(QtGui.QSizePolicy.Expanding)
        self.canvas.setSizePolicy(policy)
        self.canvas.setMinimumWidth(300)
        self.axes = self.figure.add_subplot(111)

        # Figure Layout
        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(plot_toolbar)
        layout.addWidget(frame)

        # Default navigation toolbar for matplotlib
        self.mpl_toolbar = sywidgets.SyNavigationToolbar(self.canvas, self)
        layout.addWidget(self.mpl_toolbar)

        self.setLayout(layout)

        self._update_signal_comboboxes()

        self._timeout_after = 500
        self._update_plot_timer = QtCore.QTimer(self)
        self._update_plot_timer.setInterval(self._timeout_after)
        self._update_plot_timer.setSingleShot(True)

        self.x_value.currentIndexChanged[int].connect(self._x_selection_changed)
        self.y_value.currentIndexChanged[int].connect(self._y_selection_changed)
        self.y_value.selectedItemsChanged.connect(self._update_plot_timer.start)
        self.resample_value.valueChanged[int].connect(self._resample_value_changed)
        self.plot_large_data_check.stateChanged.connect(self._update_plot_timer.start)
        self._update_plot_timer.timeout.connect(self._update_plot)

    def paintEvent(self, event):
        self._draw_canvas()
        super(ViewerPlot, self).paintEvent(event)

    def _set_figure_background_color(self):
        # FIXME: setting the correct facecolor for matplotlib figures embedded
        # in QTabWidgets doesn't work
        color = self.palette().color(self.backgroundRole())
        self.figure.set_facecolor(color.name())

    def _draw_canvas(self):
        self.axes.relim()
        self.axes.autoscale_view(True, True, True)
        self.figure.tight_layout()
        self.canvas.draw()

    def _update_plot(self, redraw=True):
        table = self._model.table()
        if table is None:
            return
        if self._line_legend is not None:
            old_legend_loc = self._line_legend._loc
        else:
            old_legend_loc = 1
        self.axes.cla()  # clear plot

        if (table.number_of_rows() > self._large_data_limit and
                not self.plot_large_data_check.isChecked()):
            return

        # show line plots
        if self._line_plot_active:
            self._y_label_action.setVisible(True)
            self._y_value_action.setVisible(True)
            x_column_name = self.x_value.currentText()
            y_column_names = self.y_value.checkedItemNames()
            for y_column_name in y_column_names:
                self._plot_line(x_column_name, y_column_name)
            if len(y_column_names) == 1:
                y_attr = table.get_column_attributes(y_column_names[0])
                unit = y_attr.get('unit', None)
                y_label = unicode(y_column_names[0])
                if unit is not None:
                    y_label += u' [{}]'.format(unit)
                self.axes.set_ylabel(y_label)
            if len(self.axes.lines):
                self._line_legend = self.axes.legend(loc='upper left')
            else:
                self._line_legend = None
            if self._line_legend is not None:
                self._line_legend.draggable(True, use_blit=True)
                # (Bene) not a good way to use private variables
                self._line_legend._loc = old_legend_loc
        else:
            # show histogram
            self._y_label_action.setVisible(False)
            self._y_value_action.setVisible(False)
            hist_column = self.x_value.currentText()
            self._plot_hist(hist_column)
        if redraw:
            self._draw_canvas()

    def _plot_hist(self, y_column_name):
        table = self._model.table()
        row_slice = slice(0, table.number_of_rows(), int(self.resample_value.value()))
        y_data = table.get_column_to_array(y_column_name)[row_slice]
        y_dtype = table.column_type(y_column_name)
        if y_dtype.kind in ['S', 'U', 'M']:
            return
        bin_count = int(np.sqrt(len(y_data)))
        hist, bins = np.histogram(y_data, bin_count)

        text_params = {'mean': '{:.2e}'.format(y_data.mean()),
                       'std': '{:.2e}'.format(y_data.std()),
                       '# of nan': '{}'.format(np.count_nonzero(np.isnan(y_data)))}

        text = "\n".join(["{}: {}".format(k, v) for k, v in text_params.iteritems()])
        # TODO: make the textbox draggable like the legend in line plot
        text_box = offsetbox.TextArea(text)
        anchored_offset_box = offsetbox.AnchoredOffsetbox(loc=1,
                                                          child=text_box)
        self.axes.add_artist(anchored_offset_box)

        width = 0.7 * (bins[1] - bins[0])
        center = (bins[:-1] + bins[1:]) / 2
        self.axes.bar(center, hist, align='center', width=width)

    def _plot_line(self, x_column_name, y_column_name):
        table = self._model.table()
        column_names = table.column_names()
        row_slice = slice(0, table.number_of_rows(), int(self.resample_value.value()))
        y_data = table.get_column_to_array(y_column_name)[row_slice]
        y_dtype = table.column_type(y_column_name)
        if x_column_name in column_names:
            x_data = table.get_column_to_array(x_column_name)[row_slice]
            x_dtype = table.column_type(x_column_name)
            x_attr = table.get_column_attributes(x_column_name)
        else:
            x_data = np.arange(len(y_data))
            x_dtype = x_data.dtype
            x_attr = {}
        if len(x_data) == len(y_data):
            xdate = x_dtype.kind == 'M'
            ydate = y_dtype.kind == 'M'
            if xdate or ydate:
                self.axes.plot_date(x_data, y_data,
                                    'o', label=y_column_name,
                                    xdate=xdate, ydate=ydate)
                if xdate:
                    self.axes.get_figure().autofmt_xdate()
            else:
                self.axes.plot(x_data, y_data, 'o', label=y_column_name)
            unit = x_attr.get('unit', None)
            x_label = unicode(x_column_name)
            if unit is not None:
                x_label += u' [{}]'.format(unit)
            self.axes.set_xlabel(x_label)

    def _x_selection_changed(self, idx):
        self._update_plot_timer.start()

    def _y_selection_changed(self, idx):
        self._update_plot_timer.start()

    def _resample_value_changed(self, idx):
        self._update_plot_timer.start()

    def _update_x_combobox(self):
        column_names = self._model.column_names()
        table = self._model.table()
        excluded_type_kinds = ['S', 'U']
        column_names = [name for name in column_names
                        if table.column_type(name).kind not in excluded_type_kinds]
        column_names = ['(index)'] + column_names
        current_selection = self.x_value.currentText()
        self.x_value.clear()
        self.x_value.addItems(column_names)
        idx = 0
        if current_selection in column_names:
            idx = column_names.index(current_selection)
        self.x_value.setCurrentIndex(idx)

    def _update_y_combobox(self):
        column_names = self._model.column_names()
        table = self._model.table()
        excluded_type_kinds = ['S', 'U', 'M']
        column_names = [name for name in column_names
                        if table.column_type(name).kind not in excluded_type_kinds]
        current_selection = self.y_value.checkedItemNames()
        current_text = self.y_value.currentText()
        self.y_value.clear()
        for name in column_names:
            checked = name in current_selection
            self.y_value.add_item(name, checked)
        idx = 0
        if current_text in column_names:
            idx = column_names.index(current_text)
        self.y_value.setCurrentIndex(idx)

    def _update_signal_comboboxes(self):
        self._update_x_combobox()
        self._update_y_combobox()

    def _on_show_line(self):
        self.show_line_action.setChecked(True)
        if not self._line_plot_active:
            row_idx = self.x_value.findText('(index)')
            if row_idx == -1:
                self.x_value.insertItem(0, '(index)')
            for i in xrange(self._x_model.rowCount()):
                item = self._x_model.item(i)
                item.setEnabled(True)
            if self.x_value.findText(self._selected_x_cache) > -1:
                current_text = self._selected_x_cache
            else:
                current_text = self._model.column_names()[0]
            idx = self.x_value.findText(current_text)
            self.x_value.setCurrentIndex(idx)
            self.x_label.setText('X:')
            self.x_value.setToolTip('Select the column used for the x values')

        self._line_plot_active = True
        self._update_plot()

    def _on_show_hist(self):
        self.show_hist_action.setChecked(True)
        if self._line_plot_active:
            self._selected_x_cache = self.x_value.currentText()
            row_idx = self.x_value.findText('(index)')
            if row_idx > -1:
                self.x_value.removeItem(row_idx)

            for i in xrange(self._x_model.rowCount()):
                item = self._x_model.item(i)
                column_name = item.text()
                column_type = self._model.table().column_type(column_name)
                if column_type.kind in ['S', 'U', 'M']:
                    item.setEnabled(False)

            current_y_text = self.y_value.currentText()
            item_idx = self.x_value.findText(current_y_text)
            idx = item_idx if item_idx != -1 else 0
            self.x_value.setCurrentIndex(idx)
            self.x_label.setText('Histogram:')
            self.x_value.setToolTip('Select the column to show histogram and statistics for.')

        self._line_plot_active = False
        self._update_plot()

    def add_column_to_plot(self, column_name, as_y=True):
        # idx = self._model.column_names().index(column_name)
        if as_y:
            items = self._y_model.findItems(column_name)
            if len(items):
                idx = items[0].row()
                self.y_value.set_checked_state(idx, True)
            else:
                idx = -1
            self.y_value.setCurrentIndex(idx)
        else:
            items = self._x_model.findItems(column_name)
            if len(items):
                idx = items[0].row()
            else:
                idx = -1
            # plus 1 to current x value since we auto generate an (index) column
            self.x_value.setCurrentIndex(idx)
        self._on_show_line()

    def show_stats_for(self, column_name):
        if self._line_plot_active:
            items = self._y_model.findItems(column_name)
            if len(items):
                column_idx = items[0].row()
            else:
                column_idx = -1
            self.y_value.setCurrentIndex(column_idx)
        else:
            items = self._x_model.findItems(column_name)
            if len(items):
                column_idx = items[0].row()
            else:
                column_idx = -1
            self.x_value.setCurrentIndex(column_idx)
        self._on_show_hist()

    def set_max_data_points(self, value):
        self._max_data_points = int(value)

    def update_model(self, model):
        self._model = model
        # compute a staring value for re-sampling so the
        # number of points per line is not above self._max_data_points
        rows = self._model.rowCount(None)
        if rows > self._max_data_points:
            start_resample_value = int(round(rows / float(self._max_data_points)))
            self.resample_value.setValue(start_resample_value)
        else:
            self.resample_value.setValue(1)

        if (self._model.table() is not None and
                    self._model.table().number_of_rows() > self._large_data_limit):
            self._plot_large_data_action.setVisible(True)
        else:
            self._plot_large_data_action.setVisible(False)
        self._update_signal_comboboxes()
        self._update_plot()
