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
import binascii
import datetime
import numpy as np
import pyodbc
import re
import sqlite3
from decimal import Decimal
from contextlib import contextmanager


class FileDatabase(object):
    def __init__(self, fq_filename):
        self.fq_filename = fq_filename

    def is_valid(self):
        raise NotImplementedError

    def to_rows_table(self, table_name, columns=None):
        raise NotImplementedError

    def to_rows_query(self, query):
        raise NotImplementedError

    def table_names(self):
        raise NotImplementedError

    def table_column_names(self, table_name):
        raise NotImplementedError

    def from_table(self, table_name, table):
        raise NotImplementedError


def fix_sql_table_name(table_name):
    """Remove characters not allowed in sqlite table name."""
    return ''.join(letter for letter in table_name
                   if (letter.isalnum() or letter == '_'))


@contextmanager
def read_rows_from_query(connector, connection_string, query):
    conn = connector.connect(connection_string)
    cursor = conn.cursor()
    try:
        print 'query', query
        cursor.execute(str(query))
    except:
        raise ValueError('Not a valid SQL query.')
    try:
        names = [entry[0] for entry in cursor.description]
        yield (names, cursor)
    except TypeError:
        raise ValueError('Not a valid SQL query')
    finally:
        conn.close()


@contextmanager
def read_rows_from_table(connector, connection_string, table_name,
                         columns=None):
    """Open a sqlite3 database, read columns from table and
    return as numpy record.
    """
    conn = connector.connect(connection_string)
    cursor = conn.cursor()
    column_string = None
    if columns is None:
        column_string = '*'
    else:
        column_string = ','.join(columns)
    assert(column_string is not None)
    try:
        cursor.execute("SELECT %s FROM %s" % (column_string, table_name))
        names = [entry[0] for entry in cursor.description]
        yield (names, cursor)
    finally:
        conn.close()


def read_table_names_sqlite3(fq_filename):
    # Connect and get table names for database
    conn = sqlite3.connect(fq_filename)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    # tables: list with tuples containing table names.
    # Extra table: sqlite_sequence
    # needs to be removed and u'strings' need to be converted to 'strings'
    table_names = [str(table[0]) for table in tables
                   if table[0] != 'sqlite_sequence']
    table_names.sort()
    conn.close()
    return table_names


def read_table_column_names(connector, connection_string, table_name):
    # Connect and get table names for database
    conn = connector.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM %s" % table_name)
    description = cursor.description
    unzip_descr = zip(*list(description))
    column_names = list(unzip_descr[0])
    column_names.sort()
    conn.close()
    return column_names


def write_table_sqlite3(fq_filename, table_name, table):
    """Write table to sqlite 3."""
    if table.number_of_columns() is 0:
        print('Cannot create empty table [{}].'.format(table_name))
        return

    if table_name == "":
        table_name = 'from_table'
    else:
        table_name = fix_sql_table_name(table_name)

    conn = sqlite3.connect(fq_filename)
    # Fick problem med utf-8 nar jag korde fran csv-filer annars.. Fult?
    conn.text_factory = str
    cursor = conn.cursor()
    names = table.column_names()
    input_types = [table.column_type(name) for name in names]
    # Fix illegal column names
    names = ['[{}]'.format(re.sub(r'[\\[\\]\\(\\)]', '', name)) for name in names]
    types = []

    for input_type in input_types:
        input_type_base = input_type.str[:2]
        if input_type_base == '<i':
            types.append('integer')
        elif input_type_base == '<f':
            types.append('real')
        elif input_type_base == '|b':
            types.append('bit')
        elif input_type_base == '<M':
            types.append('datetime')
        elif input_type_base in ['<U', '|S']:
            types.append('text')
        else:
            raise NotImplementedError(
                'Type {} not implemented.'.format(input_type.str))

    assert(len(names) == len(types))

    columns = ', '.join(['{} {}'.format(iname, itype)
                         for iname, itype in zip(names, types)])
    sqlite_data = table.to_rows()
    sqlite_names = ', '.join(names)

    create_str = ("CREATE TABLE IF NOT EXISTS " + table_name +
                  " (" + columns + ")")

    # Create table from create_str.
    cursor.execute(create_str)
    insert_str = ("INSERT INTO " + table_name + "(" + sqlite_names +
                  ") VALUES(")
    insert_qm = ['?' for name in names]
    insert_qm_string = ','.join(insert_qm)
    insert_str += insert_qm_string + ')'

    type_dict = {np.int: int,
                 np.int8: int,
                 np.int16: int,
                 np.int32: int,
                 np.int64: int,
                 np.int32: int,
                 np.uint: int,
                 np.uint8: int,
                 np.uint16: int,
                 np.uint32: int,
                 np.uint64: int,
                 np.uint32: int,
                 np.float: float,
                 np.float16: float,
                 np.float32: float,
                 np.float64: float,
                 np.string_: str,
                 np.unicode_: unicode,
                 np.bool: bool,
                 np.complex: str,
                 np.complex64: str}
    try:
        sqlite_data = [tuple(type_dict[type(sqlite_item)](sqlite_item)
                       for sqlite_item in sqlite_row)
                       for sqlite_row in sqlite_data]
    except Exception:
        import traceback
        traceback.print_exc()
        raise KeyError("Data type not valid.")
    # Create table from insert_str and data from table.
    cursor.executemany(insert_str, sqlite_data)
    conn.commit()
    conn.close()


def read_table_names_pyodbc(connection_string):
    # Connect and get table names for database
    conn = pyodbc.connect(connection_string)
    try:
        cursor = conn.cursor()
        table_names = [table.table_name for table in cursor.tables()
                       if table.table_type == 'TABLE']
        return sorted(table_names)
    finally:
        conn.close()


def build_where_query(tables, columns, join_columns, where_conditions):
    """Return a SQL query from input arguments using WHERE."""
    query = 'SELECT '
    query += ', '.join(columns)
    query += ' FROM '
    query += ', '.join(tables)
    if join_columns != [] or where_conditions != []:
        query += ' WHERE '
    joins = []
    for ind in xrange(1, len(join_columns), 2):
        joins.append(join_columns[ind - 1] + '=' + join_columns[ind])
    query += ' AND '.join(joins)
    if join_columns != [] and where_conditions != []:
        query += ' AND '
    if where_conditions != []:
        query += ' AND '.join(where_conditions)

    return query


class SQLite3Database(FileDatabase):
    def is_valid(self):
        try:
            with open(self.fq_filename, 'rb') as sqlite_file:
                try:
                    s = sqlite_file.read(1024)
                    s_h = binascii.hexlify(s)
                    if s_h[0:32] == '53514c69746520666f726d6174203300':
                        return True

                except sqlite3.Error:
                    return False
        except IOError:
            pass
        return False

    def to_rows_table(self, table_name, columns=None):
        return read_rows_from_table(sqlite3, self.fq_filename, table_name,
                                    columns)

    def to_rows_query(self, query):
        return read_rows_from_query(sqlite3, self.fq_filename, query)

    def table_names(self):
        return read_table_names_sqlite3(self.fq_filename)

    def table_column_names(self, table_name):
        return read_table_column_names(sqlite3, self.fq_filename, table_name)

    def from_table(self, table_name, table):
        return write_table_sqlite3(self.fq_filename, table_name, table)


class MDBDatabase(FileDatabase):
    @property
    def connection_string(self):
        return (
            'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s' %
            self.fq_filename)

    def is_valid(self):
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string)
        except:
            return False
        finally:
            if conn is not None:
                conn.close()
        return True

    def to_rows_table(self, table_name, columns=None):
        return read_rows_from_table(pyodbc, self.connection_string, table_name,
                                    columns)

    def to_rows_query(self, query):
        return table_from_odbc_query(self.connection_string, query)

    def table_names(self):
        return read_table_names_pyodbc(self.connection_string)

    def table_column_names(self, table_name):
        return read_table_column_names(pyodbc, self.connection_string,
                                       table_name)

    def from_table(self, table_name, table):
        return table_to_odbc(table, self.connection_string, table_name, False,
                             odbc=None)


def table_to_odbc(table, fq_filename, table_name, drop_table=False,
                  use_nvarchar_size=False, odbc=None):
    """Write table to ODBC."""
    if odbc is None:
        odbc = pyodbc

    if table is None:
        raise IOError(
            'A table without columns is not possible to export to a database.')

    if table.number_of_columns() is 0:
        print('Cannot create empty table [{}].'.format(table_name))
        return

    conn = odbc.connect(fq_filename)
    if table_name == "":
        table_name = 'from_table'
    else:
        table_name = fix_sql_table_name(table_name)
    cursor = conn.cursor()
    names = table.column_names()
    input_types = [table.column_type(name) for name in names]

    # Fix illegal column names
    names = ['[{}]'.format(re.sub('[-\\[\\]\\(\\)]', '', name)) for name in names]
    types = []

    for input_type in input_types:
        input_type_base = input_type.str[:2]

        if input_type_base == '<i':
            types.append('int')
        elif input_type_base == '<f':
            types.append('float')
        elif input_type_base == '|b':
            types.append('bit')
        elif input_type_base == '<M':
            types.append('datetime')
        elif input_type_base in ['<U', '|S']:
            if use_nvarchar_size:
                types.append('nvarchar({})'.format(input_type.itemsize))
            else:
                types.append('nvarchar(MAX)')
        else:
            raise NotImplementedError(
                'Type {} not implemented.'.format(input_type.str))

    assert(len(names) == len(types))

    columns = ', '.join(['{} {}'.format(iname, itype)
                         for iname, itype in zip(names, types)])

    sqlite_data = table.to_rows()
    sqlite_names = ', '.join(names)

    tables_in_database_query = 'SELECT * FROM sys.Tables'
    cursor.execute(tables_in_database_query)
    tables_in_database = [tdata[0] for tdata in cursor.fetchall()]

    if drop_table and table_name in tables_in_database:
        cursor.execute('DROP TABLE {}'.format(table_name))
    # Create if table is missing otherwise append data.
    if drop_table or table_name not in tables_in_database:
        create_table_query = 'CREATE TABLE {} ({})'.format(table_name, columns)
        cursor.execute(create_table_query)
    insert_data_query = 'INSERT INTO {} ({}) VALUES('.format(
        table_name, sqlite_names)

    insert_qm = ['?' for name in names]
    insert_qm_string = ','.join(insert_qm)
    insert_data_query += insert_qm_string + ')'
    nan_to_none = lambda x: None if np.isnan(x) else float(x)

    type_dict = {float: nan_to_none,
                 datetime.datetime: str}

    try:
        sqlite_data = [tuple(type_dict.get(type(sqlite_item),
                                           type(sqlite_item))(sqlite_item)
                       for sqlite_item in sqlite_row)
                       for sqlite_row in sqlite_data]
    except KeyError:
        raise KeyError("Data type not valid.")
    # Enable autocommit or memory problems can occur.
    conn.autocommit = True
    if sqlite_data != []:
        try:
            cursor.executemany(insert_data_query, sqlite_data)
        except:
            print('input, [(type, name)]:', zip(names, input_types))
            print('output, [(type, name)]:', zip(names, types))
            print('drop_table', str(drop_table))
            raise
    conn.commit()
    conn.close()


def convert_types(rows):
    """
    Convert cells in rows accorting to the conversions dictionary.
    Values with types present in conversions will be converted.
    Values with types not present in conversions will be preserved.

    Return a new row generator with values converted in accordance with
    conversions.
    """
    conversions = {Decimal: float}

    def convert(cell):
        cell_type = type(cell)
        if cell_type in conversions:
            return conversions[cell_type](cell)
        else:
            return cell

    for row in rows:
        yield [convert(cell) for cell in row]


@contextmanager
def table_from_odbc_query(fq_filename, query, odbc=None):
    if odbc is None:
        odbc = pyodbc
    conn = odbc.connect(fq_filename)
    cursor = conn.cursor()
    try:
        cursor.execute(unicode(query))
    except:
        raise ValueError('Not a valid SQLite query.')
    try:
        # Get cursor description information on the form:
        # [(name, type_code, None, internal_size, precision, 0, null_ok)]
        names = [entry[0] for entry in cursor.description]
        # Check types of elements in the columns
        yield (names, convert_types(cursor))
    except TypeError:
        raise ValueError('Not a valid SQLite query')
    finally:
        conn.close()
