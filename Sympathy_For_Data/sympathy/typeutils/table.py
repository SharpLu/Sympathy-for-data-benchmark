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
API for working with the Table type.

Import this module like this::

    from sympathy.api import table

Class :class:`table.File`
-------------------------
.. autoclass:: File
   :members:
   :special-members:

Class :class:`table.FileList`
-----------------------------
.. autoclass:: FileList
   :members: __getitem__, append

"""
import collections
from itertools import islice, izip

import re
import numpy as np

from .. types import sybase
from .. types import sylist
from .. types import types
from .. utils import filebase
from .. utils.context import (deprecated_function, pending_deprecation,
                              inherit_doc)

RES_RE = re.compile('^__table_.*__$')
_TABLE_VERSION = '__table_version__'


def table_sql():
    """Avoid pre-loading table_sql."""
    from . import table_sql
    return table_sql


def _pandas():
    """
    Avoid pre-loading pandas.
    Pandas loads matplotlib taking loads of time.

    Matplotlib import has issues loading when python is installed on a unicode
    path causing unnecessary errors.
    """
    import pandas
    return pandas


def is_table(scheme, filename):
    """Return ``True`` if file at ``filename`` is represents a Table."""
    return File.is_type(filename, scheme)


def is_tables(scheme, filename):
    """
    Return ``True`` if file at ``filename`` is represents a list of Tables.
    """
    return FileList.is_type(filename, scheme)


def _reserved(name):
    return re.match(RES_RE, name)


def _reserved_attributes(attributes):
    return {k: v for k, v in attributes.items() if _reserved(k)}


def _ordinary_attributes(attributes):
    return {k: v for k, v in attributes.items() if not _reserved(k)}


@filebase.typeutil('sytypealias table = sytable')
@inherit_doc
class File(filebase.FileBase):
    """
    A Table with columns, where each column has a name and a data type.
    All columns in the Table must always be of the same length.

    Any node port with the *Table* type will produce an object of this kind.

    The data in the Table can be accessed in different ways depending on
    whether you plan on using numpy or pandas for processing the data.
    When using numpy you can access columns individually as numpy arrays via
    :meth:`get_column_to_array` and :meth:`set_column_from_array`::

        >>> from sympathy.api import table
        >>> mytable = table.File()
        >>> mytable.set_column_from_array('foo', np.array([1,2,3]))
        >>> print mytable.get_column_to_array('foo')
        [1 2 3]

    Or you can access them as pandas Series using :meth:`get_column_to_series`
    and :meth:`set_column_from_series`::

        >>> from sympathy.api import table
        >>> mytable = table.File()
        >>> mytable.set_column_from_series(pandas.Series([1,2,3], name='foo'))
        >>> print mytable.get_column_to_series('foo')
        0  1
        1  2
        2  3
        Name: foo, dtype: int64

    When working with the entire table at once you can choose between numpy
    recarrays (with :meth:`to_recarray` and :meth:`from_recarray`) or numpy
    matrices (:meth:`to_matrix` and :meth:`from_matrix`), or pandas data frame
    via the methods :meth:`to_dataframe` and :meth:`from_dataframe`.

    All these different ways of accessing the data can be mixed freely.
    """
    VERSION = '1.2'

    def _extra_init(self, gen, data, filename, mode, scheme, source):

        if source:
            self._data.update(source._data)
        else:
            if mode != 'r':
                attributes = self._data.get_table_attributes()
                if _TABLE_VERSION not in attributes:
                    attributes[_TABLE_VERSION] = self.VERSION
                    self._data.set_table_attributes(attributes)
                else:

                    self.version()

    def clear(self):
        """Clear the table. All columns and attributes will be removed."""
        for column_name in self.column_names():
            del self._data[column_name]
        self.set_table_attributes({})
        self.set_name(None)

    @deprecated_function
    def columns(self):
        """
        Return a list with the names of the table columns.

        .. deprecated:: 1.0
           Use :meth:`column_names` instead.
        """
        return self.column_names()

    def version(self):
        """
        Return the version as a string.
        This is useful when loading existing files from disk.

        .. versionadded:: 1.2.5
        """
        return self._data.get_table_attributes().get(_TABLE_VERSION, '1.2')

    def column_names(self):
        """Return a list with the names of the table columns."""
        return self._data.columns()

    def column_type(self, column):
        """Return the dtype of column named ``column``."""
        return self._data.column_type(column)

    def number_of_rows(self):
        """Return the number of rows in the table."""
        return self._data.number_of_rows()

    def number_of_columns(self):
        """Return the number of columns in the table."""
        return self._data.number_of_columns()

    def is_empty(self):
        """Returns ``True`` if the table is empty."""
        return self._data.is_empty()

    @deprecated_function
    def value(self):
        """
        Return numpy.recarray object with the table content.

        .. deprecated:: 1.0
           Use :meth:`to_recarray` instead.
        """
        return self.to_recarray()

    @staticmethod
    def from_recarray(recarray):
        """
        Write columns contained in numpy.recarray object ``recarray`` to table.
        """
        result = File()
        result._data.set(recarray)
        return result

    def to_recarray(self):
        """
        Return numpy.recarray object with the table content or None if there
        are no columns.
        """
        return self._data.value()

    @staticmethod
    def from_dataframe(dataframe):
        """
        Write columns contained in pandas DataFrame object ``dataframe`` to
        table.
        """
        result = File()
        for key, value in dataframe.iteritems():
            result._data.set_column(key, np.array(value.tolist()))

        return result

    def to_dataframe(self):
        """Return pandas DataFrame object with all columns in table."""
        return _pandas().DataFrame(collections.OrderedDict(
            (column, self.get_column_to_array(column))
            for column in self.column_names()), copy=True)

    @staticmethod
    def from_matrix(column_names, matrix):
        """
        Return a new :class:`table.File` with data from numpy matrix
        ``matrix``. ``column_names`` should be a list of strings which are
        used to name the resulting columns.
        """
        result = File()
        matrix = matrix.T
        if len(matrix) != len(column_names):
            raise ValueError(
                "The number of columns in matrix is not the same as the "
                "number of column names.")
        for key, value in zip(column_names, matrix):
            result._data.set_column(key, np.squeeze(np.asarray(value), 0))
        return result

    def to_matrix(self):
        """Return numpy matrix with all the columns in the table."""
        return np.mat(
            [self.get_column_to_array(column)
             for column in self.column_names()]).T

    @staticmethod
    def from_rows(column_names, rows):
        """
        Return new :class:`table.File` with data from iterable rows.
        ``column_names`` should be a list of strings which are used to name
        the resulting columns.
        """
        def tableiter(maxrows):
            rowiter = iter(rows)
            column_data = zip(*islice(rowiter, maxrows))
            if column_data:
                while column_data:
                    column_table = File()
                    for key, value in zip(column_names, column_data):
                        column_table.set_column_from_array(
                            key, np.array(value))
                    yield column_table
                    column_data = zip(*islice(rowiter, maxrows))
            else:
                column_table = File()
                void = np.array([], dtype=np.void)
                for key in column_names:
                    column_table.set_column_from_array(key, void)
                yield column_table

        # Set the size of the sub tables (in rows).
        # This will only be one row in the case where
        # number_of_columns >= maxcells.
        # Intended to limit memory use.
        maxcells = 2 ** 15
        number_of_columns = len(column_names)
        maxrows = max(1, maxcells / number_of_columns)
        result = File()
        result.vjoin(tableiter(maxrows), '', '', False, 0)
        return result

    def to_rows(self):
        """Return a generator over the table's rows."""
        # Set the size of the sub tables (in rows).
        # This will only be one row in the case where
        # number_of_columns >= maxcells.
        # Intended to limit memory use.
        maxcells = 2 ** 15
        number_of_columns = self.number_of_columns()
        maxrows = max(1, maxcells / number_of_columns)
        column_names = self.column_names()
        for i in xrange(0, self.number_of_rows(), maxrows):
            column_table = self[i: i + maxrows]
            for row in izip(*[column_table.get_column_to_array(key).tolist()
                              for key in column_names]):
                yield row

    @deprecated_function
    def set(self, recarray):
        """
        Write rec array.

        .. deprecated:: 1.0
           Use :meth:`from_recarray` instead.
        """
        table = self.from_recarray(recarray)
        for column_name in table.column_names():
            self.set_column_from_array(column_name,
                                       table.get_column_to_array(column_name))

    @deprecated_function
    def get(self, column_name):
        """
        Return numpy rec array.

        .. deprecated:: 1.0
           Use :meth:`to_recarray` instead.
        """
        return self[:][column_name].to_recarray()

    @deprecated_function
    def set_column(self, column_name, column):
        """
        Set a column.

        .. deprecated:: 1.0
           Use :meth:`set_column_from_array` instead.
        """
        return self.set_column_from_array(column_name, column)

    @deprecated_function
    def get_column(self, column_name):
        """
        Return numpy array.

        .. deprecated:: 1.0
           Use :meth:`get_column_to_array` instead.
        """
        return self.get_column_to_array(column_name)

    def set_column_from_array(self, column_name, array, attributes=None):
        """
        Write numpy array to column named by column_name.
        If the column already exists it will be replaced.
        """
        self._data.set_column(column_name, array)

        if attributes is not None:
            self.set_column_attributes(column_name, attributes)

    def get_column_to_array(self, column_name, index=None):
        """Return named column as a numpy array."""
        return self._data.get_column(column_name, index)

    def set_column_from_series(self, series):
        """
        Write pandas series to column named by series.name.
        If the column already exists it will be replaced.
        """
        if series.name is None:
            raise Exception('Series needs to have a name; assign series.name.')
        self._data.set_column(series.name, series.values)

    def get_column_to_series(self, column_name):
        """Return named column as pandas series."""
        return _pandas().Series(
            self._data.get_column(column_name), name=column_name, copy=True)

    def set_name(self, name):
        """Set table name. Use None to unset the name."""
        self._data.set_name(name)

    def get_name(self):
        """Return table name or None if name is not set."""
        return self._data.get_name()

    def get_column_attributes(self, column_name):
        """Return dictionary of attributes for column_name."""
        return self._data.get_column_attributes(column_name).get()

    def set_column_attributes(self, column_name, attributes):
        """
        Set dictionary of scalar attributes for column_name.

        Attribute values can be any numbers or strings.
        """
        self._data.get_column_attributes(column_name).set(attributes)

    def get_table_attributes(self):
        """Return dictionary of attributes for table."""
        return _ordinary_attributes(self._data.get_table_attributes())

    def set_table_attributes(self, attributes):
        """
        Set table attributes to those in dictionary attributes.

        Attribute values can be any numbers or strings. Replaces any old table
        attributes.

        Example::

            >>> from sympathy.api import table
            >>> mytable = table.File()
            >>> mytable.set_table_attributes(
            ...     {'Thou shall count to': 3,
            ...      'Ingredients': 'Spam'})
        """
        attributes = dict(attributes)
        reserved = _reserved_attributes(self._data.get_table_attributes())
        attributes.update(reserved)
        self._data.set_table_attributes(attributes)

    def get_attributes(self):
        """
        Get all table attributes and all column attributes.

        Returns a tuple where the first element contains all the table
        attributes and the second element contains all the column attributes.
        """
        return (self.get_table_attributes(),
                {column: self.get_column_attributes(column)
                 for column in self.column_names()})

    def set_attributes(self, attributes):
        """Set table attributes and column attrubutes at the same time.

        Input should be a tuple of dictionaries where the first element of the
        tuple contains the table attributes and the second element contains the
        column attributes.
        """
        if not (isinstance(attributes, tuple) or isinstance(attributes, list)):
            raise ValueError(
                "attributes must be either list or tuple not {}.".format(
                    type(attributes)))
        if len(attributes) != 2:
            raise ValueError("attributes must have exactly two elements.")

        self.set_table_attributes(attributes[0])
        for column in set(self.column_names()) & set(attributes[1].keys()):
            self.set_column_attributes(column, attributes[1][column])

    def update(self, other_table):
        """
        Updates the columns in the table with columns from other table keeping
        the old ones.

        If a column exists in both tables the one from other_table is used.
        Creates links where possible.
        """
        self._data.update(other_table._data)

    def update_column(self, column_name, other_table, other_name=None):
        """
        Updates a column from a column in another table.

        The column other_name from other_table will be copied into column_name.
        If column_name already exists it will be replaced.

        When other_name is not used, then column_name will be used instead.
        """
        if other_name is None:
            other_name = column_name

        self._data.update_column(
            column_name, other_table._data, other_name)

    def __getitem__(self, index):
        """
        :rtype: table.File

        Return a new :class:`table.File` object with a subset of the table
        data.

        This method fully supports both one- and two-dimensional single indices
        and slices.

        Examples::

            >>> from sympathy.api import table
            >>> mytable = table.File.from_rows(
            ...     ['a', 'b', 'c'],
            ...     [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
            >>> mytable.to_dataframe()
               a  b  c
            0  1  2  3
            1  4  5  6
            2  7  8  9
            >>> mytable[1].to_dataframe()
               a  b  c
            0  4  5  6
            >>> mytable[:,1].to_dataframe()
               b
            0  2
            1  5
            2  8
            >>> mytable[1,1].to_dataframe()
               b
            0  5
            >>> mytable[:2,:2].to_dataframe()
               a  b
            0  1  2
            1  4  5
            >>> mytable[::2,::2].to_dataframe()
               a  c
            0  1  3
            1  7  9
            >>> mytable[::-1,:].to_dataframe()
               a  b  c
            0  7  8  9
            1  4  5  6
            2  1  2  3
        """
        return File(data=self._data[index])

    def __setitem__(self, index, other_table):
        """
        Update the values at index with the values from other_table.

        This method fully supports both one- and two-dimensional single indices
        and slices, but the dimensions of the slice must be the same as the
        dimensions of other_table.
        """
        self._data[index] = other_table._data

    def __contains__(self, key):
        """
        Return True if table contains a column named key.

        Equivalent to :meth:`has_column`.
        """
        return self._data.has_column(key)

    def has_column(self, key):
        """
        Return True if table contains a column named key.

        .. versionadded:: 1.1.3
        """
        return self._data.has_column(key)

    def hjoin(self, other_table):
        """
        Add the columns from other_table.

        Analoguous to :meth:`update`.
        """
        sybase.hjoin(self._data, other_table._data)

    def vjoin(self, other_tables, input_index='', output_index='', fill=True,
              minimum_increment=1):
        """
        Add the rows from the other_tables at the end of this table.
        """
        input_list = sylist(types.from_string('[sytable]'))
        for other_table in other_tables:
            input_list.append(other_table._data)
        sybase.vjoin(self._data, input_list, input_index, output_index, fill,
                     minimum_increment)

    def vsplit(self, output_list, input_index, remove_fill):
        """Split the current table to a list of tables by rows."""
        temp_list = []
        sybase.vsplit(
            self._data, temp_list, input_index, remove_fill)
        for pair in temp_list:
            output_list.append(File(data=pair[1]))

    def source(self, other_table):
        self._data.source(other_table._data)

    @pending_deprecation()
    def set_source_id(self, identifier):
        """Set source identifier. Not implemented."""
        pass

    def __copy__(self):
        obj = super(File, self).__copy__()
        obj._data = self._data.__copy__()
        return obj

    def __deepcopy__(self, memo=None):
        obj = super(File, self).__copy__()
        obj._data = self._data.__deepcopy__()
        return obj

    @property
    def name(self):
        name = self._data.get_name()
        return name if name is not None else ''

    def attr(self, name):
        """Get the tables attribute with `name`."""
        attributes = _ordinary_attributes(self._data.get_table_attributes())
        return attributes.get(name, '')

    def col(self, name):
        """Get a column object for column with `name`."""
        return Column(name, self._data)


@inherit_doc
class FileList(filebase.FileListBase):
    """
    The :class:`FileList` class is used when working with lists of Tables.

    The main interfaces in :class:`FileList` are indexing or iterating for
    reading (see the :meth:`__getitem__` method) and the :meth:`append` method
    for writing.

    Any port with the *Tables* type will produce an object of this kind. If it
    is an input port the :class:`FileList` will be in read-through mode,
    disallowing any write actions and disabling list level caching. If it is an
    output port the :class:`FileList` will be in write-through mode,
    disallowing any read actions and making methods like :meth:`append` trigger
    an imidiate writeback of that element.
    """
    sytype = '[table]'
    scheme = 'hdf5'


class Column(object):
    """
    The :class:`Column` class is used when working with columns of Tables.
    """
    def __init__(self, name, parent_data):
        self._name = name
        self._data = parent_data

    @property
    def data(self):
        return self._data.get_column(self._name)

    @property
    def name(self):
        return self._name

    def attr(self, name):
        return self._data.get_column_attributes(self._name).get_attribute(name)
