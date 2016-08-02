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
"""Base module for sy-type containers."""
from collections import OrderedDict
from itertools import izip

import numpy as np
from . import exception as exc


def assert_type(group, type1, type2):
    """
    Asserts that the types are the same,
    raises TypeError otherwise.
    """
    try:
        assert(type1 == type2)
    except:
        type1 == type2
        name = group.__class__.__name__
        raise TypeError(
            "'{0}', unmatched types for operation '{1}' != '{2}'".format(
                name, type1, type2))


class GroupVisitor(object):
    """Visitor interface for sygroups."""
    def visit_dict(self, sydict):
        """Visit dict group."""
        raise NotImplementedError

    def visit_list(self, sylist):
        """Visit list group."""
        raise NotImplementedError

    def visit_record(self, syrecord):
        """Visit record group."""
        raise NotImplementedError

    def visit_table(self, sytable):
        """Visit table group."""
        raise NotImplementedError

    def visit_text(self, sytext):
        """Visit text group."""
        raise NotImplementedError


class VJoinVisitor(GroupVisitor):
    """Visitor that joins groups vertically."""

    def __init__(self, current, input_index, output_index, fill,
                 minimum_increment):
        self.current = current
        self.input_index = input_index
        self.output_index = output_index
        self.fill = fill
        self.minimum_increment = minimum_increment

    def visit_list(self, sylist):
        """
        VJoin common table columns.

        A index column named by self.index_name will be created to clarify
        interpretation.
        """
        def index(sytable):
            try:
                return sytable.get_column(self.input_index)
            except:
                return np.array([0] * sytable.number_of_rows(), dtype=int)

        def column_or_nan(sytable, column, length):
            try:
                return sytable.get_column(column)
            except:
                return int(length)

        def fill(columns):
            test = []
            for column in columns:
                try:
                    if column.size:
                        test.append(column[:0])
                except:
                    pass
            test = [[]] if not test else test
            dtype = np.hstack(test).dtype
            kind = dtype.kind

            if kind in ['S', 'U']:
                filler = lambda x: np.zeros(x, dtype='S1')
            else:
                filler = lambda x: np.zeros(x, dtype='f4') * np.nan

            result = [filler(column)
                      if isinstance(column, int)
                      else column for column in columns]
            if not result:
                result.append([])

            return result

        common_columns = set()
        all_columns = []
        order = OrderedDict()
        offset = 0
        indices = [[]]
        lengths = []

        # Pre-compute columns etc.
        for item in sylist:
            item_columns = item.columns()
            all_columns.append(item_columns)
            order.update(OrderedDict.fromkeys(item_columns))
            current_index = index(item)
            length = item.number_of_rows()
            minimum = np.min(current_index) if length else 0
            indices.append(current_index + (offset - minimum))

            offset += (np.max(current_index) - minimum + 1
                       if length else
                       self.minimum_increment)

            lengths.append(length)

        # Keep only common columns except when in fill mode.
        if not self.fill:
            try:
                common_columns.update(order.keys())
                for current_columns in all_columns:
                    if current_columns:
                        common_columns = common_columns.intersection(
                            current_columns)
            except:
                pass
            order = OrderedDict.fromkeys(
                [key for key in order.keys() if key in common_columns])

        # VJoin columns and attributes.
        for column in order:
            data = []
            attrs = {}

            if self.fill:
                for i, item in enumerate(sylist):
                    data.append(column_or_nan(item, column, lengths[i]))
                    if column in all_columns[i]:
                        attrs.update(item.get_column_attributes(column).get())
            else:
                for length, item in izip(lengths, sylist):
                    if length:
                        data.append(item.get_column(column))
                    try:
                        attrs.update(item.get_column_attributes(column).get())
                    except KeyError:
                        pass
            self.current.set_column(column, np.hstack(fill(data)))
            self.current.get_column_attributes(column).set(attrs)

        # VJoin index column.
        if self.current.number_of_columns() and self.output_index:
            self.current.set_column(self.output_index, np.hstack(indices))


class VSplitVisitor(GroupVisitor):
    """Visitor that split groups vertically."""

    def __init__(self, output_list, input_index, remove_fill):
        self.output_list = output_list
        self.remove_fill = remove_fill
        self.input_index = input_index

    def visit_table(self, sytable):
        """
        VSplit table columns.

        Split table into a list of tables.
        If a column named input_index is available then it will be used to
        group the output. Otherwise the split will operate as if a split column
        with values: 0...sytable.number_of_row() existed.

        The in either case, the index column, will not be written to the
        output.
        """
        def index(sytable):
            try:
                return sytable.get_column(self.input_index)
            except:
                return np.arange(sytable.number_of_rows())

        def slices_using_group_array(group_array):
            """Return the slices to split by.
            A group array is made of strictly increasing group identifiers.

            >>> slices_using_group_array(np.array([0, 0, 0, 1, 1, 2, 3, 3, 3]))
            [(0, 3), (3, 5), (5, 6), (6, 9)]
            """
            unique_elements = np.unique(group_array)
            slices = []
            for unique_element in unique_elements:
                indexes = np.flatnonzero(group_array == unique_element)
                low, high = (indexes[0], indexes[-1] + 1)
                slices.append((unique_element, slice(low, high)))
            return slices

        def indices_using_group_array(group_array):
            """
            Return list of index lists, ordered by first occurance of value.
            """
            unique_elements = np.unique(group_array)
            indices = []
            for unique_element in unique_elements:
                indices.append((unique_element,
                                np.flatnonzero(group_array == unique_element)))
            return indices

        columns = sytable.columns()
        # Perform the split and append the new tables to output.
        slice_indices = indices_using_group_array(index(sytable))
        column_attrs = {}

        for unique_element, slice_index in slice_indices:
            # Sets of all columns except for the INDEX columns.
            result = type(sytable)(sytable.container_type)
            self.output_list.append((unique_element, result))

            for column in columns:
                array = sytable.get_column(column)[slice_index]
                if self.remove_fill and len(array):
                    kind = array.dtype.kind
                    if kind in ['S', 'U']:
                        if np.all(array == ''):
                            continue
                    else:
                        if not len(array) or np.isnan(np.min(array)):
                            continue

                result.set_column(column, array)
                if column in column_attrs:
                    attrs = column_attrs[column]
                else:
                    attrs = dict(
                        sytable.get_column_attributes(column).get())
                    column_attrs[column] = attrs
                result.get_column_attributes(column).set(attrs)


class SpineCopyVisitor(GroupVisitor):
    """
    Visitor that copies the container spine structure.
    Non-container types: sytable and sytext are referenced instead
    of copied.
    """
    def __init__(self, current):
        self.current = current

    def visit_dict(self, sydict):
        """
        Copy elements of other dict and proceed with
        visiting each copy using the same visitor.
        """
        for key, value in sydict.items():
            child = type(value)(value.container_type)
            self.current[key] = child
            value.visit(SpineCopyVisitor(child))

    def visit_list(self, sylist):
        """
        Copy elements of other sylist and proceed with
        visiting each copy using the same visitor.
        """
        for value in sylist:
            child = type(value)(value.container_type)
            self.current.append(child)
            value.visit(SpineCopyVisitor(child))

    def visit_record(self, syrecord):
        """
        Copy elements of other record and proceed with
        visiting each copy using the same visitor.
        """
        for key, value in syrecord.items():
            child = type(value)(value.container_type)
            setattr(self.current, key, child)
            value.visit(SpineCopyVisitor(child))

    def visit_table(self, sytable):
        """Update table with content of other table."""
        self.current.update(sytable)

    def visit_text(self, sytext):
        """Update text with content of other text."""
        self.current.update(sytext)


class HJoinVisitor(GroupVisitor):
    """Visitor that joins groups horizontally."""

    def __init__(self, current):
        self.current = current

    def visit_dict(self, sydict):
        """HJoin dict with other dict."""
        self.current.update(sydict)

    def visit_list(self, sylist):
        """
        Iterate over list and hjoin the list type with the matching
        element from the other list.
        """
        if len(self.current) == 0:
            self.current.extend(sylist)

        for item, other_item in izip(self.current, sylist):
            hjoin(item, other_item)

    def visit_record(self, syrecord):
        """
        HJoin current record with items from 'other record'. If 'key'
        already exist hjoin the existing value with other_value.
        HJoin requires the item types to match.
        """
        for other_key, other_value in syrecord.items():
            try:
                getattr(self.current, other_key).update(other_value)
            except KeyError:
                setattr(self.current, other_key, other_value)

    def visit_table(self, sytable):
        """
        HJoin the columns in the table with columns from other table.
        Overwrite if already exist.
        """
        self.current.update(sytable)

    def visit_text(self, sytext):
        """
        HJoin the columns in the table with columns from other table.
        Overwrite if already exist.
        """
        self.current.update(sytext)


def hjoin(first_sygroup, second_sygroup):
    """HJoin first and second sygroup using the HJoinVisitor."""
    visitor = HJoinVisitor(first_sygroup)
    second_sygroup.visit(visitor)


def vjoin(output_table, sylist, input_index, output_index, fill,
          minimum_increment):
    """VJoin first and second sygroup using the VJoinVisitor."""
    visitor = VJoinVisitor(output_table, input_index, output_index, fill,
                           minimum_increment)
    sylist.visit(visitor)


def vsplit(sytable, output_list, input_index, remove_fill):
    """VSplit sytable"""
    visitor = VSplitVisitor(output_list, input_index, remove_fill)
    sytable.visit(visitor)


def spinecopy(sygroup_):
    """
    Copy sygroup container structure updated with non-container types.
    Container types: sydict, sylist and syrecord are copied.
    Non-container types: sytable and sytext are updated.
    """
    copy = type(sygroup_)(sygroup_.container_type)
    visitor = SpineCopyVisitor(copy)
    sygroup_.visit(visitor)
    return copy


class Mutator(object):
    def get(self, name=None):
        """
        Get elements from a collection.
        Returns:
            A copy of the entire collection when name is None.
            A single element collection with named element when the name is
            not None.
        """
        raise NotImplementedError

    def set(self, properties):
        """Set the elements of a collections to the content of properties."""
        raise NotImplementedError

    def delete(self, name=None):
        """
        Remove elements from a collections.
        Removes:
            Every item in the entire collection when the name is None.
            Named element when name is not None.
        """
        raise NotImplementedError


class sygroup(object):
    """Base class for sy-type containers."""
    def __init__(self, container_type, datasource):
        from . factory import typefactory
        self.container_type = container_type
        self._datasource = datasource
        self._datadestination = datasource
        self._factory = typefactory
        self._dirty = True

    def is_valid(self):
        return True

    def source(self, other):
        """
        Update self with a deepcopy of the data from other, without keeping the
        old state.

        self and other must be of the exact same type.
        """
        raise NotImplementedError

    def _writeback(self, datasource, link=None):
        """
        Write back contained information to datasource.
        When link is not None then the operation will attempt to create a link.

        Returns True if data was written/linked and False otherwise.
        """
        raise NotImplementedError

    def writeback(self):
        """Write back contained information to datasource."""
        exc.assert_exc(
            self._datadestination.can_write, exc=exc.WritebackReadOnlyError)
        self._writeback(self._datadestination)

    def _link(self, datasource, key):
        """
        Write link to the internal datasource datasource in the external
        datasource, if possible.

        Returns True if a link was written and False otherwise.
        """
        if not self._dirty and datasource.transferable(self._datasource):
            datasource.link_with(key, self._datasource)
            return True

        return False

    def __copy__(self):
        cls = type(self)
        obj = cls.__new__(cls)
        obj.container_type = self.container_type
        obj._datasource = self._datasource
        obj._factory = self._factory
        obj._dirty = self._dirty
        return obj

    def visit(self, group_visitor):
        """Accept group visitor."""
        raise NotImplementedError


class NullSource(object):
    """Null datasource."""
    can_link = False
    can_write = None

    def number_of_rows(self):
        return 0

    def number_of_columns(self):
        return 0

    @staticmethod
    def writeback(datasource):
        """Null writeback."""
        pass

    @staticmethod
    def transferable(datasource):
        """Null transferable."""
        return False

    @staticmethod
    def transfer(name, other, other_name):
        """Null transfer."""
        pass

    @staticmethod
    def shares_origin(other_datasource):
        """Null shares_origin."""
        return False

    @staticmethod
    def read_with_type(key, content_type):
        """Null read_with_type."""
        raise KeyError()

    @staticmethod
    def write_with_type(key, value, content_type):
        """Null write_with_type."""
        pass

    @staticmethod
    def size():
        """Null size."""
        return 0

    @staticmethod
    def columns():
        """Null columns."""
        return []

    @staticmethod
    def read_name():
        return None

    @staticmethod
    def write_name(name):
        pass

    @staticmethod
    def write_finished():
        pass

    @staticmethod
    def write_started(number_of_rows, number_of_columns):
        pass

    @staticmethod
    def read_column_attributes(self, column_name):
        """Null read_column_attributes."""
        return None

    @staticmethod
    def write_column_attributes(self, column_name, properties):
        """Null read_column_attributes."""
        pass

    def read_table_attributes(self):
        """Null read_table_attributes."""
        return None

    def write_table_attributes(self, properties):
        """Null write_table_attributes."""
        pass

    @staticmethod
    def read_column(column_name, index=None):
        """Null read_columns."""
        return None

    @staticmethod
    def write_column(column_name, column):
        """Null write_columns."""
        pass

    @staticmethod
    def items(content_type):
        """Null items."""
        return []

    @staticmethod
    def keys(self):
        """Null keys."""
        return []

    @staticmethod
    def read():
        """Null read."""
        return ''

    @staticmethod
    def write(text):
        """Null write."""
        pass

NULL_SOURCE = NullSource()
