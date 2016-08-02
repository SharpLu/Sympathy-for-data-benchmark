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
"""Table Data source module."""
from collections import OrderedDict
import h5py
import numpy as np
import dsgroup
import re
from sympathy.platform.state import hdf5_state

ORDER = '__sy_order__'
NAME = '__sy_name__'

table_attributes = [ORDER, NAME]

ENCODING = '__sy_encoding__'
ENCODING_TYPE = '__sy_encoding_type__'
NUMPY_TYPE = '__sy_numpy_type__'

RES_RE = re.compile('^__sy_.*__$')

column_attributes = [ENCODING, ENCODING_TYPE, NUMPY_TYPE]

UTF8 = 'utf-8'

encoded_types = {'datetime64[ns]': 'f8',
                 'datetime64[us]': 'f8',
                 'datetime64[D]': 'f8',
                 'timedelta64[us]': 'f8'}
encoded_types_matches = set(encoded_types.keys())


compress_threshold = 2048


int_compress = dict(compression='lzf', shuffle=True)
ext_compress = dict(compression='gzip', shuffle=True, compression_opts=9)


def __monkeypatch_externallink_init():
    """
    TODO! Track changes in h5py.
    Patch enables unicode datasets in h5py.ExternalLink.
    This makes it possible to use .get(name, getlink=True) without causing
    an exception.

    However, if the behavior of h5py.External link __init__ changes, then
    so must this patch.
    """
    def patch(self, filename, path):
        self._filename = filename
        self._path = path
    try:
        h5py.ExternalLink.__init__ = patch
    except AttributeError:
        pass

__monkeypatch_externallink_init()


def encode(array, encoding=UTF8):
    """
    Encode numpy unicode typed array (array.dtype.kind == 'U') as a numpy
    string array.
    """
    return np.char.encode(array, encoding)


def decode(array, encoding=UTF8):
    """
    Decode string array dataset encoded in utf-8 as a numpy unicode typed array
    (array.dtype.kind == 'U').
    """
    return np.char.decode(array, encoding)


def decode_attribute(attribute):
    """
    Decode attribute encoded in utf-8 as a list of unicode strings or as a
    single unicode string.
    """
    try:
        # Eliminate arrays.
        data = attribute.tolist()
    except:
        data = attribute
    if isinstance(data, str):
        data = data.decode(UTF8)
    elif isinstance(data, list):
        if np.array(data).dtype.kind == 'U':
            data = [x.encode(UTF8) for x in data]
    return data


def encode_attribute(attribute, encoding=UTF8):
    """
    Encode string or possibly numpy unicode typed array
    (array.dtype.kind == 'U') as string array.
    """
    try:
        # Eliminate arrays.
        data = attribute.tolist()
    except:
        data = attribute
    if isinstance(data, unicode):
        data = data.encode(encoding)
    elif isinstance(data, list):
        if np.array(data).dtype.kind == 'U':
            data = [x.encode(encoding) for x in data]
    return data


class Hdf5TableBase(dsgroup.Hdf5Group):
    """Abstraction of an HDF5-table."""
    def __init__(self, group, can_write, can_link):
        self.group = group
        self.can_write = can_write
        self.can_link = can_link
        self.compress = int_compress if can_link else ext_compress

        keys = sorted(key for key in self.group.keys()
                      if not re.match(RES_RE, key))

        order = self.group.get(ORDER, None)
        if order is None:
            order = self.group.attrs.get(ORDER, None)
            if order is None:
                order = range(len(self.group))

        stored_columns = np.array(
            keys)[order[...]].tolist() if len(order) else []

        user_columns = [dsgroup.restore_slash(key)
                        for key in stored_columns]
        self._columns = OrderedDict(zip(stored_columns, user_columns))

        self._length = None

    def read_column_attributes(self, column_name):
        dataset = hdf5_state().get(
            self.group, dsgroup.replace_slash(column_name))
        attrs = {decode_attribute(key): decode_attribute(value.tolist())
                 for key, value in dataset.attrs.items()
                 if key not in column_attributes}
        return attrs

    def write_column_attributes(self, column_name, properties):
        if properties:
            attrs = self.group[dsgroup.replace_slash(column_name)].attrs
            for key, value in properties.iteritems():
                attrs.create(encode_attribute(key),
                             encode_attribute(value))

    def read_column(self, column_name, index=None):
        """Return numpy array with data from the given column name."""
        def get_bool_index(length, int_index):
            """Return bool index vector from int index vector."""
            result = np.zeros(length, dtype=bool)
            result[int_index] = True
            return result

        def indexed(column, index):
            if isinstance(index, list):
                # Slicing with bool index is faster than list of integers.
                # See https://github.com/h5py/h5py/issues/368
                bool_index = get_bool_index(len(column), index)

                # If the list of integers was non-increasing, that information
                # gets lost when converting to a boolean index, so we need to
                # work around that.
                if not (np.diff(index) > 0).all():
                    _, sort_index = np.unique(index, return_inverse=True)
                    return column[bool_index][sort_index]
                else:
                    return column[bool_index]
            elif isinstance(index, slice):
                # H5py can't handle negative strides so we read it increasing
                # order and reverse it afterwards.
                if index.step is not None and index.step < 0:
                    increasing_index = slice(
                        index.start, index.stop, -index.step)
                    return column[increasing_index][::-1]
            return column[index]

        # Named column selection used.
        column = hdf5_state().get(
            self.group, dsgroup.replace_slash(column_name))
        if ENCODING in column.attrs:
            if column.shape == (0,):
                # Avoid zero size selection problem in h5py.
                result = np.array([], dtype=column.dtype)
            else:
                result = decode(indexed(column, index)
                                if index is not None else column,
                                column.attrs[ENCODING])
        else:
            if column.shape == (0,):
                # Avoid zero size selection problem in h5py.
                result = np.array([], dtype=column.dtype)
            else:
                result = (indexed(column, index)
                          if index is not None else column.value)
            if ENCODING_TYPE in column.attrs:
                result = result.astype(column.attrs[ENCODING_TYPE])
        return result

    def write_column(self, column_name, column):
        """
        Stores table in the hdf5 file, at path,
        with data from the given table
        """
        if column.ndim == 1:
            # 1D dataset.
            length = len(column)
        elif column.ndim == 0:
            # Scalar dataset.
            length = -1
        else:
            # Multi-dimensional columns are not allowed.
            assert(False)

        if self._length is not None:
            # Check that the table length is consistent.
            assert self._length == length, (
                'len({}) = {} != {}'.format(column_name, length, self._length))
        self._length = length

        # Write column data to the group.
        name = dsgroup.replace_slash(column_name)
        if column.dtype.kind == 'U':
            if column.nbytes > compress_threshold:
                self.group.create_dataset(
                    name, data=encode(column), **self.compress)
            else:
                self.group[name] = encode(column)
            self.group[name].attrs.create(ENCODING, UTF8)
            self.group[name].attrs.create(ENCODING_TYPE,
                                          column.dtype.str)
        else:
            dtype_name = column.dtype.name
            dtype_str = None

            if dtype_name in encoded_types_matches:
                dtype_str = column.dtype.str
                column = column.astype(encoded_types[dtype_name])

            if column.nbytes > compress_threshold:
                self.group.create_dataset(
                    name, data=column, **self.compress)
            else:
                self.group[name] = column

            if dtype_str is not None:
                self.group[name].attrs.create(ENCODING_TYPE, dtype_str)

        self._columns[name] = column_name

    def transferable(self, other):
        return (isinstance(other, Hdf5Table) and
                self.can_link and other.can_link)

    def transfer(self, name, other, other_name):
        user_name = name
        store_name = dsgroup.replace_slash(name)
        other_name = dsgroup.replace_slash(other_name)
        dataset = hdf5_state().get(other.group, other_name)

        try:
            length = len(dataset)
        except TypeError:
            # Assuming scalar dataset.
            length = -1

        if self._length is not None:
            # Check that the table length is consistent.
            assert(self._length == length)
        self._length = length
        self.group[store_name] = h5py.ExternalLink(
            dataset.file.filename.encode(UTF8), dataset.name.encode(UTF8))
        self._columns[store_name] = user_name

    def write_started(self, number_of_rows, number_of_columns):
        pass

    def write_finished(self):
        """Finish writing table."""
        lookup = {key: i for i, key in
                  enumerate(sorted(key for key in self.group.keys()
                                   if not re.match(RES_RE, key)))}
        order = [lookup[key] for key in self._columns.keys()]
        if order:
            if ORDER in self.group:
                del self.group[ORDER]

            self.group.create_dataset(ORDER, data=order, dtype='i')
            try:
                # TODO: Remove this after version 1.3 is released.
                self.group.attrs.create(ORDER, order, dtype='i')
            except RuntimeError:
                # Ignoring ordering due to size restrictions.
                pass

    def columns(self):
        """Return a list contaning the available column names."""
        return self._columns.values()

    def column_type(self, name):
        dataset = hdf5_state().get(self.group, dsgroup.replace_slash(name))
        if ENCODING_TYPE in dataset.attrs:
            return np.dtype(dataset.attrs[ENCODING_TYPE])
        else:
            return dataset.dtype

    def number_of_rows(self):
        try:
            name = iter(self._columns).next()
            column = hdf5_state().get(self.group, name)
            # Check for scalar value which has no length.
            # .size is not available for older h5py.
            if column.shape == tuple():
                return 1
            else:
                return len(column)
        except StopIteration:
            return 0

    def number_of_columns(self):
        return len(self.group)

    def write_name(self, name):
        if name is not None:
            self.group.attrs.create(NAME, encode_attribute(name))

    def read_name(self):
        name = decode_attribute(self.group.attrs.get(NAME, None))
        return name

    def read_table_attributes(self):
        return {decode_attribute(key): decode_attribute(value.tolist())
                for key, value in self.group.attrs.items()
                if key not in table_attributes}

    def write_table_attributes(self, properties):
        if properties:
            attrs = self.group.attrs
            for key, value in properties.iteritems():
                attrs.create(encode_attribute(key),
                             encode_attribute(value))


class Hdf5Table(dsgroup.Hdf5Group):
    """Abstraction of an HDF5-table."""
    def __init__(self, factory, group=None, datapointer=None, can_write=False,
                 can_link=False):
        super(Hdf5Table, self).__init__(factory, group, datapointer, can_write,
                                        can_link)
        self._table = Hdf5TableBase(self.group, self.can_write, self.can_link)

    def read_column_attributes(self, column_name):
        return self._table.read_column_attributes(column_name)

    def write_column_attributes(self, column_name, properties):
        return self._table.write_column_attributes(column_name, properties)

    def read_column(self, column_name, index=None):
        return self._table.read_column(column_name, index)

    def write_column(self, column_name, column):
        return self._table.write_column(column_name, column)

    def transferable(self, other):
        return self._table.transferable(other)

    def transfer(self, name, other, other_name):
        return self._table.transfer(name, other, other_name)

    def write_started(self, number_of_rows, number_of_columns):
        return self._table.write_started(number_of_rows, number_of_columns)

    def write_finished(self):
        return self._table.write_finished()

    def columns(self):
        return self._table.columns()

    def column_type(self, name):
        return self._table.column_type(name)

    def number_of_rows(self):
        return self._table.number_of_rows()

    def number_of_columns(self):
        return self._table.number_of_columns()

    def write_name(self, name):
        return self._table.write_name(name)

    def read_name(self):
        return self._table.read_name()

    def read_table_attributes(self):
        return self._table.read_table_attributes()

    def write_table_attributes(self, properties):
        return self._table.write_table_attributes(properties)
