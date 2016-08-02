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
import os
import sys
import argparse

from PySide import QtCore, QtGui

from sympathy.api import table
from sympathy.api import adaf
from sympathy.api import datasource
from sympathy.api import text
from sympathy.api import report
from sympathy.api import figure
from sympathy.types.types import TypeList, TypeTuple
from sympathy.utils import filebase

from .viewerbase import ViewerBase
from .lambda_viewer import LambdaViewer
from .datasource_viewer import DatasourceViewer
from .text_viewer import TextViewer
from .table_viewer import TableViewer
from .adaf_viewer import ADAFViewer
from .report_viewer import ReportViewer
from .figure_viewer import FigureViewer


class MessageViewer(QtGui.QWidget):
    def __init__(self, label=None, parent=None):
        super(MessageViewer, self).__init__(parent)
        if label is None or not isinstance(label, (str, unicode)):
            label = 'There is no data available!\n' \
                    'You probably need to execute this node!'
        q_label = QtGui.QLabel(label)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(q_label)
        self.setLayout(layout)


class ListViewer(ViewerBase):
    def __init__(self, viewer_cls=None, data_list=None, viewer=None,
                 parent=None):
        super(ListViewer, self).__init__(parent)

        self.VIEWER_CLS = viewer_cls
        self._viewer = viewer
        self._data_list = data_list

        self._init_gui()
        self._init_list_view()

    def _init_gui(self):
        hlayout = QtGui.QHBoxLayout()

        self._select_listview = QtGui.QListWidget(self)
        if self._viewer is None:
            self._viewer = self.VIEWER_CLS(parent=self)
        else:
            self._viewer.setParent(self)

        self._select_listview.setMaximumWidth(50)

        hlayout.addWidget(self._select_listview)
        hlayout.addWidget(self._viewer)
        self.setLayout(hlayout)

        self._select_listview.currentRowChanged[int].connect(self._row_changed)

    def _init_list_view(self):
        for index in xrange(len(self._data_list)):
            self._select_listview.addItem(unicode(index))

    def _row_changed(self, index):
        self._select_listview.setCurrentRow(index)
        try:
            self._viewer.update_data(self._data_list[index])
        except IndexError:
            pass

    def custom_menu_items(self):
        return self._viewer.custom_menu_items()

    def update_data(self, data):
        self._data_list = data
        self._select_listview.clear()
        self._init_list_view()
        self._row_changed(0)


class TupleViewer(ViewerBase):
    def __init__(self, viewer_clss=None, data_list=None, viewers=None,
                 parent=None):
        super(TupleViewer, self).__init__(parent)

        self.VIEWER_CLSS = viewer_clss
        self._viewers = viewers
        self._data_list = data_list
        self._tabwidget = QtGui.QTabWidget()
        self._init_gui()
        self._init_data_view()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()

        self._select_splitter = QtGui.QSplitter()

        if self._viewers is None:
            self._viewers = []
            for i, viewer_cls in enumerate(self.VIEWER_CLSS):
                viewer = viewer_cls(parent=self._select_splitter)
                self._viewers.append(viewer)
                self._tabwidget.addTab(viewer, str(i))
        else:
            for i, viewer in enumerate(self._viewers):
                self._tabwidget.addTab(viewer, str(i))

        self._init_data_view()

        self._tabwidget.setParent(self._select_splitter)

        vlayout.addWidget(self._select_splitter)
        self.setLayout(vlayout)

    def _init_data_view(self):
        for i in range(len(self._viewers)):
            self._viewers[i].update_data(self._data_list[i])

    def custom_menu_items(self):
        # Currently not implemented, may be difficult to support given the
        # current interface.

        # TODO(Erik): Make the interface more flexible so that menu items
        # change with the context.
        return []

    def update_data(self, data):
        self._data_list = data
        self._init_data_view()


def viewer_from_filename_factory(fq_sydata_filename):
    datagen = filebase.from_file(fq_sydata_filename)
    data = datagen.gen.next()
    viewer = viewer_from_instance_factory(data)
    # Do not remove due to gc.
    viewer._genref = datagen
    return viewer


def viewer_from_instance_factory(instance):

    def inner_basic(type_):

        data = filebase.empty_from_type(type_)

        if str(data) == 'lambda()':
            viewer = LambdaViewer(data)
        elif isinstance(data, table.File):
            viewer = TableViewer(data, plot=True)
        elif isinstance(data, datasource.File):
            viewer = DatasourceViewer(data)
        elif isinstance(data, text.File):
            viewer = TextViewer(data)
        elif isinstance(data, adaf.File):
            viewer = ADAFViewer(data)
        elif isinstance(data, report.File):
            viewer = ReportViewer(data)
        elif isinstance(data, figure.File):
            viewer = FigureViewer(data)
        else:
            viewer = MessageViewer(label='The data-type of this port '
                                         'is currently not supported.')
        return viewer

    def inner_list(type_):
        child_viewer = inner_main(type_[0])
        return ListViewer(viewer=child_viewer,
                          data_list=filebase.empty_from_type(type_))

    def inner_tuple(type_):
        child_viewers = [inner_main(child_type)
                         for child_type in type_]
        return TupleViewer(viewers=child_viewers,
                           data_list=filebase.empty_from_type(type_))

    def inner_main(type_):

        if isinstance(type_, TypeList):
            viewer = inner_list(type_)
        elif isinstance(type_, TypeTuple):
            viewer = inner_tuple(type_)
        else:
            viewer = inner_basic(type_)

        return viewer

    viewer = inner_main(instance.container_type)
    viewer.update_data(instance)
    return viewer


class ViewerManager(object):
    def __init__(self, window):
        self._window = window
        self._viewer = None

    @property
    def viewer(self):
        return self._viewer

    @viewer.setter
    def viewer(self, value):
        self._viewer = value

    def data(self):
        return self._viewer.data()

    def update(self, data):
        # if isinstance(data, syi_module.SyiNode):
        #     self._viewer = self._create_syinode_widget(data)
        # else:
        #     self.viewer = viewer_from_instance_factory(data)
        self.viewer = viewer_from_instance_factory(data)
        self._window.setCentralWidget(self.viewer)

    def clear(self):
        """Clear the viewer."""
        self._viewer = None
        self.update(self._viewer)

    def _create_syinode_widget(self, syinode):
        widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()

        tabwidget = QtGui.QTabWidget()

        for port in syinode.io.outputs():
            data = port.to_data()
            viewer = viewer_from_instance_factory(data)
            viewer.layout().setContentsMargins(0, 0, 0, 0)
            tabwidget.addTab(viewer, port.name)

        layout.addWidget(tabwidget)
        widget.setLayout(layout)
        return widget


class MainWindow(QtGui.QMainWindow):
    window_title = 'Data Viewer'

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self._viewer_manager = ViewerManager(self)
        self._fq_filename = None

        self._init_gui()

    def _init_gui(self):
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        open_action = QtGui.QAction('&Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.setStatusTip('Open')
        open_action.triggered.connect(self._open)

        clear_action = QtGui.QAction('Clear', self)
        # clear_action.setShortcut('Ctrl+R')
        clear_action.setStatusTip('Clear')
        clear_action.triggered.connect(self._clear)

        reload_action = QtGui.QAction('&Reload', self)
        reload_action.setShortcut('Ctrl+R')
        reload_action.setStatusTip('Reload')
        reload_action.triggered.connect(self._reload)

        quit_action = QtGui.QAction('&Quit', self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.setStatusTip('Quit')
        quit_action.triggered.connect(self.close)

        manual_action = QtGui.QAction('&User Manual', self)
        manual_action.setStatusTip('Open User Manual in browser')
        manual_action.triggered.connect(self.open_documentation)

        # self.statusBar()
        menubar = self.menuBar()
        filemenu = menubar.addMenu('&File')
        view_menu = menubar.addMenu('&View')
        help_menu = menubar.addMenu('&Help')
        # removed until we find a nicer way of implementing options into the global settings
        # self._options_menu = menubar.addMenu('&Options')
        filemenu.addAction(open_action)
        filemenu.addAction(quit_action)

        view_menu.addAction(clear_action)
        view_menu.addAction(reload_action)

        help_menu.addAction(manual_action)

        self._console_dock = QtGui.QDockWidget('Interactive console', self)
        self._console_dock.setHidden(True)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._console_dock)

        dock_widget = QtGui.QWidget()
        dock_widget.setLayout(QtGui.QVBoxLayout())
        dock_widget.layout().addWidget(QtGui.QLabel('Console'))

        interactive_action = self._console_dock.toggleViewAction()
        interactive_action.setShortcut('Ctrl+I')
        view_menu.addAction(interactive_action)

        self.setWindowTitle(self.window_title)

    def open_from_filename(self, filename):
        def is_file_valid(filename):
            return (
                filename is not None and
                os.path.isfile(filename) and
                os.stat(filename).st_size)
        old_viewer = self._viewer_manager.viewer
        if is_file_valid(filename):
            self._fq_filename = filename
            viewer = viewer_from_filename_factory(filename)
        else:
            viewer = MessageViewer()

        # self._options_menu.clear()
        # if hasattr(viewer, 'custom_menu_items'):
        #     for action in viewer.custom_menu_items():
        #         self._options_menu.addAction(action)
        if viewer is None and old_viewer is not None:
            viewer = old_viewer
        self._viewer_manager.viewer = viewer
        self.setCentralWidget(viewer)

    def _clear(self):
        self._viewer_manager.clear()

    def _reload(self):
        self.open_from_filename(self._fq_filename)

    def _open(self):
        filename, _ = QtGui.QFileDialog.getOpenFileName(
            self, 'Open File', '.')
        self.open_from_filename(filename)

    def open_documentation(self):
        """Open the documentation at the Viewer chapter."""
        # TODO: implementation
        pass


def run():
    parser = argparse.ArgumentParser(
        'Open a viewer for *.sydata files.')

    # Filename is a positional argument.
    parser.add_argument(
        'filename', action='store', nargs='?', default=None,
        help='A .sydata file.')
    args = parser.parse_args()

    application = QtGui.QApplication(sys.argv)

    window = MainWindow()

    if args.filename:
        fs_encoding = sys.getfilesystemencoding()
        window.open_from_filename(args.filename.decode(fs_encoding))

    window.setMinimumWidth(800)
    window.setMinimumHeight(600)

    window.show()
    window.activateWindow()
    window.raise_()

    sys.exit(application.exec_())
