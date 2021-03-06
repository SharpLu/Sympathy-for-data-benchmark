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

from sylib.table_importer_gui import TableImportWidgetCSV
from sylib.table_sources import ImporterCSV, TableSourceCSV
from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui')
from sympathy.api import node as synode
from sympathy.api import importers
from sympathy.api.exceptions import SyDataError


class DataImportCSVWidget(QtGui.QWidget):

    def __init__(self, parameters, fq_infilename):
        super(DataImportCSVWidget, self).__init__()
        self._parameters = parameters
        self._init_gui()
        self._filename = fq_infilename

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        hlayout = QtGui.QHBoxLayout()

        row_label = QtGui.QLabel("Skip no. rows beginning of file")
        self._row_lineedit = QtGui.QLineEdit()
        self._preview = QtGui.QTextEdit()
        self._show_preview_button = QtGui.QPushButton('Show preview')

        hlayout.addWidget(row_label)
        hlayout.addWidget(self._row_lineedit)
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self._preview)
        vlayout.addWidget(self._show_preview_button)

        self.setLayout(vlayout)
        # Init GUI from parameters before signals are connected.
        self._init_gui_from_parameters()

        self._row_lineedit.textChanged[str].connect(
            self._row_changed)
        self._show_preview_button.clicked.connect(self._show_preview)

    def _init_gui_from_parameters(self):
        self._row_lineedit.setText(str(
            self._parameters.value_or_empty(
                "start_reading_from_line")))

    def _row_changed(self, text):
        self._parameters.set_integer(
            "start_reading_from_line", int(text))

    def _show_preview(self):
        with open(self._filename, 'r') as f:
            from_row = 0
            if len(self._row_lineedit.text()) > 0:
                from_row = int(self._row_lineedit.text())
            lines = f.readlines(1024)
            self._preview.setText(''.join(lines[from_row:]))


class DataImportCSV(importers.base.TableDataImporterBase):
    """Importer for CSV files."""

    IMPORTER_NAME = "CSV"

    def __init__(self, fq_infilename, parameters):
        super(DataImportCSV, self).__init__(fq_infilename, parameters)
        if parameters is not None:
            self._init_parameters()

    def name(self):
        return self.IMPORTER_NAME

    def _init_parameters(self):
        parameters = self._parameters
        nbr_of_rows = 99999
        nbr_of_end_rows = 9999999

        # Init header row spinbox
        if 'header_row' not in parameters:
            parameters.set_integer(
                'header_row', value=1,
                description='The row where the headers are located.',
                editor=synode.Util.bounded_spinbox_editor(
                    1, nbr_of_rows, 1).value())
        # Init unit row spinbox
        if 'unit_row' not in parameters:
            parameters.set_integer(
                'unit_row', value=1,
                description='The row where the units are located.',
                editor=synode.Util.bounded_spinbox_editor(
                    1, nbr_of_rows, 1).value())
        # Init description row spinbox
        if 'description_row' not in parameters:
            parameters.set_integer(
                'description_row', value=1,
                description='The row where the descriptions are located.',
                editor=synode.Util.bounded_spinbox_editor(
                    1, nbr_of_rows, 1).value())
        # Init data start row spinbox
        if 'data_start_row' not in parameters:
            parameters.set_integer(
                'data_start_row', value=1,
                description='The first row where data is stored.',
                editor=synode.Util.bounded_spinbox_editor(
                    1, nbr_of_rows, 1).value())
        # Init data end row spinbox
        if 'data_end_row' not in parameters:
            parameters.set_integer(
                'data_end_row', value=0,
                description='The data rows.',
                editor=synode.Util.bounded_spinbox_editor(
                    0, nbr_of_end_rows, 1).value())
        # Init headers checkbox
        if 'headers' not in parameters:
            parameters.set_boolean(
                'headers', value=None,
                description='File has headers.')
        # Init units checkbox
        if 'units' not in parameters:
            parameters.set_boolean(
                'units', value=False,
                description='File has headers.')
        # Init descriptions checkbox
        if 'descriptions' not in parameters:
            parameters.set_boolean(
                'descriptions', value=False,
                description='File has headers.')
        # Init transposed checkbox
        if 'transposed' not in parameters:
            parameters.set_boolean(
                'transposed', value=False, label='Transpose input data',
                description='Transpose the data.')
        if 'end_of_file' not in parameters:
            parameters.set_boolean(
                'end_of_file', value=True,
                description='Select all rows to the end of the file.')

        if 'read_selection' not in parameters:
            parameters.set_list(
                'read_selection', value=[0],
                plist=['Read to the end of file',
                       'Read specified number of rows',
                       'Read to specified number of rows from the end'],
                description='Select how to read the data',
                editor=synode.Util.combo_editor().value())

            # Move value of old parameter to new the format.
            if not parameters['end_of_file'].value:
                parameters['read_selection'].value = [2]

        if 'delimiter' not in parameters:
            parameters.set_string(
                'delimiter',
                value=None)
        if 'other_delimiter' not in parameters:
            parameters.set_string(
                'other_delimiter',
                value=None,
                description='Enter other delimiter than the standard ones.')

        if 'preview_start_row' not in parameters:
            parameters.set_integer(
                'preview_start_row', value=1, label='Preview start row',
                description='The first row where data will review from.',
                editor=synode.Util.bounded_spinbox_editor(
                    1, 500, 1).value())

        if 'no_preview_rows' not in parameters:
            parameters.set_integer(
                'no_preview_rows', value=20, label='Number of preview rows',
                description='The number of preview rows to show.',
                editor=synode.Util.bounded_spinbox_editor(1, 200, 1).value())

        if 'source_coding' not in parameters:
            parameters.set_string(
                'source_coding',
                value=None)

        if 'double_quotations' not in parameters:
            parameters.set_boolean(
                'double_quotations', value=False,
                label='Remove double quotations',
                description='Remove double quotations in importation.')

        if 'exceptions' not in parameters:
            parameters.set_list(
                'exceptions', label='How to handle failed importation:',
                description='Select method to handle eventual errors',
                plist=['Raise Exceptions',
                       'Partially read file',
                       'Read file without delimiters'],
                value=[0], editor=synode.Util.combo_editor().value())

    def valid_for_file(self):
        """Return True if input file is a valid CSV file."""
        if self._fq_infilename is None:
            return False

        not_allowed_extensions = ['xls', 'xlsx', 'h5', 'sydata']
        extension = os.path.splitext(self._fq_infilename)[1][1:]
        if extension in not_allowed_extensions:
            return False
        else:
            return True

    def parameter_view(self, parameters):
        valid_for_file = self.valid_for_file()
        if not valid_for_file:
            return QtGui.QWidget()
        return TableImportWidgetCSV(parameters, self._fq_infilename)

    def import_data(self, out_datafile, parameters=None, progress=None):
        """Import CSV data from a file"""
        parameters = parameters

        headers_bool = parameters['headers'].value
        units_bool = parameters['units'].value
        descriptions_bool = parameters['descriptions'].value
        headers_row_offset = parameters['header_row'].value - 1
        units_row_offset = parameters['unit_row'].value - 1
        descriptions_row_offset = parameters['description_row'].value - 1

        data_row_offset = parameters['data_start_row'].value - 1
        read_selection = parameters['read_selection'].value[0]
        data_rows = parameters['data_end_row'].value

        delimiter = parameters['delimiter'].value
        encoding = parameters['source_coding'].value

        exceptions = parameters['exceptions'].value[0]

        # Establish connection to csv datasource
        table_source = TableSourceCSV(self._fq_infilename)

        # Check if csv-file has a header (for auto importation only)
        if headers_bool is None:
            headers_bool = table_source.has_header
            if headers_bool:
                data_row_offset += 1
        # Check if delimiter and encoding have been modified in GUI
        if delimiter is not None:
            table_source.delimiter = delimiter
        if encoding is not None:
            table_source.encoding = encoding

        if table_source.valid_encoding:
            if not headers_bool:
                headers_row_offset = -1
            if not units_bool:
                units_row_offset = -1
            if not descriptions_bool:
                descriptions_row_offset = -1

            if read_selection == 0:
                nr_data_rows = -1
                data_end_rows = 0
            elif read_selection == 1:
                nr_data_rows = data_rows
                data_end_rows = 0
            elif read_selection == 2:
                nr_data_rows = 0
                data_end_rows = data_rows
            else:
                raise ValueError('Unknown Read Selection.')

            importer = ImporterCSV(table_source)

            try:
                if exceptions == 1:
                    importer.set_partial_read(True)
                importer.import_csv(
                    out_datafile, nr_data_rows, data_end_rows,
                    data_row_offset, headers_row_offset,
                    units_row_offset, descriptions_row_offset)
            except:
                if exceptions == 2:
                    importer.import_csv(
                        out_datafile, nr_data_rows, data_end_rows,
                        data_row_offset, headers_row_offset,
                        units_row_offset, descriptions_row_offset,
                        read_csv_full_rows=True)
                else:
                    raise

        else:
            raise SyDataError(
                'No valid encoding could be determined for input file.')
