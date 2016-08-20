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
import os

import xlsxwriter
from sympathy.platform.exceptions import sywarn

from sylib.export import table as exporttable
from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui')


def tables_to_xlsx(in_tables, fq_outfilename, header, to_plot, table_names):
    from sylib.plot import backend as plot_backends
    from sylib.plot import model as plot_models

    workbook = xlsxwriter.Workbook(fq_outfilename)
    sheet_names = []
    for i, in_table in enumerate(in_tables):
        if table_names:
            ws_name = os.path.basename(in_table.get_name())
        else:
            ws_name = in_table.get_name()

        ws_name = ws_name or 'Table_{0}'.format(i)

        if len(ws_name) > 23:
            ws_name = ws_name[:23]

        pattern = r'^(%s)(\d*)$' % ws_name
        search_res = [
            re.search(pattern, name)
            for name in sheet_names if re.search(pattern, name)]
        if search_res:
            try:
                order = int(search_res[-1].group(2)) + 1
            except ValueError:
                order = 1
            ws_name = u'{0}{1}'.format(ws_name, order)

        plots_model = plot_models.get_plots_model(in_table)
        xlsx_backend = plot_backends.XLSXWriterChartBackend(
            plots_model, workbook)
        xlsx_backend.render(ws_name, header, to_plot)
        sheet_names.append(ws_name)
    workbook.close()


class DataExportXLSXWidget(QtGui.QWidget):
    def __init__(self, parameter_root, node_context_input):
        super(DataExportXLSXWidget, self).__init__()
        self._parameter_root = parameter_root
        self._node_context_input = node_context_input
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()

        self._to_sheets = self._parameter_root['to_sheets']
        self._to_sheets_check_box = self._to_sheets.gui()

        self._to_plot = self._parameter_root['to_plot']
        self._to_plot_check_box = self._to_plot.gui()
        if not has_plots(self._node_context_input['port0']):
            self._to_plot.value = False
            self._to_plot_check_box.setDisabled(True)

        self._table_names = self._parameter_root['table_names']
        self._table_names_check_box = self._table_names.gui()
        self._table_names_check_box.setEnabled(
            not self._to_sheets.value)

        vlayout.addWidget(self._table_names_check_box)
        vlayout.addWidget(self._to_sheets_check_box)
        vlayout.addWidget(self._to_plot_check_box)
        vlayout.addWidget(self._parameter_root['header'].gui())

        self._to_sheets_check_box.stateChanged[int].connect(
            self._to_sheets_state_changed)

        self.setLayout(vlayout)

    @qt_compat.Slot(int)
    def _to_sheets_state_changed(self, value):
        if self._to_sheets.value:
            self._table_names.value = False
            self._table_names_check_box.setEnabled(
                False)
        else:
            self._table_names_check_box.setEnabled(
                True)


def has_plots(tables):
    for table in tables:
        if 'plots model' in table.get_attributes()[0]:
            plot = table.get_attributes()[0]['plots model']
            if u'"Data": ["", ""]' in plot:
                return False
        else:
            return False
    return True


def no_plot_warning():
    sywarn(
        'One or more plots contain no signal data. Plot output has '
        'been disabled since Excel does not support this. Check your '
        'plot configurations.')


class DataExportXLSX(exporttable.TableDataExporterBase):
    """Exporter for XLSX files."""

    EXPORTER_NAME = 'XLSX'
    FILENAME_EXTENSION = 'xlsx'
    DEFAULT_XLSX_NAME = 'xlsx_filename'

    def __init__(self, custom_parameter_root):
        super(DataExportXLSX, self).__init__(custom_parameter_root)

        if 'header' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                'header', value=True, label='Export header',
                description='Export column names')

        if 'to_sheets' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                'to_sheets', label='Export data to sheets',
                description='Select if incoming Tables are going to to be '
                'exported to sheets in a single file or to a single sheet in'
                'multiple files.')

        if 'to_plot' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                'to_plot', label='Embed plot in output file(s)',
                description='Select if incoming Tables with plot data should '
                'be embedded in the output file. If no plots are present, the '
                'option is disabled.',
                value=True)

        if 'table_names' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                'table_names',
                label='Use table names as filenames',
                description='Use table names as filenames')

    def parameter_view(self, node_context_input):
        return DataExportXLSXWidget(
            self._custom_parameter_root, node_context_input)

    def export_data(self, in_data, fq_outfilename, progress=None):
        """Export Table to XLSX."""
        header = self._custom_parameter_root['header'].value
        to_plot = self._custom_parameter_root['to_plot'].value
        to_sheets = self._custom_parameter_root['to_sheets'].value
        table_names = self._custom_parameter_root['table_names'].value
        if not to_sheets:
            in_data = [in_data]
        if to_plot and not has_plots(in_data):
            no_plot_warning()
            to_plot = False
        tables_to_xlsx(
            in_data, fq_outfilename, header, to_plot, table_names)

    def create_filenames(self, node_context_input, filename):
        to_sheets = self._custom_parameter_root['to_sheets'].value
        filename_generator = super(DataExportXLSX, self).create_filenames(
            node_context_input, filename)
        if to_sheets:
            return [filename_generator.next()]
        return filename_generator
