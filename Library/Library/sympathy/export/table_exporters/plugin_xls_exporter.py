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
import numpy as np
import datetime

from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui')
from sylib.export import table as exporttable


def table2xls(table, fq_outfilename, header):
    table.to_excel(fq_outfilename, index=False, header=header)


class DataExportXLSWidget(QtGui.QWidget):
    def __init__(self, parameter_root, fq_infilename):
        super(DataExportXLSWidget, self).__init__()
        self._parameter_root = parameter_root
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.addWidget(self._parameter_root['header'].gui())
        self.setLayout(vlayout)


class DataExportXLS(exporttable.TableDataExporterBase):
    """Exporter for XLS files."""
    EXPORTER_NAME = 'XLS'
    FILENAME_EXTENSION = 'xls'

    def __init__(self, custom_parameter_root):
        super(DataExportXLS, self).__init__(custom_parameter_root)

        if 'header' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                'header', value=True, label='Export header',
                description='Export column names')

    def parameter_view(self, node_context_input):
        return DataExportXLSWidget(
            self._custom_parameter_root, node_context_input)

    def export_data(self, in_sytable, fq_outfilename, progress=None):
        """Export Table to XLS."""
        header = self._custom_parameter_root['header'].value
        df = in_sytable.to_dataframe()

        for col_name in df:
            column = df[col_name]
            if column.dtype.kind == 'm':
                # Timedeltas can't be written to excel in general, but if the
                # delta is less than a day, it can be represented as a time.
                import pandas as pd
                df[col_name] = pd.Series(np.zeros_like(
                    column, 'datetime64[us]')) + column
                print column
            elif column.dtype.kind == 'M':
                # All dates before 1900-03-01 are ambiguous because
                # of a bug in Excel which incorrectly treats the year 1900 as a
                # leap year. So perhaps we shouldn't write any such dates to
                # xls files? If we do write them, perhaps we should give a
                # warning about the fact that those dates can be problematic?
                df.loc[column < datetime.datetime(1900, 3, 1),
                       col_name] = np.nan

        table2xls(df, fq_outfilename, header)
