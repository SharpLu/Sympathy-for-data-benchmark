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
"""
Importer of the ComTest file format
"""
import datetime
import time
import os
import string
import re

from itertools import izip
import numpy as np

from sympathy.api import importers
from sympathy.api import table
from sympathy.api.exceptions import SyDataError
from sylib.table_sources import ImporterCSV, TableSourceCSV


LAA_TB_COLUMN = 'TimeDateRel'
LAA_DELIMITER = '\t'
LAA_ENCODING = 'iso8859_1'
META_FOOT_ROWS = 0
DATA_FOOT_ROWS = 0
DATA_NO_ROWS = -1


class DataImportLAA(importers.base.ADAFDataImporterBase):
    """ Importation of laa, lab, daa and dab data into the ADAF format. """
    IMPORTER_NAME = 'LAA'

    def __init__(self, fq_infilename, parameters):
        super(DataImportLAA, self).__init__(fq_infilename, parameters)

    def valid_for_file(self):
        pass

    def import_data(self, out_adaffile, parameters=None, progress=None):
        """
        Main method in the process of importing laa, lab, daa and dab files.
        """
        fq_filename_list = self._generate_filename_list()

        if len(fq_filename_list) == 0:
            raise SyDataError('No files in filename list.')

        basefilename, _ = os.path.splitext(os.path.basename(
            fq_filename_list[0]))
        out_adaffile.set_source_id(basefilename)

        numerical_data_tables = {'res': table.File(),
                                 'ts': table.File()}

        for filename in fq_filename_list:
            # print 'Importing data from {0}'.format(filename)
            table_source = TableSourceCSV(filename,
                                          delimiter=LAA_DELIMITER,
                                          encoding=LAA_ENCODING)
            self._importer = ImporterCSV(table_source)

            num_data_start_row = self._parse_and_store_metadata(
                filename, out_adaffile.meta)

            self._import_numerical_data(
                filename, num_data_start_row, numerical_data_tables)

        self._adaf_res_writer(out_adaffile, numerical_data_tables['res'])
        self._adaf_ts_writer(out_adaffile, numerical_data_tables['ts'])

    def _generate_filename_list(self):
        """
        Find files with the same filename, except extension.
        These are connected to each other and the data of the files
        should be imported to the same ADAF.
        """
        fq_filename, extension = os.path.splitext(self._fq_infilename)

        la_ext_list = [
            'la{0}'.format(char) for char in string.lowercase]
        da_ext_list = [
            'da{0}'.format(char) for char in string.lowercase]

        extension_list = la_ext_list + da_ext_list

        filename_list = [fq_filename + '.{0}'.format(ext)
                         for ext in extension_list
                         if os.path.exists(fq_filename + '.{0}'.format(ext))]

        return filename_list

    def _parse_and_store_metadata(self, filename, meta_container):
        """Parse file to get rows and headers of metadata categories."""
        # Regular expression to detect headers for metadatagroups.
        # As far as we know the headers starts with a backslash, \,
        # and ends with a colon, :. (Daniel Hedendahl, 2013-04-03)
        reg_exp = r'^\\.*:$'
        meta_table = table.File()
        with open(filename) as fid:

            for row_number, line in enumerate(fid):
                message = re.search(reg_exp, line.strip())

                if message is not None:
                    header = unicode(
                        message.group().lstrip('\\').rstrip(':'), LAA_ENCODING)
                    if header in ['data', 'Data']:
                        meta_container.from_table(meta_table)
                        return row_number
                else:
                    line_list = unicode(line.strip(), LAA_ENCODING).split(
                        LAA_DELIMITER)

                    if len(line_list) == 2:
                        name_unit, value = tuple(line_list)

                        try:
                            name, unit = tuple(name_unit.split('('))
                            unit = unit.strip().rstrip(')')
                        except ValueError:
                            name = name_unit.split('(')[0]
                            unit = '-'

                        name = self._replace_bad_signal_header(name.strip())

                        full_header = unicode(
                            (header + '/' + name).replace(' ', '_'))
                        value_array = np.array([
                            self._int_float_or_str(value.strip())])
                        attributes = {'unit': unit,
                                      'category': header}

                        meta_table.set_column_from_array(
                            full_header, value_array)
                        meta_table.set_column_attributes(
                            full_header, attributes)

    def _int_float_or_str(self, value):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def _import_metadata(self, filename, headers, rows, meta_container):
        """Importation of the metadata in the header of the file."""
        for header, row1, row2 in izip(headers[0:-1], rows[0:-1], rows[1:]):
            nr_rows = row2 - row1 - 2
            offset = row1 + 1
            metadata_table = table.File()
            self._importer.import_csv(
                metadata_table, nr_rows, META_FOOT_ROWS, offset)

            if metadata_table.number_of_columns() == 2:
                for name_unit, value in zip(
                        metadata_table.get_column_to_array('X0'),
                        metadata_table.get_column_to_array('X1')):

                    try:
                        name, unit = tuple(name_unit.split('('))
                        unit = unit.strip().rstrip(')')
                    except ValueError:
                        name = name_unit.split('(')[0]
                        unit = '-'
                    name = self._replace_bad_signal_header(name.strip())

                    attributes = {'unit': unit,
                                  'category': header}

                    full_header = (header + '/' + name).replace(' ', '_')

                    try:
                        meta_container.create_column(
                            unicode(full_header),
                            value.reshape((1,)),
                            attributes)
                    except KeyError:
                        pass

    def _VAT_signals(self, in_table):
        """
        The names of the VAT-signala are changed into the names
        defined in the descriptions fields.
        """
        out_table = table.File()
        for column in in_table.column_names():
            try:
                if 'VAT' in column:
                    description = (
                        in_table.get_column_attributes(column)['description'])
                    if '.D' in column:
                        new_header = self._replace_bad_signal_header(
                            '{0}_D'.format(description))
                    else:
                        new_header = self._replace_bad_signal_header(
                            description)
                else:
                    new_header = self._replace_bad_signal_header(column)

                out_table.update_column(new_header, in_table, column)
            except TypeError:
                pass

        return out_table

    def _replace_bad_signal_header(self, header):
        """Replacment of bad signal headers."""
        header = unicode(header)
        header = header.replace("( )", "")
        header = header.replace("-", "_")
        header = header.replace("/", "_")
        header = header.replace('\\', "_")
        header = header.replace("____", "_")
        header = header.replace("___", "_")
        header = header.replace("__", "_")
        header = header.replace(" ", "_")
        header = header.replace(".", "_")

        return header

    def _import_numerical_data(self, filename, start_row, table_dict):
        """
        Method collects data from file and pass it to corresponding writer.
        """
        head_offset = start_row + 1
        desc_offset = start_row + 2
        unit_offset = start_row + 3
        data_offset = start_row + 4

        data_table = table.File()
        self._importer.import_csv(
            data_table, DATA_NO_ROWS, DATA_FOOT_ROWS, data_offset,
            headers_row_offset=head_offset,
            units_row_offset=unit_offset,
            descriptions_row_offset=desc_offset)

        data_table = self._VAT_signals(data_table)

        container = self._numerical_container_factory(
            os.path.splitext(filename)[1])

        table_dict[container].hjoin(data_table)

        # numerical_data_writer(adaffile, data_table)

    def _numerical_container_factory(self, extension):
        """ The factory returns writer depending on the file extension."""
        if extension[:3] == '.la':
            return 'res'
        elif extension[:3] == '.da':
            return 'ts'
        else:
            raise Exception('Unknown file extension.')

    def _adaf_res_writer(self, adaffile, data_table):
        """Write the imported data to the result container."""
        if (data_table.number_of_columns() > 0 and
                data_table.number_of_rows() > 0):
            adaffile.res.from_table(data_table)

    def _obtain_time_basis(self, abs_time_array):
        """
        A new timebasis array is calculated from the values
        in the column TimeDateAbs. At the moment of developing this
        importion routine the column TimeDataRel could not serve as
        timebasis array.
        """

        time_basis_array = np.ones(abs_time_array.size, dtype=np.float)
        zero_datetime_str = abs_time_array[0]

        micro_seconds = int(zero_datetime_str[15:]) * 1000

        zero_datetime = datetime.datetime(int(zero_datetime_str[:4]),
                                          int(zero_datetime_str[4:6]),
                                          int(zero_datetime_str[6:8]),
                                          int(zero_datetime_str[9:11]),
                                          int(zero_datetime_str[11:13]),
                                          int(zero_datetime_str[13:15]),
                                          micro_seconds)

        zero_timestamp = int(
            time.mktime(zero_datetime.timetuple()) * 1e3 +
            zero_datetime.microsecond / 1e3)

        for ii, value in enumerate(abs_time_array):
            micro_seconds = int(value[15:]) * 1000

            zero_datetime = datetime.datetime(int(value[:4]),
                                              int(value[4:6]),
                                              int(value[6:8]),
                                              int(value[9:11]),
                                              int(value[11:13]),
                                              int(value[13:15]),
                                              micro_seconds)

            timestamp = int(
                time.mktime(zero_datetime.timetuple()) * 1e3 +
                zero_datetime.microsecond / 1e3)

            time_basis_array[ii] = timestamp - zero_timestamp

        time_diff = time_basis_array[1] - time_basis_array[0]

        return time_diff, time_basis_array

    def _adaf_ts_writer(self, adaffile, data_table):
        """Write the imported data to the timeseries container."""
        if (data_table.number_of_columns() > 0 and
                data_table.number_of_rows() > 0):
            sampling_rate = 0.0
            try:
                time_rel_array = data_table.get_column_to_array(
                    LAA_TB_COLUMN)
                ms_per_day_night = 60 * 60 * 24 * 1000

                time_basis = ms_per_day_night * time_rel_array
                sampling_rate = time_basis[1] - time_basis[0]

                attr = {'unit': u'ms',
                        'description': u'Timebasis',
                        'sampling_rate': sampling_rate}

                data_table.set_column_from_array('TimeBasis', time_basis)
                data_table.set_column_attributes('TimeBasis', attr)

            except IndexError:
                raise SyDataError(
                    'The considered daa/dab-file does not include the column '
                    'TimeDateRel. A timebasis could not be created.')

            tbasis = adaffile.sys

            try:
                system = tbasis[u'ComTest']
            except KeyError:
                system = tbasis.create(u'ComTest')

            raster_name = 'Group0'
            try:
                raster = system[raster_name]
            except KeyError:
                raster = system.create(raster_name)

            raster.from_table(data_table, 'TimeBasis')
