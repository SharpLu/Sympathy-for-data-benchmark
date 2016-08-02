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

"""Sympathy table."""
from collections import OrderedDict
import numpy as np
import dask.array as da
from dask.dot import  dot_graph
import datetime
from . import sybase
from . import exception as exc


def _column_factory(datasource, column, nrows):
    assert(datasource != sybase.NULL_SOURCE)
    return Column(source=OnDiskColumnSource(datasource, column, nrows))


class Source(object):

    def get(self):
        raise NotImplementedError

    def link(self, name, datasource):
        raise NotImplementedError

    def write(self, name, datasource):
        raise NotImplementedError

    @property
    def dirty(self):
        raise NotImplementedError


class InMemoryColumnSource(Source):

    def __init__(self, obj, attrs=None):
        self._obj = obj
        self._attrs = attrs or {}

    def get(self, index=None):
        if index is None:
            return self._obj
        else:
            return self._obj[index]

    def link(self, name, attrs, datasource):
        self.write(name, attrs, datasource)

    def write(self, name, attrs, datasource):
        datasource.write_column(name, self.get())
        datasource.write_column_attributes(name, attrs)

    @property
    def dirty(self):
        return True

    @property
    def dtype(self):
        return self._obj.dtype

    @property
    def attrs(self):
        return {}

    def __len__(self):
        return len(self._obj)


class OnDiskColumnSource(Source):

    def __init__(self, datasource, key, nrows=None):
        self._datasource = datasource
        self._key = key
        self._nrows = nrows

    def __hash__(self):
        return hash(self._datasource.file.filename,
                    self._datasource.group.name,
                    self._key)

    def get(self, index=None):
        return self._datasource.read_column(self._key, index)

    def link(self, name, attrs, datasource):
        if datasource.transferable(self._datasource):
            if not datasource.shares_origin(self._datasource):
                datasource.transfer(name, self._datasource, self._key)
            # else:
            #     Asked to write something clean to itself, nothing to do.

        else:
            self.write(name, attrs, datasource)

    def write(self, name, attrs, datasource):
        datasource.write_column(name, self.get())
        datasource.write_column_attributes(name, attrs)

    @property
    def dirty(self):
        return False

    @property
    def dtype(self):
        return self._datasource.column_type(self._key)

    @property
    def attrs(self):
        return dict(self._datasource.read_column_attributes(self._key)
                    or {})

    def __len__(self):
        if self._nrows is None:
            self._nrows = self._datasource.number_of_rows()
        return self._nrows


class Column(object):

    def __init__(self, data=None, source=None, attrs=None):
        assert(data is not None or source is not None)

        if isinstance(data, np.ndarray) or isinstance(data, da.Array):
            #dot_graph(da.Array)
            source = InMemoryColumnSource(data)

        self._source = source
        self._dirty = source.dirty
        self._attrs = attrs

    def get(self, index=None):
        return self._source.get(index)

    def _link(self, name, datasource):
        self._source.link(name, self.attrs, datasource)

    def _write(self, name, datasource):
        self._source.write(name, self.attrs, datasource)

    @property
    def dirty(self):
        return self._source.dirty

    @property
    def dtype(self):
        return self._source.dtype

    @property
    def attrs(self):
        if self._attrs is None:
            self._attrs = self._source.attrs
        return dict(self._attrs)

    @attrs.setter
    def attrs(self, value):
        if value is not None:
            for k, v in value.items():
                _key_guard(k, 'Attribute name')
                _str_guard(v, 'Attribute value')

        self._attrs = value
        self._dirty = True

    def __len__(self):
        return len(self._source)

    def __copy__(self):
        obj = Column(source=self._source)
        obj._dirty = self._dirty
        obj._attrs = self._attrs
        return obj

    def __deepcopy__(self, memo=None):
        return self.__copy__()


def _str_guard(string, name='String'):
    if isinstance(string, np.ndarray):
        if string.dtype.kind == 'U':
            return
    try:
        unicode(string)
    except UnicodeEncodeError:
        raise ValueError(
            u'{}: {} contains bad characters, it should be in '
            'unicode or contain only ASCII'.format(name, repr(string)))


def _key_guard(key, name='String'):
    if np.array(key).dtype.kind in ['S', 'U']:
        _str_guard(key, name)
    else:
        raise ValueError(u'{}: {} ({}) has bad type, it should be in '
                         'unicode or contain only ASCII'.format(
                             name, repr(key), type(key)))


class syattributes(object):
    """A interface to attributes stored in sytables."""
    def __init__(self, column):
        self._column = column

    def delete(self):
        """Delete all attributes."""
        self._column.attrs = None

    def get(self):
        """Returns all attributes."""
        return self._column.attrs

    def set(self, properties):
        """Set the attributes to the values in the properties dictionary."""
        self._column.attrs = properties

    def delete_attribute(self, name):
        """Delete named attribute."""
        attrs = self._column.attrs
        del attrs[name]
        self._column.attrs = attrs

    def get_attribute(self, name):
        """Returns named attribute."""
        return self._column.attrs[name]

    def set_attribute(self, name, value):
        """Set named attribute to the given value."""
        attrs = self._column.attrs
        attrs[name] = value
        self._column.attrs = attrs

    def __getitem__(self, name):
        return self.get_attribute(name)

    def __setitem__(self, name, value):
        self.set_attribute(name, value)

    def __delitem__(self, name):
        self.delete_attribute(name)


class sytable(sybase.sygroup):
    """A type representing a table."""
    def __init__(self, container_type, datasource=sybase.NULL_SOURCE):
        """
        Init. container_type parameter is not used, needed to
        conform factory interface.
        """
        super(sytable, self).__init__(container_type,
                                      datasource or sybase.NULL_SOURCE)
        columns = datasource.columns()
        self._name = datasource.read_name()
        self._attributes = datasource.read_table_attributes() or {}
        self._number_of_rows = datasource.number_of_rows()
        self._columns = OrderedDict(
            (column, _column_factory(datasource, column, self._number_of_rows))
            for column in columns)

        self._column_attributes = dict.fromkeys(columns)
        self._dirty = False

    def columns(self):
        """Return a list with the names of the table columns."""
        return self._columns.keys()

    def number_of_rows(self):
        """Return the number table rows."""
        if self.number_of_columns():
            return self._number_of_rows
        else:
            return 0

    def number_of_columns(self):
        """Return the number of table columns."""
        return len(self._columns)

    def column_type(self, name):
        return self._get_column_column(name).dtype

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._dirty = True
        if name is not None:
            _key_guard(name, 'Table name')
        self._name = name

    def get_table_attributes(self):
        return self._attributes

    def set_table_attributes(self, attributes):
        """
        Set scalar attributes for the table,
        attributes argument is a dictionary.
        """
        self._dirty = True
        if attributes is not None:
            for k, v in attributes.iteritems():
                _key_guard(k, 'Attribute name')
                _str_guard(v, 'Attribute value')
        self._attributes = attributes

    def get(self, column_name):
        """Return numpy rec array."""
        if column_name is None:
            raise ValueError(
                'column_name=None is not valid for column(), use value()')
        column = self.get_column(column_name)
        return np.rec.array(column, {'names': [column_name],
                                     'formats': [str(column.dtype)]})

    def _get_column_index(self, name, index):
        return self._get_column_column(name).get(index)

    def _get_column(self, name):
        return self._get_column_column(name).get()

    def _get_column_column(self, name):
        try:
            column = self._columns[name]
        except KeyError:
            _key_guard(name, 'Column name')
            raise KeyError(u'Column: "{}" not found.'.format(name))
        return column

    def get_column(self, column_name, index=None):
        if index is None:
            return self._get_column(column_name)
        return self._get_column_index(column_name, index)

    def value(self):
        """Return numpy rec array or None."""
        columns = self._columns.keys()

        if not columns:
            return None
        datacolumns = self._columns.values()
        # Construct the table from numpy array.
        return np.rec.array(
            [datacolumn.get() for datacolumn in datacolumns],
            {'names': columns,
             'formats': [str(column.dtype)
                         for column in datacolumns]})

    def visit(self, group_visitor):
        """Accept group visitor."""
        group_visitor.visit_table(self)

    def has_column(self, column_name):
        """Returns True if a column name exists in table, False otherwise."""
        return column_name in self._columns

    def __contains__(self, column_name):
        """Not implemented. Use :meth:`has_column` instead."""
        raise NotImplementedError("Use method has_column instead.")

    def set(self, table):
        """Write numpy rec array."""
        if table is None:
            return
        for name in table.dtype.names:
            self._set_column(name, table[name])

    def _set_column_length_guard(self, column_name, length):
        if self.number_of_columns() == 0:
            return
        elif self.number_of_columns() == 1 and self.has_column(column_name):
            return
        elif length != self._number_of_rows:
            raise ValueError('Can not add column of length {}'
                             ' to table of length {}'.format(
                                 length, self._number_of_rows))

    def set_column(self, column_name, column):
        """Write numpy array column to a column named column_name."""
        _key_guard(column_name, 'Column name')
        self._set_column(column_name, column)

    def _set_column(self, column_name, column):
        """Write numpy array column to a column named column_name.
        Does not perform any dimension checks on column."""
        self._dirty = True

        if column.ndim != 1:
            raise ValueError("Can only add one-dimensional columns.")
        if column.dtype.hasobject:
            # Attempting to create a specific non-object based numpy type.
            try:
                first = column[0]
            except IndexError:
                column = np.array([])
            else:
                try:
                    # Determining type from the first element.
                    if isinstance(first, datetime.datetime):
                        # Datetime.
                        column = np.array(column, dtype='datetime64[us]')
                    elif isinstance(first, datetime.timedelta):
                        # Timedelta.
                        try:
                            column = np.array(column, dtype='timedelta64[us]')
                        except TypeError:
                            # This exception can occur in numpy 1.9.1 on 32-bit
                            # Windows if there is a mix of zero-value and
                            # non-zero-value timedeltas. Work around by not
                            # converting the zero-value timedeltas to numpy,
                            # but using it as the default value instead.
                            temp_column = np.zeros_like(
                                column, dtype='timedelta64[us]')
                            for i, v in enumerate(column):
                                if v != datetime.timedelta(0):
                                    temp_column[i] = v
                            column = temp_column
                    else:
                        # No conversion possible.
                        raise ValueError()
                except (ValueError, TypeError):
                    raise Exception(
                        u'Unsupported object type in column {}'.format(
                            column_name))

        column = Column(column)
        self._set_column_column(column_name, column)
        self._number_of_columns = len(column)

    def _set_column_column(self, name, column):
        len_column = len(column)
        self._set_column_length_guard(name, len_column)
        self._set_column_column_nocheck(name, column, len_column)

    def _set_column_column_nocheck(self, name, column, nrows):
        self._dirty = True
        self._columns[name] = column.__copy__()
        self._number_of_rows = nrows

    def update(self, other):
        """
        Write all columns from other table. Creates links if possible.
        """
        # Check if any columns will remain with their original length. If so
        # also check if the lengths of the tables are the same.
        self._dirty = True
        nrows = other.number_of_rows()

        if (other._columns and
            set(self._columns) - set(other._columns) and
                other.number_of_rows() != self.number_of_rows()):

            raise ValueError('Can not add columns of length {}'
                             ' to table of length {}'.format(
                                 other.number_of_rows(),
                                 self.number_of_rows()))

        for name, column in other._columns.items():
            self._set_column_column_nocheck(name, column, nrows)

        self.set_table_attributes(other.get_table_attributes())
        self.set_name(other.get_name())

    def source(self, other):
        self._name = other._name
        self._attributes = {}
        self._columns = OrderedDict()
        self._number_of_rows = other.number_of_rows()
        self.update(other.__deepcopy__())
        self._dirty = other._dirty
        self._datasource = other._datasource

    def __copy__(self):
        obj = super(sytable, self).__copy__()
        obj._name = self._name
        obj._attributes = self._attributes
        obj._number_of_rows = self._number_of_rows
        obj._columns = dict(self._columns)
        return obj

    def __deepcopy__(self, memo=None):
        obj = self.__copy__()
        obj._columns = {k: v.__deepcopy__()
                        for k, v in self._columns.iteritems()}
        return obj

    def update_column(self, cache_name, other, other_name):
        """
        Write column with other_name from other table as cache_name in the
        current table. Create links if possible.
        """
        _key_guard(cache_name, 'Column name')
        if cache_name != other_name:
            _key_guard(other_name, 'Column name target')
        self._update_column(cache_name, other, other_name)

    def _update_column(self, cache_name, other, other_name):
        """
        Write column with other_name from other table as cache_name in the
        current table. Create links if possible. Doesn't check column length
        consistency.
        """
        self._set_column_column(
            cache_name, other._get_column_column(other_name))

    def is_empty(self):
        """Returns ``True`` if the table is empty."""
        return (self.number_of_rows() == 0 and
                self.number_of_columns() == 0)

    def __getitem__(self, index):
        def identity_slice(index, size):
            if not isinstance(index, slice):
                return False
            explicit_index = slice(index.start or 0,
                                   size if index.stop is None else index.stop,
                                   1 if index.step is None else index.step)
            return explicit_index == slice(0, size, 1)

        result = sytable(self.container_type)

        if isinstance(index, tuple):
            if len(index) is not 2:
                # The table is only two dimensional so it would not make sense
                # to go beyond two indices.
                raise TypeError('Invalid index.')
            row_index, col_index = index

            if isinstance(col_index, int):
                if col_index >= len(self.columns()):
                    raise IndexError(
                        'Column index {} is out of bound. '
                        'There are only {} columns in this table.'
                        ''.format(col_index, len(self.columns())))
                col_index = slice(col_index, col_index + 1)
            elif isinstance(col_index, slice):
                pass
            else:
                # Allowing 1D iterable indices.
                assert(len(col_index))
                col_index = np.array(col_index)

                assert(col_index.ndim is 1)
                # Convert to list after asserting dimension.
                col_index = col_index.tolist()

            columns = np.array(self.columns())[col_index].tolist()

        else:
            row_index = index
            columns = self.columns()

        if isinstance(row_index, int):
            start = row_index
            if row_index < 0:
                start += self.number_of_rows()
            if row_index >= self.number_of_rows():
                raise IndexError(
                    'Row index {} is out of bound. '
                    'There are only {} rows in this table.'
                    ''.format(row_index, self.number_of_rows()))
            row_index = slice(start, start + 1)

        elif isinstance(row_index, slice):
            # raw_index = row_index
            number_of_rows = self.number_of_rows()
            start = row_index.start
            stop = row_index.stop
            if start is not None and start < 0:
                start += number_of_rows
            if stop is not None and stop < 0:
                stop += number_of_rows
            row_index = slice(start, stop, row_index.step)
        else:
            # Allowing 1D iterable indices.
            row_index = np.array(row_index)

            assert(row_index.ndim == 1)
            # Convert to list after asserting dimension.
            row_index = row_index.tolist()

        rows = self.number_of_rows()
        if identity_slice(row_index, rows):
            # The whole table is requested, copying can be avoided in
            # favor of an update operation.
            for column_name in columns:
                result.update_column(column_name, self, column_name)
        else:
            # Copy data creating reduced table.
            for column_name in columns:
                result.set_column(
                    column_name,
                    self._get_column_index(column_name, row_index))
                result.get_column_attributes(column_name).set(
                    self.get_column_attributes(column_name).get())
        return result

    def __setitem__(self, index, other_table):
        self._dirty = True

        def identity_slice(index, size):
            return (
                [index.start or 0,
                 1 if index.step is None else index.step] == [0, 1] and
                (size if index.stop is None else index.stop) >= size)

        def positive_slice(index, length):
            if not isinstance(index, slice):
                return True
            start = index.start or 0
            stop = length if index.stop is None else index.stop
            step = 1 if index.step is None else index.step
            return (start >= 0 and
                    step >= 1 and
                    stop >= start)

        def slice_length(index, length):
            if isinstance(index, np.ndarray):
                return len(index)
            start = index.start or 0
            stop = length if index.stop is None else index.stop
            step = 1 if index.step is None else index.step
            return abs((stop - start) / step)

        def replace_data(col_slice, row_slice):
            columns = self.columns()

            if (slice_length(col_slice, self.number_of_columns()) !=
                    other_table.number_of_columns()):
                raise ValueError('Table column length mismatch.')
            if (slice_length(row_slice, self.number_of_rows()) !=
                    other_table.number_of_rows()):
                raise ValueError('Table row length mismatch.')

            for other_column, column in zip(other_table.columns(),
                                            np.array(columns)[col_slice]):
                attrs = self._get_column_column(column).attrs
                current = np.array(self.get_column(column))
                current[row_slice] = other_table.get_column(other_column)
                self._columns[column] = Column(
                    source=InMemoryColumnSource(current, attrs))

        new_columns = other_table.columns()
        curr_columns = self.columns()

        full_col = False
        full_row = False

        cols = self.number_of_columns()
        rows = self.number_of_rows()

        if isinstance(index, tuple):
            if len(index) is not 2:
                # The table is only two dimensional so it would not make sense
                # to go beyond two indices.
                raise TypeError('Invalid index.')
            row_index, col_index = index

            if isinstance(col_index, int):
                slice_col_index = slice(col_index, col_index + 1)
            elif isinstance(col_index, slice):
                full_col = identity_slice(col_index, cols)
                slice_col_index = col_index
            else:
                # Allowing 1D iterable indices.
                slice_col_index = (
                    np.array(col_index)
                    if col_index is not None else np.array([], dtype=int))
                if slice_col_index.ndim != 1:
                    raise TypeError('Index iterable must be 1D.')
        else:
            row_index = index
            full_col = True
            col_index = slice(0, None, None)
            slice_col_index = col_index

        if isinstance(row_index, int):
            row_index = slice(row_index, row_index + 1)
            slice_row_index = row_index
        elif isinstance(row_index, slice):
            slice_row_index = row_index
            full_row = identity_slice(slice_row_index, rows)
        else:
            # Allowing 1D iterable indices.
            slice_row_index = (
                np.array(row_index)
                if col_index is not None else np.array([], dtype=int))
            if slice_row_index.ndim != 1:
                raise TypeError('Invalid index.')

        if not positive_slice(slice_col_index, cols):
            raise ValueError('Negative slice notation unsupported.')

        if not positive_slice(slice_row_index, rows):
            raise ValueError('Negative slice notation unsupported.')

        if full_row and full_col:
            # Replace the table entirely with other_table.
            for column in curr_columns:
                del self[column]
            self.update(other_table)

        elif full_row:
            if isinstance(col_index, slice):
                col_step = (1 if slice_col_index.step is None
                            else slice_col_index.step)
            else:
                col_step = None

            if col_step is 1:
                # Replace the columns selected entirely by other_table.
                remove_columns = curr_columns[slice_col_index]
                kept_columns = set(curr_columns).difference(remove_columns)

                if other_table.number_of_rows() != rows:
                    raise ValueError('Table row length mismatch.')

                if kept_columns.intersection(new_columns):
                    raise ValueError('Overlapping column names.')

                for column in remove_columns:
                    del self[column]
                col_start = slice_col_index.start or 0
                col_stop = ((col_start if slice_col_index.stop is None
                             else slice_col_index.stop) +
                            other_table.number_of_columns())
                for column in new_columns:
                    self.update_column(column, other_table, column)
                columns = [(k, v.get()) for k, v in self._columns.items()]
                self._columns = OrderedDict(
                    (k, Column(v)) for k, v in
                    (columns[:col_start] +
                     columns[len(kept_columns):] +
                     columns[col_stop:len(kept_columns)]))

            else:
                replace_data(slice_col_index, slice_row_index)
        elif full_col:
            if isinstance(row_index, slice):
                row_step = (1 if slice_row_index.step is None
                            else slice_row_index.step)
            else:
                row_step = None

            if row_step is 1:
                # Replace the rows selected entirely by other_table.
                if (other_table.number_of_columns() != cols):
                    raise ValueError('Table column length mismatch.')

                row_start = slice_row_index.start or 0
                row_stop = ((row_start if slice_row_index.stop is None
                             else slice_row_index.stop) +
                            other_table.number_of_rows())

                for column in curr_columns:
                    attrs = self._get_column_column(column).attrs
                    current = self.get_column(column)
                    self._columns[column] = Column(source=InMemoryColumnSource(
                        np.hstack([current[:row_start],
                                   other_table.get_column(column),
                                   current[row_stop:]]), attrs))

            else:
                replace_data(slice_col_index, slice_row_index)
        else:
            # Sub-selection used.
            # Replace the selected data by other_table, keeping dimensions etc.
            replace_data(slice_col_index, slice_row_index)

    def writeback(self):
        super(sytable, self).writeback()

    def _writeback(self, datasource, link=None):
        # Transfer relies on direct compatiblity, for example, in the hdf5
        # datasource case both sources need to be hdf5 and the source needs to
        # be read only.
        origin = self._datasource
        target = datasource

        exc.assert_exc(target.can_write, exc=exc.WritebackReadOnlyError)

        if link:
            return self._link(target, link)

        target.write_started(self.number_of_rows(), self.number_of_columns())
        shares_origin = target.shares_origin(origin)

        target.write_table_attributes(self._attributes)
        target.write_name(self._name)

        dirty_cols = any(v.dirty for v in self._columns.values())

        if shares_origin and not (self._dirty or dirty_cols):
            # There is no point in writeback of unmodified data to the
            # original datasource.
            return

        # Linking transfer must be considered for each column.
        for key, col in self._columns.items():
            if col.dirty:
                col._write(key, target)
            else:
                col._link(key, target)

        target.write_finished()

    def get_column_attributes(self, column):
        return syattributes(self._get_column_column(column))

    def __delitem__(self, column):
        del self._columns[column]
        self._dirty = True

    def __repr__(self):
        return "sytable()"
