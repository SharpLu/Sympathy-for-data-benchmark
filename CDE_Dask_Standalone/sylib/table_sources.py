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
import codecs
from contextlib import contextmanager
import datetime
from itertools import izip
import numpy as np
import os
import pandas as pd
import re
import xlrd
import copy

from distutils.version import StrictVersion

from sympathy.platform.exceptions import sywarn, SyDataError
from sympathy.platform import qt_compat

QtCore = qt_compat.QtCore # noqa

from sympathy.api import table

from .xl_utils import get_xl_sheetnames


PANDAS_CSV_READER = pd.io.parsers.read_csv

CSV_FILE_DELIMITERS = {'Tab': '\t',
                       'Comma': ',',
                       'Semicolon': ';',
                       'Space': ' ',
                       'Other': ' '}

CODEC_LANGS = {'Western (ASCII)': 'ascii',
               'Western (ISO 8859-1)': 'iso8859_1',
               'Western (ISO 8859-15)': 'iso8859_15',
               'Western (Windows 1252)': 'windows-1252',
               'UTF-16 BE': 'utf_16_be',
               'UTF-16 LE': 'utf_16_le',
               'UTF-16': 'utf_16',
               'UTF-8': 'utf_8'}

CHUNK_ROW_LIMIT = 1000
CHUNK_BYTE_LIMIT = 1 * 1024 * 1024
SNIFF_LIMIT = 5 * 1024 * 1024
ITER_LIMIT = 50
FIND_NR_KEY = r'\d'
FIND_LINE_NR = r'line \d+'
TOO_MANY_COLUMNS = r'[\w\W]*Expected \d+ fields in line (\d+), saw \d+'
END_OF_LINE = r'[\w\W]*EOF inside string starting at line (\d+)'


def tablesource_model_factory(parameters, fq_infilename, mode):
    """Direct request from GUI of a model class."""
    if mode == 'CSV':
        return TableSourceModelCSV(parameters, fq_infilename, mode)
    elif mode == 'XLS':
        return TableSourceModelXLS(parameters, fq_infilename, mode)
    else:
        raise Exception('Unknown table source format.')


@contextmanager
def open_workbook(filename):
    """Open workbook, on demand - if possible."""
    with xlrd.open_workbook(filename, on_demand=True) as wb:
        yield wb


class PreviewWorker(QtCore.QObject):
    preview_ready = qt_compat.Signal(table.File)

    def __init__(self, import_function):
        super(PreviewWorker, self).__init__()
        self._data_table = None
        self._import_function = import_function

    def create_preview_table(self, *args):
        self._data_table = table.File()
        self._import_function(self._data_table, *args)
        self.preview_ready.emit(self._data_table)


class TableSourceModel(QtCore.QObject):
    """Model class, layer between importers and GUIs."""

    update_table = qt_compat.Signal()

    def __init__(self, parameters, fq_infilename, mode):
        super(TableSourceModel, self).__init__()
        self._parameters = parameters

        self._fq_infilename = fq_infilename
        self.data_table = None

        self._init_model_common_parameters()

    def _init_model_common_parameters(self):
        """Init common parameters xls and csv importers."""
        self.preview_start_row = self._parameters['preview_start_row']
        self.no_preview_rows = self._parameters['no_preview_rows']

        self.headers = self._parameters['headers']
        self.header_row = self._parameters['header_row']

        self.units = self._parameters['units']
        self.unit_row = self._parameters['unit_row']

        self.descriptions = self._parameters['descriptions']
        self.description_row = self._parameters['description_row']

        self.data_start_row = self._parameters['data_start_row']

        self.data_end_of_file = self._parameters['end_of_file']
        self.data_end_row = self._parameters['data_end_row']

    def _init_model_specific_parameters(self):
        """Method to include the init of special parameters for a
        specific importer.
        """
        pass

    @qt_compat.Slot()
    def collect_preview_values(self):
        """Method that asks the importer for preview data."""
        pass


class TableSourceModelXLS(TableSourceModel):
    """Model layer between GUI and xls importer."""

    get_preview = qt_compat.Signal(unicode, int, int, bool, int, int, int)

    def __init__(self, parameters, fq_infilename, mode):
        super(TableSourceModelXLS, self).__init__(
            parameters, fq_infilename, mode)
        self.data_table = None

        self._init_model_specific_parameters()
        self._init_preview_worker()

    def _init_model_specific_parameters(self):
        """Init special parameters for xls importer."""
        self.transposed = self._parameters['transposed']

        sheet_names = get_xl_sheetnames(self._fq_infilename)

        self.worksheet_name = self._parameters['worksheet_name']
        self.worksheet_name.list = sheet_names

    def _init_preview_worker(self):
        """Collect preview data from xls file."""
        self._importer = ImporterXLS(self._fq_infilename)

        self._preview_thread = QtCore.QThread()
        self._preview_worker = PreviewWorker(self._importer.import_xls)
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_thread.finished.connect(self._preview_worker.deleteLater)
        self.get_preview.connect(self._preview_worker.create_preview_table)
        self._preview_worker.preview_ready.connect(self.set_preview_table)
        self._preview_thread.start()

        self.collect_preview_values()

    @qt_compat.Slot()
    def collect_preview_values(self):
        """Collect preview data from xls file."""
        data_start_row = self.data_start_row.value - 1
        data_end_row = data_start_row + self.no_preview_rows.value

        sheet_name = self.worksheet_name.selected
        transposed = self.transposed.value

        if self.headers.value:
            headers_row = self.header_row.value - 1
        else:
            headers_row = -1
        if self.units.value:
            units_row = self.unit_row.value - 1
        else:
            units_row = -1
        if self.descriptions.value:
            descriptions_row = self.description_row.value - 1
        else:
            descriptions_row = -1

        self.get_preview.emit(
            sheet_name, data_start_row, data_end_row, transposed,
            headers_row, units_row, descriptions_row)

    @qt_compat.Slot(table.File)
    def set_preview_table(self, data_table):
        self.data_table = data_table
        self.update_table.emit()


class TableSourceModelCSV(TableSourceModel):
    """Model layer between GUI and csv importer."""

    get_preview = qt_compat.Signal(int, int, int, int, int, int)

    def __init__(self, parameters, fq_infilename, mode):
        super(TableSourceModelCSV, self).__init__(
            parameters, fq_infilename, mode)
        self.data_table = None
        self._csv_source = TableSourceCSV(fq_infilename)
        self._importer = ImporterCSV(self._csv_source)
        self._importer.set_partial_read(True)
        self._csv_delimiters = copy.copy(CSV_FILE_DELIMITERS)

        if self.headers.value is None:
            self.headers.value = self._csv_source.has_header
            if self.headers.value:
                self.data_start_row.value += 1

        self._init_model_specific_parameters()
        self._init_preview_worker()

    def _init_model_specific_parameters(self):
        """Init special parameters for csv importer."""
        self.source_coding = self._parameters['source_coding']
        self.delimiter = self._parameters['delimiter']
        self.custom_delimiter = self._parameters['other_delimiter']
        self.double_quotations = self._parameters['double_quotations']

        self.exceptions_mode = self._parameters['exceptions']

        if self.delimiter.value is None:
            self.delimiter.value = self._csv_source.delimiter
        else:
            self._csv_source.delimiter = self.delimiter.value

        if self.source_coding.value is None:
            self.source_coding.value = self._csv_source.encoding
        else:
            self._csv_source.encoding = self.source_coding.value

        self._csv_delimiters['Other'] = self.custom_delimiter.value

        self.delimiter_key = [
            key for key, value in self._csv_delimiters.iteritems()
            if value == self.delimiter.value][0]
        self.encoding_key = [
            key for key, value in CODEC_LANGS.iteritems()
            if value == self.source_coding.value][0]

    def _init_preview_worker(self):
        """Collect preview data from xls file."""
        def import_function(*args):
            try:
                self._importer.import_csv(*args, require_num=False)
            except:
                self._importer.import_csv(
                    *args, require_num=False, read_csv_full_rows=True)

        self._preview_thread = QtCore.QThread()
        self._preview_worker = PreviewWorker(import_function)
        self._preview_worker.moveToThread(self._preview_thread)
        self.get_preview.connect(self._preview_worker.create_preview_table)
        self._preview_worker.preview_ready.connect(self.set_preview_table)
        self._preview_thread.start()

        self.collect_preview_values()

    @qt_compat.Slot(unicode)
    def set_new_custom_delimiter(self, value):
        """Set new custom delimiter from GUI."""
        self.custom_delimiter.value = str(value)
        self._csv_delimiters['Other'] = str(value)
        self.set_delimiter('Other')

    @qt_compat.Slot(int)
    def set_double_quotations(self, value):
        self._set_source_double_quotations()
        self.collect_preview_values()

    def _set_source_double_quotations(self):
        self._csv_source.double_quotations = (
            self.double_quotations.value)

    @qt_compat.Slot(str)
    def set_delimiter(self, delimiter_key):
        """Set changed delimiter from GUI."""
        self.delimiter.value = self._csv_delimiters[str(delimiter_key)]
        self._csv_source.delimiter = self.delimiter.value
        self.collect_preview_values()

    @qt_compat.Slot(str)
    def set_encoding(self, encoding_key):
        """Set changed encodings from GUI."""
        self.source_coding.value = CODEC_LANGS[str(encoding_key)]
        self._csv_source.encoding = self.source_coding.value
        self.collect_preview_values()

    @qt_compat.Slot()
    def collect_preview_values(self):
        """Collect preview data from csv file."""
        no_rows = self.no_preview_rows.value
        row_offset = self.data_start_row.value - 1

        if self.headers.value:
            headers_row = self.header_row.value - 1
        else:
            headers_row = -1
        if self.units.value:
            units_row = self.unit_row.value - 1
        else:
            units_row = -1
        if self.descriptions.value:
            descriptions_row = self.description_row.value - 1
        else:
            descriptions_row = -1

        if self._csv_source.valid_encoding:
            self.get_preview.emit(
                no_rows, 0, row_offset, headers_row, units_row,
                descriptions_row)
        else:
            error_string = 'Invalid encoding'
            self.data_table = table.File()
            self.data_table.set_column_from_array(
                'X0', np.array([error_string]))

        self.update_table.emit()

    @qt_compat.Slot(table.File)
    def set_preview_table(self, data_table):
        self.data_table = data_table
        self.update_table.emit()


class ImporterXLS(object):
    """Class for importation of data in the xls format."""

    def __init__(self, fq_infilename):
        def raise_mixed_types(x):
            class MixedTypesError(Exception):
                pass
            raise MixedTypesError()

        self._fq_infilename = fq_infilename

        self._xl_cell_to_num = {
            xlrd.XL_CELL_TEXT: raise_mixed_types,
            xlrd.XL_CELL_NUMBER: lambda x: x,
            xlrd.XL_CELL_DATE: raise_mixed_types,
            xlrd.XL_CELL_BOOLEAN: float,
            xlrd.XL_CELL_ERROR: raise_mixed_types,
            xlrd.XL_CELL_EMPTY: lambda x: np.NaN,
            xlrd.XL_CELL_BLANK: lambda x: np.NaN}

        self._xl_cell_to_date = {
            xlrd.XL_CELL_TEXT: unicode,
            xlrd.XL_CELL_NUMBER: raise_mixed_types,
            xlrd.XL_CELL_DATE: self.date,
            xlrd.XL_CELL_BOOLEAN: raise_mixed_types,
            xlrd.XL_CELL_ERROR: raise_mixed_types,
            xlrd.XL_CELL_EMPTY: lambda x: None,
            xlrd.XL_CELL_BLANK: lambda x: None}

        self._xl_cell_to_str = {
            xlrd.XL_CELL_TEXT: unicode,
            xlrd.XL_CELL_NUMBER: unicode,
            xlrd.XL_CELL_DATE: lambda x: unicode(self.date(x)),
            xlrd.XL_CELL_BOOLEAN: lambda x: unicode(bool(x)),
            xlrd.XL_CELL_ERROR: lambda x: unicode(
                xlrd.error_text_from_code[x]),
            xlrd.XL_CELL_EMPTY: unicode,
            xlrd.XL_CELL_BLANK: unicode}

        self._xl_cell_to_bool = {
            xlrd.XL_CELL_TEXT: raise_mixed_types,
            xlrd.XL_CELL_NUMBER: lambda x: x != 0,
            xlrd.XL_CELL_DATE: raise_mixed_types,
            xlrd.XL_CELL_BOOLEAN: bool,
            xlrd.XL_CELL_ERROR: raise_mixed_types,
            xlrd.XL_CELL_EMPTY: lambda x: False,
            xlrd.XL_CELL_BLANK: lambda x: False}

    def _datetimes_or_timedeltas(self, x):
        """
        If there are any datetimes in the list, coerce everything into
        datetimes, else coerce everything inte timedeltas.
        """
        has_datetimes = False
        for value in x:
            if isinstance(value, datetime.datetime):
                has_datetimes = True

        if has_datetimes:
            # There is at least one datetime. Turn everything into datetimes.
            new_x = []
            for value in x:
                if value is None:
                    new_x.append(datetime.datetime(1900, 1, 1))
                elif isinstance(value, datetime.timedelta):
                    new_x.append(value + datetime.datetime(1900, 1, 1))
                else:
                    new_x.append(value)
            return new_x
        else:
            # There are no datetimes. Turn everything into timedeltas.
            new_x = []
            for value in x:
                if value is None:
                    new_x.append(datetime.timedelta(0))
                else:
                    new_x.append(value)
            return new_x

    def date(self, x):
        dtuple = xlrd.xldate_as_tuple(x, self._datemode)
        if dtuple[0] > 0:
            return datetime.datetime(*dtuple)

        elif sum(dtuple[:3]) == 0:
            return datetime.timedelta(
                hours=dtuple[3], minutes=dtuple[4], seconds=dtuple[5])
        else:
            assert False, 'Months or days without year cannot be represented'

    def date_str(self, x):
        return unicode(self.date(x))

    def get_row_to_array(
            self, ws, row, data_start_column=0, data_end_column=None):
        """Read a row in the xls file and returns it as an array."""
        return self._to_array(ws, 'row', row,
                              data_start=data_start_column,
                              data_end=data_end_column)

    def get_column_to_array(
            self, ws, column, data_start_row=0, data_end_row=None):
        """Read a column in the xls file and returns it as an array."""
        return self._to_array(ws, 'column', column,
                              data_start=data_start_row,
                              data_end=data_end_row)

    def _to_array(self, ws, alignment, i, data_start=0, data_end=None):
        """Read a row/column in the xls file and returns it as an array."""
        if alignment == 'row':
            ws_types = ws.row_types
            ws_values = ws.row_values
        elif alignment == 'column':
            ws_types = ws.col_types
            ws_values = ws.col_values
        else:
            raise ValueError("Invalid alignment: {}. Should be either "
                             "'row' or 'column'.".format(alignment))

        values = ws_values(i, data_start, data_end)
        types = ws_types(i, data_start, data_end)
        non_empty_types = set(types) - {xlrd.XL_CELL_EMPTY,
                                        xlrd.XL_CELL_BLANK}

        converter = self._xl_cell_to_str
        list_converter = lambda x: x
        if xlrd.XL_CELL_TEXT in non_empty_types:
            converter = self._xl_cell_to_str
        else:
            if len(non_empty_types) >= 2:
                converter = self._xl_cell_to_str
            elif xlrd.XL_CELL_DATE in non_empty_types:
                # There are only datetimes/timedeltas in this row/col
                converter = self._xl_cell_to_date
                list_converter = self._datetimes_or_timedeltas
            elif xlrd.XL_CELL_BOOLEAN in non_empty_types:
                # There are only booleans in this row/col
                converter = self._xl_cell_to_bool
            elif xlrd.XL_CELL_NUMBER in non_empty_types:
                # There are only numbers in this row/col
                converter = self._xl_cell_to_num

        return np.array(list_converter(
            [converter[t](v) for t, v in izip(types, values)]))

    def import_xls(self, out_table, sheet_name,
                   data_start, data_end,
                   transposed, headers_row_offset=-1,
                   units_row_offset=-1,
                   descriptions_row_offset=-1):
        """Adminstration method for the importation of data in xls format."""
        with open_workbook(self._fq_infilename) as wb:
            self._datemode = wb.datemode
            try:
                ws = wb.sheet_by_name(sheet_name)
            except xlrd.XLRDError:
                # This is used if called from the auto importer or if the
                # config is incorrect.
                ws = wb.sheet_by_index(0)
            out_table.set_name(sheet_name)

            if transposed:
                nr_rows = ws.ncols
                nr_cols = ws.nrows
                data_collector = self.get_row_to_array
                header_collector = self.get_column_to_array
            else:
                nr_rows = ws.nrows
                nr_cols = ws.ncols
                data_collector = self.get_column_to_array
                header_collector = self.get_row_to_array

            if data_end < 0:
                data_end = nr_rows + data_end
            elif data_end == 0:
                data_end = nr_rows
            else:
                pass

            if headers_row_offset >= 0:
                headers = [unicode(x) for x in
                           header_collector(ws, headers_row_offset)]
            else:
                headers = [
                    'f{0}'.format(index) for index in xrange(nr_cols)]

            if units_row_offset >= 0:
                units = [unicode(x) for x in
                         header_collector(ws, units_row_offset)]
            else:
                units = None

            if descriptions_row_offset >= 0:
                descs = [unicode(x) for x in
                         header_collector(ws, descriptions_row_offset)]
            else:
                descs = None

            for col in xrange(nr_cols):
                if not headers[col]:
                    continue
                attr = {}
                out_table.set_column_from_array(
                    headers[col], data_collector(
                        ws, col, data_start, data_end))
                if units:
                    attr['unit'] = units[col]
                if descs:
                    attr['description'] = descs[col]

                out_table.set_column_attributes(headers[col], attr)


class ImporterCSV(object):
    """Importer class for data in csv format."""

    def __init__(self, csv_source):
        self._source = csv_source
        self._partial_read = False

    def set_partial_read(self, value):
        self._partial_read = value

    def import_csv(self, out_table,
                   nr_data_rows, data_foot_rows, data_row_offset,
                   headers_row_offset=-1,
                   units_row_offset=-1,
                   descriptions_row_offset=-1,
                   require_num=True,
                   read_csv_full_rows=False):
        """Adminstration method for the importation of data in csv format."""
        self._discard = False
        self._require_num = require_num

        data_table = self._data_as_table(
            nr_data_rows, data_foot_rows, data_row_offset,
            read_csv_full_rows)

        if read_csv_full_rows:
            out_table.update(data_table)
            return

        if headers_row_offset >= 0:
            header_table = self._collect_single_row(headers_row_offset)
            unit_table = table.File()
            desc_table = table.File()

            if units_row_offset >= 0:
                unit_table = self._collect_single_row(units_row_offset)
            if descriptions_row_offset >= 0:
                desc_table = self._collect_single_row(descriptions_row_offset)

            for column_name in header_table.column_names():
                header = unicode(
                    header_table.get_column_to_array(column_name)[0])
                attr = {}

                if header:

                    try:
                        out_table.update_column(
                            header, data_table, column_name)
                    except KeyError:
                        empty_column = np.array(
                            [u''] * data_table.number_of_rows())
                        out_table.set_column_from_array(header, empty_column)

                    try:
                        unit = unit_table.get_column_to_array(column_name)[0]
                        attr['unit'] = unicode(unit)
                    except KeyError:
                        pass

                    try:
                        description = desc_table.get_column_to_array(
                            column_name)[0]
                        attr['description'] = unicode(description)
                    except KeyError:
                        pass

                    if attr:
                        out_table.set_column_attributes(
                            header, attr)

                else:
                    pass

        else:
            out_table.update(data_table)

    def _collect_single_row(self, row_offset):
        """
        Import a single line from the csv-file. This method is used for
        header, units and descriptions.
        """
        no_rows = 1
        require_num = False
        return self._source.read_part(no_rows, row_offset, require_num)

    def _data_as_table(self, no_rows, foot_rows, offset_rows, full_rows):
        """
        Merges the imported data, stored in one or many Tables, into a single
        Table.
        """
        out_table = table.File()

        if full_rows:
            table_list = self._data_as_tables_full_rows(
                no_rows, offset_rows)
        else:
            table_list = self._data_as_tables(
                no_rows, foot_rows, offset_rows)

        if len(table_list) > 1:
            out_table.vjoin(table_list, '', '', True, 0)
        elif len(table_list) == 1:
            out_table = table_list[0]

        if foot_rows > 0 and not self._discard:
            return out_table[:-foot_rows]
        else:
            return out_table

    def _data_as_tables(self, no_rows, foot_rows, offset_rows, iter_count=0):
        """
        Import data from csv-file in chunks. Each chunk is represented
        by a Table in the list, table_list.
        """
        table_list = []
        iter_count += 1

        if iter_count > ITER_LIMIT:
            message = ('Process has ended because the number of calls '
                       'of the method "_data_as_tables" have passed the '
                       'allowed limit, {0}'.format(ITER_LIMIT))
            raise Exception(message)

        if no_rows <= 0:
            try:
                table_list.append(self._source.read_to_end_no_chunks(
                    offset_rows, self._require_num))
            except TooManyColumnsError as tmce:
                table_list.extend(self._split_reading_whole_file(
                    tmce.line, offset_rows, iter_count))

        elif no_rows > 0:
            try:
                table_list.append(self._source.read_part(
                    no_rows, offset_rows, self._require_num))
            except TooManyColumnsError as tmce:
                table_list.extend(self._split_reading_part_file(
                    tmce.line, offset_rows, no_rows, iter_count))
        else:
            raise Exception('Not valid number of rows to read.')

        return table_list

    def _data_as_tables_full_rows(self, no_rows, offset_rows):
        """Import data from csv-file as whole rows."""
        if no_rows == -1:
            return self._source.read_to_end_full_rows(offset_rows)
        elif no_rows > 0:
            return self._source.read_part_full_rows(no_rows, offset_rows)
        else:
            raise Exception('Not valid number of rows to read.')

    def _split_reading_whole_file(self, line, offset_rows, iter_count):
        """Method called if the number of columns in a row is higher than
        expected by pandas.io.parser. The reading from the csv file is
        splited into two readings. This method is used when the whole
        csv file is imported.
        """
        out_list = []

        no_rows_1 = line - 1 - offset_rows
        offset_1 = offset_rows
        offset_2 = line - 1

        if offset_1 == offset_2:
            self._discard_warning(offset_1)
            return out_list

        out_list.extend(
            self._data_as_tables(no_rows_1, 0, offset_1, iter_count))

        out_list.extend(
            self._data_as_tables(-1, 0, offset_2, iter_count))

        return out_list

    def _split_reading_part_file(self, line, offset_rows,
                                 no_rows, iter_count):
        """Method called if the number of columns in a row is higher than
        expected by pandas.io.parser. The reading from the csv file is
        splited into two readings. This method is used when only a part of
        the csv file is imported.
        """
        out_list = []

        no_rows_1 = line - 1 - offset_rows
        offset_1 = offset_rows
        no_rows_2 = no_rows - no_rows_1
        offset_2 = line - 1

        if offset_1 == offset_2:
            self._discard_warning(offset_1)
            return out_list
        if (no_rows + offset_rows) < line:
            raise SyDataError(
                'File is corrupt, error in row: {}'.format(line))

        out_list.extend(
            self._data_as_tables(no_rows_1, 0, offset_1, iter_count))

        out_list.extend(
            self._data_as_tables(no_rows_2, 0, offset_2, iter_count))

        return out_list

    def _discard_warning(self, row):
        if self._partial_read:
            sywarn(
                'Error in row: {}, discarding it and every row below.'.format(
                    row + 1))
            self._discard = True
        else:
            raise SyDataError(
                'File is corrupt, error in row: {}'.format(row + 1))


class TableSourceCSV(object):
    DEFAULT_DELIMITER = ';'
    """
    This class is the layer between the physical csv-file and the importation
    routines.
    """

    def __init__(self, fq_infilename, delimiter=None, encoding=None):
        self._fq_infilename = fq_infilename
        self._filesize = os.path.getsize(fq_infilename)
        self._delimiter = self.DEFAULT_DELIMITER
        self._chunksize = None

        if encoding is None:
            self._encoding = self._sniff_encoding()
        else:
            self._valid_encoding = self._check_encoding(encoding, delimiter)
            self._encoding = encoding

        if delimiter is None:
            self._delimiter = self._sniff_delimiter()
        else:
            self._delimiter = str(delimiter)

        self._has_header = self._sniff_header()

        self._no_rows = None

    def filesize(self):
        """Return filesize of csv-file."""
        return self._filesize

    @property
    def nrows(self):
        """Return the number of row in csv-file, call counter
        if value is not known.
        """
        if self._no_rows is None:
            self._no_rows = self._row_counter()
        return self._no_rows

    @property
    def delimiter(self):
        """Return present delimiter."""
        return self._delimiter

    @delimiter.setter
    def delimiter(self, delimiter):
        """Set delimiter fromthe outside."""
        self._delimiter = str(delimiter)

    @property
    def encoding(self):
        """Return present encoding."""
        return self._encoding

    @encoding.setter
    def encoding(self, encoding):
        """Set encoding of file from outside the source class."""
        self._encoding = encoding
        self._valid_encoding = self._check_encoding(
            self._encoding, self._delimiter)
        self._no_rows = None

    @property
    def chunksize(self):
        """Return present encoding."""
        return self._chunksize

    @chunksize.setter
    def chunksize(self, chunksize):
        """Set chunksize when reading from outside the source class."""
        self._chunksize = chunksize

    @property
    def object(self):
        """Open and return csv-file as file object."""
        self._csvfile = codecs.open(
            self._fq_infilename, mode='rb', encoding=self._encoding)
        return self._csvfile

    def close_object(self):
        """Close open csv-file."""
        self._csvfile.close()

    @property
    def has_header(self):
        """Return True if if header has been found in csv-file."""
        return self._has_header

    def read_to_end_full_rows(self, offset):
        """Quick call for importation of data in csv-file as full rows."""
        return self._read_full_rows(-1, offset)

    def read_part_full_rows(self, no_rows, offset):
        """
        Quick call for importation of a part of data in csv-file
        as full rows.
        """
        return self._read_full_rows(no_rows, offset)

    def read_to_end_no_chunks(self, offset, req_num):
        """
        Quick call for read the whole csv-file. The method gets
        a dataframe from _read and return a table to caller.
        """
        return table.File().from_dataframe(
            self._read(row_offset=offset,
                       require_num=req_num).dropna(how='all'))

    def read_part(self, no_rows, offset, req_num):
        """
        Quick call for just read a part of the csv-file. The method gets
        a dataframe from _read and return a table to caller.
        """
        return table.File().from_dataframe(
            self._read(no_rows=no_rows,
                       row_offset=offset,
                       require_num=req_num).dropna(how='all'))

    def _read(self, no_rows=None, row_offset=None, foot_rows=None,
              require_num=True, chunksize=None):
        """Administration of the reading of csv-files with pandas."""
        encoding = self._encoding
        delimiter = self._delimiter

        # Detect utf_8 BOM and change encoding if it is there.
        if encoding == 'utf_8':
            with open(self._fq_infilename) as f:
                if f.read(len(codecs.BOM_UTF8)) == codecs.BOM_UTF8:
                    encoding = 'utf_8_sig'

        if delimiter != '':
            if encoding.startswith('utf_16'):
                return self._read_python(
                    no_rows, row_offset, encoding,
                    delimiter, foot_rows, chunksize)
            else:
                return self._read_c(
                    no_rows, row_offset, encoding,
                    delimiter, foot_rows, require_num, chunksize)
        else:
            if chunksize is not None:
                return [pd.DataFrame()]
            else:
                return pd.DataFrame()

    def _read_sniff(self, no_rows=None, row_offset=None,
                    encoding=None, delimiter=None):
        """Quick call used by the sniffer methods."""
        chunksize = None
        foot_rows = 0

        return self._read_python(
            no_rows, row_offset, encoding, delimiter, foot_rows, chunksize)

    def _read_c(self, no_rows, row_offset, encoding,
                delimiter, foot_rows, require_num, chunksize):
        """Method for reading csv file with pandas.io.parsers.read_csv,
        c engine.
        """
        try:
            if StrictVersion(pd.__version__) >= StrictVersion('0.15.0'):
                return PANDAS_CSV_READER(self._fq_infilename,
                                         sep=delimiter,
                                         skipinitialspace=True,
                                         header=None,
                                         prefix='X',
                                         skiprows=row_offset,
                                         skipfooter=foot_rows,
                                         nrows=no_rows,
                                         chunksize=chunksize,
                                         encoding=encoding,
                                         doublequote=False,
                                         engine='c',
                                         na_filter=require_num,
                                         skip_blank_lines=False)
            else:
                sywarn(
                    'The csv import routine is optimized to work '
                    'with pandas v.0.15.0 or newer. '
                    'Your present verison is {}'.format(pd.__version__))
                return PANDAS_CSV_READER(self._fq_infilename,
                                         sep=delimiter,
                                         skipinitialspace=True,
                                         header=None,
                                         prefix='X',
                                         skiprows=row_offset,
                                         skipfooter=foot_rows,
                                         nrows=no_rows,
                                         chunksize=chunksize,
                                         encoding=encoding,
                                         doublequote=False,
                                         engine='c',
                                         na_filter=require_num)

        except Exception as message:
            errorline = re.match(TOO_MANY_COLUMNS, str(message))

            if errorline:
                raise TooManyColumnsError(
                    message, int(errorline.groups(0)[0]))
            else:
                errorline = re.match(END_OF_LINE, str(message))
                if errorline:
                    raise TooManyColumnsError(
                        message, int(errorline.groups(0)[0]) + 1)
                else:
                    return self._read_python(no_rows,
                                             row_offset,
                                             encoding,
                                             delimiter,
                                             foot_rows,
                                             chunksize)

    def _read_python(
            self, no_rows, row_offset, encoding,
            delimiter, foot_rows, chunksize):
        """Method for reading csv file with pandas.io.parsers.read_csv,
        python engine.
        """
        try:
            if StrictVersion(pd.__version__) >= StrictVersion('0.15.0'):
                return PANDAS_CSV_READER(self._fq_infilename,
                                         sep=delimiter,
                                         skipinitialspace=True,
                                         header=None,
                                         prefix='X',
                                         skiprows=row_offset,
                                         skipfooter=foot_rows,
                                         nrows=no_rows,
                                         chunksize=chunksize,
                                         encoding=encoding,
                                         doublequote=False,
                                         engine='python',
                                         skip_blank_lines=False)
            else:
                sywarn(
                    'The csv import routine is optimized to work '
                    'with pandas v.0.15.0 or newer. '
                    'Your present verison is {}'.format(pd.__version__))
                return PANDAS_CSV_READER(self._fq_infilename,
                                         sep=delimiter,
                                         skipinitialspace=True,
                                         header=None,
                                         prefix='X',
                                         skiprows=row_offset,
                                         skipfooter=foot_rows,
                                         nrows=no_rows,
                                         chunksize=chunksize,
                                         encoding=encoding,
                                         doublequote=False,
                                         engine='python')

        except Exception as message:
            errorline = re.match(TOO_MANY_COLUMNS, str(message))

            if errorline:
                raise TooManyColumnsError(
                    message, int(errorline.groups(0)[0]))
            else:
                errorline = re.match(END_OF_LINE, str(message))
                if errorline:
                    raise TooManyColumnsError(
                        message, int(errorline.groups(0)[0]) + 1)
                else:
                    raise

    def _read_full_rows(self, no_rows, offset):
        encoding = self._encoding
        table_list = []

        with codecs.open(self._fq_infilename,
                         mode='rb',
                         encoding=encoding) as csvfile:

            try:
                for row in xrange(offset):
                    csvfile.next()
            except StopIteration:
                return table_list

            if no_rows > 0:
                out_table = table.File()
                data_list = []
                try:
                    for x in xrange(no_rows):
                        data_list.append(csvfile.next().strip())
                except StopIteration:
                    return table_list
                out_table.set_column_from_array(
                    'X0', np.array(data_list))
                table_list.append(out_table)
            else:
                byte_to_end = self.filesize() - csvfile.tell()
                while byte_to_end > CHUNK_BYTE_LIMIT:
                    out_table = table.File()
                    data_list = []
                    for x in xrange(CHUNK_ROW_LIMIT):
                        data_list.append(csvfile.next().strip())

                    out_table.set_column_from_array(
                        'X0', np.array(data_list))
                    table_list.append(out_table)
                    byte_to_end = self.filesize() - csvfile.tell()

                out_table = table.File()
                data = np.array(csvfile.read().split('\n'))
                if data[-1] == '':
                    data = data[:-1]

                if len(data):
                    out_table.set_column_from_array('X0', data)
                table_list.append(out_table)

        return table_list

    @property
    def valid_file(self):
        """Return True if file is a csv-file."""
        return self._check_file_validity()

    @property
    def valid_encoding(self):
        """Return True if valid encoding has been determined."""
        return self._valid_encoding

    def _check_file_validity(self):
        """Check if incoming file is a valid csv-file."""
        not_allowed_extensions = ['xls', 'xlsx']
        extension = os.path.splitext(self._fq_infilename)[1][1:]
        if extension in not_allowed_extensions:
            return False
        else:
            return self._valid_encoding

    def _row_counter(self):
        """Count the number of rows in csv-file."""
        def blocks(files, size=65536):
            while True:
                b = files.read(size)
                if not b:
                    break
                yield b

        if self._valid_encoding:
            line_nr = 0
            with open(self._fq_infilename, 'r') as f:
                line_nr = sum(bl.count('\n') for bl in blocks(f))
            return line_nr + 1
        else:
            return -1

    def _sniff_encoding(self):
        """Sniff if either utf_8, iso8859_1 or utf_16 is a valid encodings."""
        default_encoding = 'utf_8'
        # encodings = ['utf_8', 'utf_16', 'iso8859_1']
        encodings = ['utf_8', 'utf_16', 'utf_16_le', 'utf_16_be', 'iso8859_1']
        # First, test without delimiter.
        for encoding in encodings:
            if self._check_encoding(encoding):
                self._valid_encoding = True
                return encoding

        self._valid_encoding = False
        return default_encoding

    def _check_encoding(self, encoding, delimiter=None):
        """Check if incoming encoding is valid."""
        def check_small_file(csvfile, check=True):
            return checker(csvfile.read(), check)

        def check_large_file(csvfile, encoding, check=True):
            valid_start = checker(csvfile.read(SNIFF_LIMIT))
            if encoding != 'utf_16':
                csvfile.seek(-SNIFF_LIMIT, os.SEEK_END)
                valid_end = checker(csvfile.read(), check)
            else:
                valid_end = True

            return (valid_start and valid_end)

        def checker(sniff_text, check=True):
            if not check:
                return True

            row_split = sniff_text.split('\n')
            if len(row_split) > 1:
                return True
            return False

        def check_file():
            return valid_encoding

        valid_encoding = True
        has_newlines = False

        with open(self._fq_infilename) as csvfile:
            data = csvfile.readline()
            if data == '':
                return True

            has_newlines = '\n' in data

        with codecs.open(self._fq_infilename,
                         mode='rb',
                         encoding=encoding) as csvfile:
            try:
                if self._filesize > SNIFF_LIMIT:
                    valid_encoding = check_large_file(
                        csvfile, encoding, has_newlines)
                else:
                    valid_encoding = check_small_file(csvfile, has_newlines)
            except Exception:
                valid_encoding = False

        return valid_encoding

    def _sniff_delimiter(self):
        """Method tries to determine a valid delimiter."""
        if self._valid_encoding:
            best = self.DEFAULT_DELIMITER
            best_count = 0
            smallest_diff = 1000
            num_lines = 50
            encoding = self._encoding

            delimiters = CSV_FILE_DELIMITERS.values()
            counts = []

            for delimiter in delimiters:
                try:
                    # First row not included. High probability to
                    # be the header row which can include a lot of spaces
                    counts.append(self._read_sniff(
                        no_rows=num_lines,
                        row_offset=1,
                        encoding=encoding,
                        delimiter=delimiter).shape[1])
                except Exception:
                    counts.append(None)
            try:
                count, delimiter = max(zip(counts, delimiters))
                if count > 1:
                    return delimiter
            except ValueError:
                pass

            # Slower fallback method of determining delimiter if the
            # fast one fails to give a delimiter.

            for delimiter in delimiters:
                counts = []

                for offset in xrange(num_lines):
                    try:
                        data_frame = self._read_sniff(
                            no_rows=1,
                            row_offset=offset,
                            encoding=encoding,
                            delimiter=delimiter)
                        counts.append(data_frame.shape[1])
                    except Exception:
                        pass

                if not counts:
                    continue

                if (abs(min(counts) - max(counts)) < smallest_diff and
                        max(counts) > 1):
                    best = delimiter
                    best_count = max(counts)
                    smallest_diff = abs(min(counts) - max(counts))
                elif (abs(min(counts) - max(counts)) == smallest_diff and
                        max(counts) > best_count):
                    best = delimiter
                    best_count = max(counts)
                    smallest_diff = abs(min(counts) - max(counts))
                else:
                    pass

            return best
        else:
            return str(self.DEFAULT_DELIMITER)

    def _sniff_header(self):
        """Method tries to determine if there exist a header in csv-file."""
        if self._valid_encoding:
            try:
                header_table = self.read_part(1, 0, False)
                data_table = self.read_part(20, 1, True)
            except:
                return False

            if data_table.number_of_rows() < 1:
                return False

            if (header_table.number_of_columns() <
                    data_table.number_of_columns()):
                return False

            has_header = 0
            for column in header_table.column_names():
                header_array = header_table.get_column_to_array(column)
                try:
                    data_array = data_table.get_column_to_array(column)
                except KeyError:
                    if header_array[0] == u'':
                        continue
                    else:
                        return False

                if header_array.dtype != data_array.dtype:
                    has_header += 1

            return has_header > 0

        else:
            return False


class TooManyColumnsError(Exception):
    """Exception raised when the number of columns are higher than Pandas has
    expected in a row.
    """

    def __init__(self, value, line):
        self._value = value
        self.line = line

    def __str__(self):
        return repr(self._value)
