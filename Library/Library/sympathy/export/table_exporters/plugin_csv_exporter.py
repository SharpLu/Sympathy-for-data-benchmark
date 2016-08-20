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
import collections
import csv

from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui')
from sylib.export import table as exporttable
from sympathy.api import node as synode


# We are currently unable to support UTF-16 encodings since this plugin uses
# pythons csv module and from python docs
# (https://docs.python.org/2/library/csv.html#examples):
#
#     The csv module doesn't directly support reading and writing Unicode, but
#     it is 8-bit-clean save for some problems with ASCII NUL characters. So
#     you can write functions or classes that handle the encoding and decoding
#     for you as long as you avoid encodings like UTF-16 that use NULs. UTF-8
#     is recommended.
#
# So if we ever want to support UTF-16 we would have to use a different
# backend.
CODEC_LANGS = collections.OrderedDict((
    ('Western (ASCII)', 'ascii'),
    ('Western (ISO 8859-1)', 'iso8859_1'),
    ('Western (ISO 8859-15)', 'iso8859_15'),
    ('Western (Windows 1252)', 'windows-1252'),
    ('UTF-8', 'utf_8')))


def encode_values(data_row, encoding):
    """
    Return a list of encoded strings with the values of the sequence data_row.
    The values in the sequences are converted to unicode first so if any values
    are already encoded strings, they must be encoded with 'ascii' codec.
    """
    return [unicode(value).encode(encoding) for value in data_row]


def table2csv(tabledata, fq_outfilename, header, encoding):
    """Write table to CSV."""
    # Workaround instead of using matplotlib's rec2csv that doesn't play
    # nicely with unicode/latin-1 characters.
    with open(fq_outfilename, 'w+b') as out_file:

        csv_writer = csv.writer(out_file,
                                delimiter=';',
                                quotechar='"',
                                doublequote=True,
                                quoting=csv.QUOTE_MINIMAL)

        if header:
            csv_writer.writerow(
                encode_values(tabledata.column_names(), encoding))
        if tabledata is not None:
            for row in tabledata.to_rows():
                csv_writer.writerow(encode_values(row, encoding))


class DataExportCSVWidget(QtGui.QWidget):
    def __init__(self, parameter_root, *args, **kwargs):
        super(DataExportCSVWidget, self).__init__(*args, **kwargs)
        self._parameter_root = parameter_root
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.addWidget(self._parameter_root['encoding'].gui())
        vlayout.addWidget(self._parameter_root['table_names'].gui())
        vlayout.addWidget(self._parameter_root['header'].gui())
        # vlayout.addWidget(self._parameters['filename_extension'].gui())
        self.setLayout(vlayout)


class DataExportCSV(exporttable.TableDataExporterBase):
    """Exporter for CSV files."""
    EXPORTER_NAME = "CSV"
    FILENAME_EXTENSION = "csv"

    def __init__(self, custom_parameter_root):
        super(DataExportCSV, self).__init__(custom_parameter_root)
        if 'table_names' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                'table_names', label='Use table names as filenames',
                description='Use table names as filenames')

        if 'header' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                'header', value=True, label='Export header',
                description='Export column names')

        if 'encoding' not in custom_parameter_root:
            custom_parameter_root.set_list(
                'encoding', label='Character encoding',
                list=CODEC_LANGS.keys(), value=[4],
                description='Character encoding determines how different '
                            'characters are represented when written to disc, '
                            'sent over a network, etc.',
                editor=synode.Util.combo_editor().value())

    def parameter_view(self, node_context_input):
        return DataExportCSVWidget(self._custom_parameter_root)

    def export_data(self, in_sytable, fq_outfilename, progress=None):
        """Export Table to CSV."""
        header = self._custom_parameter_root['header'].value
        encoding = CODEC_LANGS[
            self._custom_parameter_root['encoding'].selected]
        table2csv(in_sytable, fq_outfilename, header, encoding)
