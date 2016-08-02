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
import itertools

from .. platform import qt_compat
QtGui = qt_compat.import_module('QtGui')

from .. utils.components import get_components
from .. platform import gennode
from .. platform import exceptions


class IExporterAccessManager(object):
    def create_filenames(self, parameter_root, node_contex_input):
        raise NotImplementedError

    def parameter_view(self, parameter_root, node_context_input):
        raise NotImplementedError

    def file_based(self):
        raise NotImplementedError


class ExporterAccessManagerBase(object):
    def __init__(self, exporter):
        self._exporter = exporter

    def create_filenames(self, parameter_root, node_context_input):
        if self._exporter.file_based():
            filename = parameter_root['filename'].value
            return self._exporter.create_filenames(
                node_context_input, filename)
        return self._exporter.create_filenames(node_context_input, None)

    def parameter_view(self, parameter_root, node_context_input):
        return self._exporter.parameter_view(node_context_input)

    def file_based(self):
        return self._exporter.file_based()


class IDataExporter(object):
    """Interface for a DataExporter. It's important to set EXPORTER_NAME
    to a unique name otherwise errors will occur."""
    EXPORTER_NAME = "UNDEFINED"
    access_manager = IExporterAccessManager

    def create_filenames(self, *args):
        raise NotImplementedError

    def export_data(self, *args):
        raise NotImplementedError

    def parameter_view(self, *args):
        return QtGui.QWidget()

    @staticmethod
    def file_based():
        raise NotImplementedError


class DataExporterBase(IDataExporter):
    access_manager = ExporterAccessManagerBase

    def __init__(self, custom_parameter_root):
        self._custom_parameter_root = custom_parameter_root

    @staticmethod
    def file_based():
        return True

    def create_filenames(self, *args):
        return inf_filename_gen('-')


class ADAFDataExporterBase(DataExporterBase):
    pass


class TableDataExporterBase(DataExporterBase):
    pass


class TextDataExporterBase(DataExporterBase):
    pass


class DatasourceDataExporterBase(DataExporterBase):
    pass


class DataExporterLocator(object):
    """Given a folder locate all eligable exporter classes derived from
    the IDataExporter interface."""
    def __init__(self, exporter_parent_class):
        super(DataExporterLocator, self).__init__()
        self._exporter_parent_class = exporter_parent_class

    def exporter_from_name(self, exporter_name):
        """Return the exporter associated with exporter_name."""
        exporters = get_components('plugin_*.py', self._exporter_parent_class)
        return next(exporter for exporter in exporters
                    if exporter.EXPORTER_NAME == exporter_name)

    def available_exporters(self):
        """Return the available exporters."""
        exporters = get_components('plugin_*.py', self._exporter_parent_class)
        return {exporter.EXPORTER_NAME: exporter for exporter in exporters}


class ExporterConfigurationWidget(QtGui.QWidget):
    def __init__(self, available_exporters, parameters,
                 node_context_input, parent=None, filename_selection=True):
        super(ExporterConfigurationWidget, self).__init__(parent)
        self._parameters = parameters
        self._custom_parameters = parameters['custom_exporter_data']
        self._available_exporters = available_exporters
        self._available_exporter_names = sorted(available_exporters.keys())
        self._exporter_name = None
        self._node_context_input = node_context_input
        self._exporters = {}

        self._init_gui(filename_selection)
        self._init_gui_from_parameters()

    def _init_gui(self, filename_selection):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setSizeConstraint(QtGui.QLayout.SetMaximumSize)
        hlayout = QtGui.QHBoxLayout()

        exporter_label = QtGui.QLabel('Exporter to use')
        self._exporter_combobox = QtGui.QComboBox()
        hlayout.addWidget(exporter_label)
        hlayout.addWidget(self._exporter_combobox)
        hlayout.addSpacing(250)

        self._exporter_tabwidget = QtGui.QTabWidget()
        self._exporter_combobox.addItems(self._available_exporter_names)

        if len(self._available_exporter_names) == 1:
            self._exporter_combobox.setDisabled(True)

        for im_name in self._available_exporter_names:
            exporter_class = self._available_exporters[im_name]

            custom_parameter_root = self._custom_parameters
            try:
                custom_group = custom_parameter_root[im_name]
            except KeyError:
                custom_group = custom_parameter_root.create_group(im_name)

            tab_widget = QtGui.QWidget()
            tab_layout = QtGui.QVBoxLayout()
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_widget.setLayout(tab_layout)

            # Create default filename extension info from exporter.
            # If this is explicitly set to none then it will not be used.

            output_extension = getattr(
                exporter_class, 'FILENAME_EXTENSION', '')

            use_extension = (exporter_class.file_based() and
                             output_extension is not None)

            if use_extension:
                try:
                    custom_group['filename_extension']
                except KeyError:

                    try:
                        custom_group.set_string(
                            'filename_extension',
                            value=output_extension,
                            label='Filename extension')
                    except AttributeError:
                        custom_group.set_string(
                            'filename_extension', value='',
                            label='Filename extension')
            exporter = exporter_class.access_manager(
                exporter_class(self._custom_parameters[im_name]))
            self._exporters[im_name] = exporter
            try:
                parameter_widget = (
                    exporter.parameter_view(self._parameters,
                                            self._node_context_input))
            except Exception as e:
                parameter_widget = QtGui.QLabel(u'Failed to load')
                exceptions.sywarn(u'Exporter:"{}" failed to load: "{}"'.format(
                    im_name, e))
                tab_layout.addWidget(parameter_widget)
            else:
                tab_layout.addWidget(parameter_widget)

                if use_extension and filename_selection:
                    tab_layout.addWidget(
                        custom_group['filename_extension'].gui())
            self._exporter_tabwidget.addTab(tab_widget, im_name)

        vlayout.addItem(hlayout)
        vlayout.addWidget(self._exporter_tabwidget)
        vlayout.addItem(QtGui.QSpacerItem(500, 1))
        self.setLayout(vlayout)

        self._exporter_combobox.currentIndexChanged[int].connect(
            self._exporter_changed)
        self._exporter_tabwidget.currentChanged[int].connect(
            self._tab_changed)

    def _init_gui_from_parameters(self):
        active_exporter = self._parameters['active_exporter'].value
        if active_exporter != '':
            index = self._exporter_combobox.findText(active_exporter)
        else:
            index = 0
            self._exporter_changed(index)
        self._exporter_combobox.setCurrentIndex(index)

    def _exporter_changed(self, index):
        active_exporter = str(self._exporter_combobox.itemText(index))
        self._parameters['active_exporter'].value = active_exporter
        self._exporter_tabwidget.setCurrentIndex(index)

    def _tab_changed(self, index):
        self._exporter_combobox.setCurrentIndex(index)

    def create_filenames(self):
        exporter = self._exporters.get(
            self._parameters['active_exporter'].value, None)
        return create_filenames_from_parameters(
            self._parameters, self._node_context_input, exporter)


def inf_filename_gen(filename_wo_ext, filename_ext=None):
    """Return an infinite filename generator.
       >>> filenames = inf_filename_gen('test', 'csv')
       >>> filenames.next()
       'test.csv'
       >>> filenames.next()
       'test_1.csv'
    """
    if '' == filename_wo_ext:
        number = lambda x: u'{0}'.format(str(x))
    else:
        number = lambda x: u'' if x == 0 else u'_{0}'.format(str(x))
    extsep = '' if not filename_ext else os.path.extsep
    if filename_ext is None:
        return (u'{0}{1}'.format(
            filename_wo_ext, number(index))
            for index in itertools.count())
    return (u'{0}{1}{2}{3}'.format(
            filename_wo_ext, number(index), extsep, filename_ext)
            for index in itertools.count())


def inf_fq_filename_gen(directory, filenames):
    gen = (os.path.join(directory, filename) for filename in filenames)

    if isinstance(filenames, list):
        return list(gen)
    else:
        return gen


def create_fq_filenames(directory, filenames):
    return inf_fq_filename_gen(directory, filenames)


def create_filenames_from_parameters(parameter_root, node_context_input,
                                     exporter):
    try:
        return exporter.create_filenames(
            parameter_root, node_context_input)
    except (AttributeError, NotImplementedError, exceptions.NoDataError):
        return inf_filename_gen('-')


class ExporterWidget(QtGui.QWidget):
    def __init__(self, node_context, parameter_root, exporter_param_widget,
                 util_lib=None, parent=None, filename_selection=True):
        super(ExporterWidget, self).__init__(parent)
        self._node_context = node_context
        self._parameter_root = parameter_root
        self._exporter_param_widget = exporter_param_widget
        self._util_lib = util_lib
        self._input_file_count = self._get_input_file_count()
        self._init_gui(filename_selection)

    def _init_gui(self, filename_selection):
        vlayout = QtGui.QVBoxLayout()

        exporter_vlayout = QtGui.QVBoxLayout()
        exporter_vlayout.addWidget(self._exporter_param_widget)

        exporter_groupbox = QtGui.QGroupBox('Exporter')
        exporter_groupbox.setLayout(exporter_vlayout)

        if 'directory' not in self._parameter_root:
            self._parameter_root.set_string(
                'directory', label='Output directory',
                description='Select the directory where to export the files.',
                editor=gennode.Util.directory_editor().value())

        if 'filename' not in self._parameter_root:
            self._parameter_root.set_string(
                'filename', label='Filename',
                description='Filename without extension.')

        outputs_vlayout = QtGui.QVBoxLayout()

        for child in self._parameter_root.children():
            if child.name not in ['active_exporter',
                                  'custom_exporter_data']:
                outputs_vlayout.addWidget(child.gui())

        preview_button = QtGui.QPushButton('Filename(s) preview')
        self._preview_label = QtGui.QLabel('')
        self._preview_label.setMaximumWidth(500)
        self._preview_label.setWordWrap(True)

        outputs_vlayout.addWidget(preview_button)
        outputs_vlayout.addWidget(self._preview_label)

        outputs_groupbox = QtGui.QGroupBox('Outputs')
        outputs_groupbox.setLayout(outputs_vlayout)

        vlayout.addWidget(exporter_groupbox)
        vlayout.addWidget(outputs_groupbox)
        self.setLayout(vlayout)

        preview_button.clicked.connect(self._preview_clicked)

    def _preview_clicked(self):
        filenames = self._exporter_param_widget.create_filenames()

        if isinstance(filenames, list):
            length = len(list(filenames))
        else:
            length = self._input_file_count

        # Preview at most 5 entries.
        length = min(5, length)

        preview_filenames = [fq_filename for fq_filename, _ in zip(
            filenames, xrange(length))]
        if not len(preview_filenames):
            self._preview_label.setText('Nothing to preview')
        else:
            self._preview_label.setText(', '.join(preview_filenames))

    def _get_input_file_count(self):
        inputfile_count = None
        input_list = self._node_context.input['port0']
        if input_list.is_valid():
            inputfile_count = len(input_list)
        else:
            # When no input data is available show preview for three
            # filenames.
            inputfile_count = 3
        return inputfile_count


def main():
    fq_source_filename = (
        '/Users/alexander/Projects/sympathy/code/sympathy-datasources/src/'
        'Python/vcc/diva_exporter.py')
    dil = DataExporterLocator(fq_source_filename)
    print dil.functions()

if __name__ == '__main__':
    main()
