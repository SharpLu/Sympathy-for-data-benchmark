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
import traceback

from .. utils.components import get_components
from .. platform.exceptions import sywarn
from .. platform import qt_compat

QtGui = qt_compat.import_module('QtGui')


class DATASOURCE(object):
    FILE = 0
    DATABASE = 1


class IDataImportFactory(object):
    """A factory interface for DataImporters."""
    def __init__(self):
        super(IDataImportFactory, self).__init__()

    def importer_from_datasource(self, datasource):
        """Get an importer from the given datasource."""
        raise NotImplementedError("Not implemented for interface.")


class IDataImporter(object):
    """Interface for a DataImporter. It's important to set IMPORTER_NAME
    to a unique name otherwise errors will occur."""
    IMPORTER_NAME = "UNDEFINED"
    DATASOURCES = [DATASOURCE.FILE]

    def __init__(self, fq_infilename, parameters):
        super(IDataImporter, self).__init__()
        self._fq_infilename = fq_infilename
        self._parameters = parameters

    def valid_for_file(self):
        """Is this importer valid for the given file."""
        raise NotImplementedError("Not implemented for interface.")

    def import_data(self, out_adaffile, parameters=None, progress=None):
        raise NotImplementedError("Not implemented for interface.")

    def name(self):
        raise NotImplementedError("Not implemented for interface.")


class ADAFDataImporterBase(IDataImporter):
    def __init__(self, fq_infilename, parameters):
        super(ADAFDataImporterBase, self).__init__(fq_infilename, parameters)

    def valid_for_file(self):
        """Return True if this importer is valid for fq_filename."""
        return False

    def is_adaf(self):
        """Is the file to be imported a valid ADAF file."""
        return False


class TableDataImporterBase(IDataImporter):
    def __init__(self, fq_infilename, parameters):
        super(TableDataImporterBase, self).__init__(fq_infilename, parameters)

    def valid_for_file(self):
        """Return True if this importer is valid for fq_filename."""
        return False

    def is_table(self):
        """Is the file to be imported a valid Table file."""
        return False


class TextDataImporterBase(IDataImporter):
    def __init__(self, fq_infilename, parameters):
        super(TextDataImporterBase, self).__init__(fq_infilename, parameters)

    def valid_for_file(self):
        """Return True if this importer is valid for fq_filename."""
        return False

    def is_text(self):
        """Is the file to be imported a valid Table file."""
        return False


class IDataSniffer(object):
    def __init__(self):
        super(IDataSniffer, self).__init__()

    def sniff(self, path):
        """Sniff the given file and return the data format."""
        raise NotImplementedError("Not implemented for interface.")


class IDataImporterWidget(object):
    """Interface for data importer widgets, used to configure
    parameters to the importer."""
    def __init__(self):
        pass


class DataImporterLocator(object):
    """Given a folder locate all eligable importer classes derived from
    the IDataImporter interface."""
    def __init__(self, importer_parent_class):
        super(DataImporterLocator, self).__init__()
        self._importer_parent_class = importer_parent_class

    def importer_from_sniffer(self, file2import):
        """Use sniffers to evaluate a valid importer and return it."""
        valid_importer = lambda c: c(file2import, None).valid_for_file()
        for importer in get_components('plugin_*.py',
                                       self._importer_parent_class):
            if valid_importer(importer):
                return importer
        return None

    def importer_from_name(self, importer_name):
        """Return the importer associated with importer_name."""
        importers = get_components('plugin_*.py', self._importer_parent_class)
        valid_importers = (importer for importer in importers
                           if importer.IMPORTER_NAME == importer_name)
        try:
            return next(valid_importers)
        except StopIteration:
            raise KeyError(importer_name)

    def available_importers(self, datasource_compatibility=None):
        """Return the available importers."""
        importers = get_components('plugin_*.py', self._importer_parent_class)
        if datasource_compatibility is None:
            return {importer.IMPORTER_NAME: importer for importer in importers}
        else:
            return {importer.IMPORTER_NAME: importer for importer in importers
                    if datasource_compatibility in importer.DATASOURCES}


class ImporterConfigurationWidget(QtGui.QWidget):
    def __init__(self, available_importers, parameters,
                 fq_infilename, parent=None):
        super(ImporterConfigurationWidget, self).__init__(parent)
        self._parameters = parameters
        self._custom_parameters = self._parameters["custom_importer_data"]
        self._available_importers = available_importers
        self._available_importer_names = sorted(available_importers.keys())
        self._importer_name = None
        self._fq_infilename = fq_infilename

        self._init_gui()
        self._init_gui_from_parameters()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setSizeConstraint(QtGui.QLayout.SetMaximumSize)
        hlayout = QtGui.QHBoxLayout()

        importer_label = QtGui.QLabel("Importer to use")
        self._importer_combobox = QtGui.QComboBox()
        hlayout.addWidget(importer_label)
        hlayout.addWidget(self._importer_combobox)
        hlayout.addSpacing(250)

        self._importer_tabwidget = QtGui.QTabWidget()
        self._importer_combobox.addItems(self._available_importer_names)

        for i, im_name in enumerate(self._available_importer_names):
            importer_class = self._available_importers[im_name]
            try:
                if im_name not in self._custom_parameters:
                    self._custom_parameters.create_group(im_name)

                importer = importer_class(self._fq_infilename,
                                          self._custom_parameters[im_name])
                if hasattr(importer, 'parameter_view'):
                    parameter_widget = (
                        importer.parameter_view(
                            self._custom_parameters[im_name]))
                    self._importer_tabwidget.addTab(parameter_widget, im_name)
                else:
                    self._importer_tabwidget.addTab(QtGui.QWidget(), im_name)
            except:
                sywarn("{} importer failed to build its configuration gui. "
                       "The exception was:\n{}".format(
                           im_name, traceback.format_exc()))
                self._importer_tabwidget.addTab(QtGui.QWidget(),
                                                '{}:Failed'.format(im_name))
        vlayout.addItem(hlayout)
        vlayout.addWidget(self._importer_tabwidget)
        vlayout.addItem(QtGui.QSpacerItem(500, 1))
        fail_layout = QtGui.QHBoxLayout()
        fail_layout.addWidget(QtGui.QLabel('Action on failed import:'))
        fail_layout.addWidget(self._parameters['fail_strategy'].gui())
        vlayout.addItem(fail_layout)
        self.setLayout(vlayout)

        self._importer_combobox.currentIndexChanged[int].connect(
            self._importer_changed)
        self._importer_tabwidget.currentChanged[int].connect(
            self._tab_changed)

    def _init_gui_from_parameters(self):
        active_importer = self._parameters["active_importer"].value
        index = self._importer_combobox.findText(active_importer)
        # Select the first item if none is selected.
        if index == -1:
            self._importer_combobox.setCurrentIndex(0)
        else:
            self._importer_combobox.setCurrentIndex(index)

    def _importer_changed(self, index):
        active_importer = str(self._importer_combobox.itemText(index))
        self._parameters["active_importer"].value = active_importer
        self._importer_tabwidget.setCurrentIndex(index)

    def _tab_changed(self, index):
        self._importer_combobox.setCurrentIndex(index)


def main():
    fq_source_filename = (
        "/Users/alexander/Projects/sympathy/code/sympathy-datasources/src/"
        "Python/vcc/diva_importer.py")
    dil = DataImporterLocator(fq_source_filename)
    print dil.functions()

if __name__ == '__main__':
    main()
