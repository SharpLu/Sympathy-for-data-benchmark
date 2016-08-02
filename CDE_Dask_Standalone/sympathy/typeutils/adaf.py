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
API for working with the ADAF type.

Import this module like this::

    from sympathy.api import adaf


The ADAF structure
------------------
An ADAF consists of three parts: meta data, results, and time series.

Meta data contains information about the data in the ADAF. Stuff like when,
where and how it was measured or what parameter values were used to generated
it. A general guideline is that the meta data should be enough to (at least in
theory) reproduce the data in the ADAF.

Results and time series contain the actual data. Results are always scalar
whereas the time series can have any number of values.

Time series can come in several systems and each system can contain several
rasters. Each raster in turn has one basis and any number of time series. So
for example an experiment where some signals are sampled at 100Hz and others
are sampled only once per second would have (at least) two rasters. A basis
doesn't have to be uniform but can have samples only every now and then.

.. TODO: When to use ADAF and why not just use several tables.

.. _accessing_adaf:

Accessing the data
------------------
The :class:`adaf.File` object has two members called ``meta`` and ``res``
containing the meta data and results respectively. Both are :class:`Group`
objects.

Example of how to use ``meta`` (``res`` is completely analogous):
    >>> from sympathy.api import adaf
    >>> import numpy as np
    >>> f = adaf.File()
    >>> f.meta.create_column(
    ...     'Duration', np.array([3]), {'unit': 'h'})
    >>> f.meta.create_column(
    ...     'Relative humidity', np.array([63]), {'unit': '%'})
    >>> print f.meta['Duration'].value()
    [3]
    >>> print f.meta['Duration'].attr['unit']


Time series can be accessed in two different ways. Either via the member
``sys`` or via the member ``ts``. Using sys is generally recommended since
``ts`` handles multiple time series with the same name across different rasters
poorly. Using the member ``tb`` should be considered obsolete.

Example of how to use sys:
    >>> f.sys.create('Measurement system')
    >>> f.sys['Measurement system'].create('Raster1')
    >>> f.sys['Measurement system']['Raster1'].create_basis(
    ...     np.array([0.01, 0.02, 0.03]),
    ...     {'unit': 's'})
    >>> f.sys['Measurement system']['Raster1'].create_signal(
    ...     'Amount of stuff',
    ...     np.array([1, 2, 3]),
    ...     {'unit': 'kg'})
    >>> f.sys['Measurement system']['Raster1'].create_signal(
    ...     'Process status',
    ...     np.array(['a', 'b', 'c']),
    ...     {'description': 'a=awesome, b=bad, c=critical'})
    >>> f.sys.keys()
    ['Measurement system']
    >>> f.sys['Measurement system'].keys()
    ['Raster1']
    >>> f.sys['Measurement system']['Raster1'].keys()
    ['Signal1', 'Signal2']
    >>> print f.sys['Measurement system']['Raster1']['Signal1'].t
    [ 0.01  0.02  0.03]
    >>> print f.sys['Measurement system']['Raster1']['Signal1'].y
    [1 2 3]
    >>> print f.sys['Measurement system']['Raster1']['Signal1'].unit()
    kg

The rasters are of type :class:`RasterN`.


Class :class:`adaf.File`
------------------------
.. autoclass:: File
   :members:

Class :class:`text.FileList`
----------------------------
.. autoclass:: FileList
   :members: __getitem__, append

Class :class:`Group`
--------------------
.. autoclass:: Group
   :members:

Class :class:`RasterN`
----------------------
.. autoclass:: RasterN
   :members:

Class :class:`Timeseries`
-------------------------
.. autoclass:: Timeseries
   :members:

Class :class:`Column`
---------------------
.. autoclass:: Column
   :members:
"""
from collections import OrderedDict
from datetime import datetime
from getpass import getuser
from os import getenv
import sys
import numpy as np

from . import table as ttable
from .. dataexporters import utils as dsutils
from .. types import sybase
from .. types import sylist
from .. types import types
from .. types.factory import typefactory
from .. utils import filebase
from .. utils.dtypes import get_pretty_type
from .. utils.prim import combined_key
from .. platform import exceptions
from .. utils.context import inherit_doc

fs_encoding = sys.getfilesystemencoding()


def datetime_to_isoformat_string(datetime_object):
    return datetime_object.isoformat()


def isoformat_string_to_datetime(isoformat_string):
    try:
        return datetime.strptime(
            isoformat_string, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        return datetime.strptime(
            isoformat_string, "%Y-%m-%dT%H:%M:%S")


def is_adaf(scheme, filename):
    return File.is_type(filename, scheme)


def is_adafs(scheme, filename):
    return FileList.is_type(filename, scheme)


def exporter_factory(exporter_type):
    return dsutils.adaf_exporter_factory(exporter_type)


def plural(count):
    """
    Return plural word ending for english.
    I.e. u's' if count != 1 else u''.
    """
    return u's' if count != 1 else u''


def non_unique(values):
    """Return a set of non-unique values for iterable values."""
    dups = set()
    for i, value in enumerate(values):
        # Only look forward, cause we already checked earlier values
        if value in values[i+1:]:
            dups.add(value)
    return dups


def check_raster_bases(sys):
    """Return a list of all raster that have no basis."""
    rasters_wo_bases = []
    for sname, system in sys.items():
        for rname, raster in system.items():
            try:
                raster.basis_column()
            except KeyError:
                if sname:
                    rasters_wo_bases.append(u"'{}'/'{}'".format(sname, rname))
                else:
                    rasters_wo_bases.append(u"'{}'".format(rname))
    return rasters_wo_bases


def sys_warnings(sys):
    """
    Return a list of string warnings for a mapping of rasters.
    Warns about rasters without bases and conflicting time series names.
    """
    systems = [system for system in sys.keys()]
    rasters = []
    for system in systems:
        rasters.extend(sys[system].values())
    ts = []
    for raster in rasters:
        ts.extend(raster.keys())
    lines = []

    # Warn about name conflicts
    name_conflicts = non_unique(ts)
    if name_conflicts:
        c = len(name_conflicts)
        if c != 1:
            lines.append(
                u"Warning: {} time series names "
                u"occur more than once.".format(c))
        else:
            lines.append(
                u"Warning: Time series name '{}' "
                u"occur more than once.".format(name_conflicts.pop()))

    # Warn about rasters without bases
    rasters_wo_bases = check_raster_bases(sys)
    if rasters_wo_bases:
        c = len(rasters_wo_bases)
        if c != 1:
            lines.append(u"Warning: {} rasters have no bases".format(c))
        else:
            lines.append(u"Warning: Raster '{}' has no basis".format(
                rasters_wo_bases[0]))
    return lines


def descriptive_narray(name, narray):
    return u"  .{0} => {1}".format(name, short_narray(narray))


def short_narray(narray):
    # Temporarily change the way numpy prints
    old_options = np.get_printoptions()
    np.set_printoptions(precision=4, suppress=True, threshold=12)
    pretty_narray = repr(narray)
    np.set_printoptions(**old_options)
    return pretty_narray


@filebase.typeutil('sytypealias adaf = (meta: sytable, res: sytable, root: sytable, sys:{(attr:sytable, data:{(attr:sytable, data:sytable)})})')
@inherit_doc
class File(filebase.FileBase):
    """
    File represents the top level of the ADAF format.

    Any node port with the *ADAF* type will produce an object of this kind.

    Use the members ``meta``, ``res`` and ``sys`` to access the data.
    See :ref:`accessing_adaf` for an example.
    """
    VERSION = '1.2'

    def _extra_init(self, gen, data, filename, mode, scheme, source):
        if source:
            self.source(source)
        else:
            self.meta = Group(self._data.meta, name="meta")
            self.res = Group(self._data.res, name="res")
            self.root = Group(self._data.root, name="root")
            self.sys = SystemGroupContainer(self._data.sys, name='sys')

            self.ts = TimeseriesGroup(self.sys)

            if mode != 'r':

                if not self.package_id():
                    self.__set_package_id()
                if not self.timestamp():
                    self.__set_timestamp()
                if not self.user_id():
                    self.__set_user_id()
                if not self._get_file_attribute('version'):
                    self.__set_version()

    @property
    def tb(self):
        raise Exception("Avoid using 'tb' member, use 'sys' instead.")

    @tb.setter
    def tb(self, value):
        raise Exception("Avoid using 'tb' member, use 'sys' instead.")

    def hjoin(self, other_adaf):
        """HJoin ADAF with other ADAF. See also node :ref:`HJoin ADAF`."""
        self.meta.hjoin(other_adaf.meta)
        self.res.hjoin(other_adaf.res)
        self.sys.hjoin(other_adaf.sys)

    def vjoin(self, other_adafs, input_index, output_index, fill,
              minimum_increment, include_rasters=False,
              use_reference_time=False):
        """VJoin ADAF with other ADAF. See also node :ref:`VJoin ADAF`."""
        basis_name = '__hopefully_unique_adaf_basis_name__'
        from_seconds = {'us': 1e6, 'ms': 1e3, 's': 1}
        raster_times = []

        def fill_empty(enum_rasters):
            curr = 0
            empty = ttable.File()
            result = []
            for i, raster_table in enum_rasters:
                result.extend([empty] * (i - curr))
                result.append(raster_table)
                curr = i + 1
            return result

        def update_reference_time(raster_table, timedelta, unit):
            attributes = raster_table.get_column_attributes(basis_name)
            offset = timedelta.total_seconds() * from_seconds[unit]
            raster_table.set_column_from_array(
                basis_name,
                raster_table.get_column_to_array(basis_name) + offset)
            raster_table.set_column_attributes(basis_name, attributes)

        self.meta.vjoin(
            [other.meta for other in other_adafs], input_index, output_index,
            fill, minimum_increment)
        self.res.vjoin(
            [other.res for other in other_adafs], input_index, output_index,
            fill, minimum_increment)

        if include_rasters:
            raster_lookup = {}
            for i, other_adaf in enumerate(other_adafs):
                for system_key, system_value in other_adaf.sys.items():
                    system = raster_lookup.setdefault(system_key, {})
                    for raster_key, raster_value in system_value.items():
                        system.setdefault(raster_key, []).append(
                            (i, raster_value))
                        if use_reference_time:
                            raster_times.append(
                                raster_value.attr.get_or_empty(
                                    'reference_time'))

            if use_reference_time:
                raster_times = [rtime for rtime in raster_times if rtime]
                reftime_min = min(raster_times) if raster_times else None

            for system_key, system_value in raster_lookup.iteritems():
                system = self.sys.create(system_key)
                for raster_key, raster_value in system_value.iteritems():
                    raster = system.create(raster_key)
                    raster_table = ttable.File()
                    raster_new = []
                    raster_times = []
                    last_unit = None

                    for i, rastern in raster_value:
                        reftime = rastern.attr.get_or_empty(
                            'reference_time')
                        unit = rastern.basis_column().attr.get_or_empty(
                            'unit')

                        if use_reference_time:
                            if reftime != '' and unit != '':
                                if last_unit and last_unit != unit:
                                    print('Excluding raster with different'
                                          ' unit.')
                                    continue
                                raster_new.append(
                                    (i,
                                     rastern.to_table(basis_name=basis_name)))
                                raster_times.append(reftime)
                            else:
                                print('Excluding raster missing '
                                      'reference_time or unit.')
                        else:
                            raster_new.append((
                                i,
                                rastern.to_table(basis_name=basis_name)))
                    last_unit = unit

                    if raster_new:
                        if use_reference_time:
                            for (i, rastert), reftime, in zip(raster_new,
                                                              raster_times):
                                update_reference_time(
                                    rastert,
                                    reftime - reftime_min,
                                    unit)

                        raster_table.vjoin(
                            [rastert
                             for rastert in fill_empty(raster_new)],
                            input_index, output_index, fill, minimum_increment)

                        if (use_reference_time
                                and raster_table.number_of_columns()):
                            raster_table = ttable.File.from_dataframe(
                                raster_table.to_dataframe().sort(
                                    basis_name, ascending=True))
                        raster_table.set_name(raster_key)

                        try:
                            for column_name in raster_table.column_names():
                                raster_table.set_column_attributes(
                                    column_name,
                                    raster_new[0][1].get_column_attributes(
                                        column_name))
                        except KeyError:
                            pass

                        raster.from_table(raster_table, basis_name=basis_name,
                                          use_basis_name=False)

                        if use_reference_time and reftime_min is not None:
                            raster.attr.set('reference_time', reftime_min)

    def vsplit(self, other_adafs, input_index, remove_fill, require_index,
               include_rasters=False):
        """
        VSplit ADAF, appending the resulting ADAFs onto ``other_adafs`` list.
        """
        meta_keys = self.meta.keys()
        res_keys = self.res.keys()

        if require_index and meta_keys and input_index not in meta_keys:
            raise Exception(
                'Meta missing Input Index {0}'.format(input_index))

        if require_index and res_keys and input_index not in self.res.keys():
            raise Exception(
                'Res missing Input Index {0}'.format(input_index))

        meta_list = []
        sybase.vsplit(
            self.meta.to_table()._data, meta_list, input_index, remove_fill)
        res_list = []
        sybase.vsplit(
            self.res.to_table()._data, res_list, input_index, remove_fill)

        ts_dict = {}
        basis_name = '__hopefully_unique_adaf_basis_name__'

        if include_rasters:
            for system_key, system_value in self.sys.items():
                for raster_key, raster_value in system_value.items():
                    ts_list = []
                    try:
                        raster_table = raster_value.to_table(
                            basis_name=basis_name)
                        sybase.vsplit(
                            raster_table._data,
                            ts_list,
                            input_index,
                            remove_fill)
                    except KeyError:
                        # Assuming that the raster is empty and failing due to
                        # missing named basis.
                        pass
                    for key, value in ts_list:
                        ts_group = ts_dict.setdefault(key, {})
                        ts_system = ts_group.setdefault(system_key, {})
                        ts_system[raster_key] = value

        meta_dict = OrderedDict(meta_list)
        res_dict = OrderedDict(res_list)

        for key in sorted(set(
                meta_dict.keys() + res_dict.keys() + ts_dict.keys())):
            adaf = File()
            if key in meta_dict:
                adaf.meta.from_table(ttable.File(data=meta_dict[key]))
            if key in res_dict:
                adaf.res.from_table(ttable.File(data=res_dict[key]))
            if include_rasters and key in ts_dict:
                systems = {}
                for system_key, system_value in ts_dict[key].iteritems():
                    if system_key in systems:
                        system = systems[system_key]
                    else:
                        system = adaf.sys.create(system_key)
                        systems[system_key] = system
                    for raster_key, raster_value in system_value.iteritems():
                        raster = system.create(raster_key)
                        raster.from_table(ttable.File(data=raster_value),
                                          basis_name=basis_name)

            other_adafs.append(adaf)

    def source(self, other_adaf):
        """Use the data from ``other_adaf`` as source for this file."""
        self._data.source(other_adaf._data)
        self.meta = Group(self._data.meta, name="meta")
        self.res = Group(self._data.res, name="res")
        self.root = Group(self._data.root, name="root")
        self.sys = SystemGroupContainer(self._data.sys, name='sys')
        self.ts = TimeseriesGroup(self.sys)

    def _set_file_attribute(self, key, value):
        """Set an ADAF file attribute updating it if it has already been set.
        """
        self.root.set_attribute(key, value)

    def _get_file_attribute(self, key):
        """Get an ADAF file attribute or an empty string if the attribute
        hasn't been set."""
        # Two different storage models have been used for file attributes:
        #   1. Stored as attributes on root table. (Used from version 1.1.2)
        #   2. Stored as zero-dimensional numpy arrays in self.root.
        #      (Used from version 1.0)
        # This method tries both storage models for backwards compatibility but
        # favors 1 if both exist.
        attrs = self.root.get_attributes()
        if key in attrs:
            return attrs[key]
        elif key in self.root:
            try:
                return np.unicode_(self.root[key].value())
            except KeyError:
                return u''
        else:
            return u''

    def package_id(self):
        """Get the package identifier string."""
        return self._get_file_attribute('package_id')

    def source_id(self):
        """Get the source identifier string. If the source identifier has not
        been set, it will default to an empty string."""
        return self._get_file_attribute('source_id')

    def timestamp(self):
        """Get the time string."""
        return self._get_file_attribute('timestamp')

    def user_id(self):
        """Get the user identifier string."""
        return self._get_file_attribute('user_id')

    def version(self):
        """
        Return the version as a string.
        This is useful when loading existing files from disk.

        .. versionadded:: 1.2.5
        """
        return self._get_file_attribute('version') or '1.2'

    def __set_version(self):
        self.root.set_attribute('version', self.VERSION)

    def __set_package_id(self):
        """Set the package identifier string."""
        package_id = getenv('SY_PYTHON_SUPPORT_HASH') or ''
        self._set_file_attribute('package_id', package_id)

    def set_source_id(self, source_id):
        """Set the source identifier string."""
        self._set_file_attribute('source_id', source_id)

    def __set_timestamp(self):
        """Set the time string."""
        timestamp = datetime.now().isoformat()
        self._set_file_attribute('timestamp', timestamp)

    def __set_user_id(self):
        """Set the user identifier string."""
        user_id = getuser()
        try:
            self._set_file_attribute('user_id', user_id)
        except UnicodeDecodeError:
            self._set_file_attribute('user_id', user_id).decode(fs_encoding)

    def is_empty(self):
        return (self.meta.is_empty() and
                self.res.is_empty() and
                self.sys.is_empty())

    def __repr__(self):
        """
        Short unambiguous string representation.
        """
        id_ = hex(id(self))
        empty = "Empty " if self.is_empty() else ""
        return "<{}adaf.File object at {}>".format(empty, id_)

    def __unicode__(self):
        """String representation."""
        systems = [system for system in self.sys.keys()]
        rasters = []
        for system in systems:
            rasters.extend(self.sys[system].values())
        ts = []
        for raster in rasters:
            ts.extend(raster.keys())
        systems_list = u":\n    {}".format(systems) if systems else u""

        lines = [
            u"{!r}:".format(self),
            u"  {meta} meta columns (.meta)".format(
                meta=len(self.meta.keys())),
            u"  {res} result columns (.res)".format(
                res=len(self.res.keys())),
            u"  {} time series in {} raster{} (.ts or .sys)".format(
                len(ts), len(rasters), plural(len(rasters))),
            u"  {} measurement system{} (.sys){}".format(
                len(systems), plural(len(systems)), systems_list)]

        lines.extend(sys_warnings(self.sys))
        return u"\n".join(lines)

    def __copy__(self):
        raise NotImplementedError

    def __deepcopy__(self, memo=None):
        obj = super(File, self).__deepcopy__()
        obj.meta = Group(obj._data.meta, name="meta")
        obj.res = Group(obj._data.res, name="res")
        obj.root = Group(obj._data.root, name="root")
        obj.sys = SystemGroupContainer(obj._data.sys, name='sys')
        obj.ts = TimeseriesGroup(obj.sys)
        return obj


@inherit_doc
class FileList(filebase.FileListBase):
    """
    The :class:`FileList` class is used when working with lists of ADAFs.

    The main interfaces in :class:`FileList` are indexing or iterating for
    reading (see the :meth:`__getitem__` method) and the :meth:`append` method
    for writing.

    Any port with the *ADAFs* type will produce an object of this kind. If it
    is an input port the :class:`FileList` will be in read-through mode,
    disallowing any write actions and disabling list level caching. If it is an
    output port the :class:`FileList` will be in write-through mode,
    disallowing any read actions and making methods like :meth:`append` trigger
    an imidiate writeback of that element.
    """
    sytype = '[adaf]'
    scheme = 'hdf5'


class Attributes(object):
    """Convenience class for using attributes."""

    def __init__(self, attributes):
        self.__attributes = attributes

    def get(self, key):
        """Return value of attribute named by ``key``. Raise ``KeyError`` if
        attribute hasn't been set."""
        return self[key]

    def get_or_empty(self, key):
        """Return value of attribute ``key`` or return an empty
        string if that attribute does not exist."""
        return self.__attributes.get_or_empty(key)

    def set(self, key, value):
        """Set value of attribute ``key``."""
        self[key] = value

    def keys(self):
        """Return the current attribute names."""
        return self.__attributes.keys()

    def values(self):
        """Return the current attribute values."""
        return [self.get(key) for key in self.__attributes.keys()]

    def update(self, other):
        """
        Add all keys and values from other.
        If some of the attributes already exist they will be updated with the
        new valeus.

        .. versionadded:: 1.3.1
        """
        for k, v in other.items():
            self.set(k, v)

    def items(self):
        """Return the current attribute names and values."""
        return zip(self.keys(), self.values())

    def __contains__(self, key):
        """Return True if attribute ``key`` has been set."""
        return key in self.keys()

    def __getitem__(self, key):
        """Return value of attribute named by ``key``."""
        return self.__attributes.get(key)

    def __setitem__(self, key, value):
        """Set value of attribute named by ``key``."""
        self.__attributes.set(key, value)
        return value


class MAttributes(object):
    """Convenience class for using attributes stored in a sytable column."""

    def __init__(self, node, name):
        self.__node = node
        self.__name = name

    def get(self, key):
        """Return value of attribute ``key``."""
        try:
            return self.__node.get_attribute(key)
        except KeyError:
            if key == 'unit':
                return 'unknown'
            elif key == 'description':
                return ''
            raise

    def get_or_empty(self, key):
        """Return value of attribute ``key`` or return an empty
        string if key does not exist."""
        try:
            return self.get(key)
        except KeyError:
            return ''

    def set(self, key, value):
        """Set value of attribute ``key``."""
        self.__node.set_attribute(key, value)

    def keys(self):
        """Return the current attribute keys."""
        return self.__node.get().keys()


class SAttributes(object):
    """Convenience class for using attributes stored in a sytable column."""

    def __init__(self, node):
        self.__node = node

    def get(self, key):
        """Return value of attribute named by key."""
        return self.__node.get_column(key).tolist()[0]

    def get_or_empty(self, key):
        """Return value of attribute named by key or return the empty
        string if key does not exist."""
        try:
            return self.__node.get_column(key).tolist()[0]
        except KeyError:
            return ''

    def set(self, key, value):
        """Set value of attribute named by key."""
        self.__node.set_column(key, np.array([value]))

    def keys(self):
        """Return the current attribute keys."""
        return self.__node.columns()


class TAttributes(object):
    """Convenience class for using attributes stored in a sytable itself."""
    def __init__(self, node):
        self.__node = node

    def get(self, key):
        """Return value of attribute named by key."""
        value = self.__node.get_table_attributes()[key]
        if key == 'reference_time' and isinstance(value, basestring):
            value = isoformat_string_to_datetime(value)
        return value

    def get_or_empty(self, key):
        """Return value of attribute named by key or return the empty
        string if key does not exist."""
        try:
            return self.get(key)
        except KeyError:
            return ''

    def set(self, key, value):
        """Set value of attribute named by key."""
        if key == 'reference_time' and isinstance(value, datetime):
            value = datetime_to_isoformat_string(value)

        attributes = self.__node.get_table_attributes()
        attributes[key] = value
        self.__node.set_table_attributes(attributes)

    def keys(self):
        """Return the current attribute keys."""
        return self.__node.get_table_attributes().keys()


class Group(filebase.PPrintUnicode):
    """
    Class representing a group of scalars. Used for ``meta`` and ``res``.
    Supports dictionary-like ``__getitem__`` interface for data retrieval. To
    write a column use :meth:`create_column`.
    """
    def __init__(self, data, name=None):
        self.__data = data
        self.name = name

    def keys(self):
        """Return the current group keys."""
        return self.__data.columns()

    def values(self):
        """Return the current group values."""
        return [self[key] for key in self.keys()]

    def items(self):
        """Return the current group items."""
        return zip(self.keys(), self.values())

    def number_of_rows(self):
        """
        Return the number of rows in the Group.

        .. versionadded:: 1.2.6
        """
        return self.__data.number_of_rows()

    def to_table(self):
        """Export table containing the data."""
        result = ttable.File(data=self.__data)
        result.set_name(self.name)
        return result

    def get_attributes(self):
        """Return a dictionary of all attributes on this group."""
        return self.__data.get_table_attributes()

    def set_attribute(self, key, value):
        """Add an attribute to this :class:`Group`.
        If the attribute already exists it will be updated."""
        attr = self.__data.get_table_attributes()
        attr[key] = value
        self.__data.set_table_attributes(attr)

    def from_table(self, table):
        """
        Set the content to that of table.
        This operation replaces the columns of the group with the content of
        the table.
        """
        self.__data.source(table._data)

    def create_column(self, name, data, attributes=None):
        """
        Create and add a new, named, data column to the group.
        Return created column.
        """
        self.__data.set_column(name, data)
        column_attrs = self.__data.get_column_attributes(name)
        if attributes:
            column_attrs.set(attributes)
        return Column(column_attrs, self.__data, name)

    def delete_column(self, name):
        """Delete named data column from the group."""
        del self.__data[name]

    def rename_column(self, old_name, new_name):
        """Rename the named data column."""
        self.__data.set_column(new_name, self.__data.get_column(old_name))
        old_attrs = self.__data.get_column_attributes(old_name)
        new_attrs = self.__data.get_column_attributes(new_name)
        new_attrs.set(old_attrs.get())

    def is_empty(self):
        return self.__data.is_empty()

    def hjoin(self, other_group):
        """HJoin Group with other Group."""
        sybase.hjoin(self.__data, other_group.__data)

    def vjoin(self, other_groups, input_index, output_index, fill,
              minimum_increment):
        """VJoin Group with other Group."""
        input_list = sylist(types.from_string('[sytable]'))
        for other_group in other_groups:
            input_list.append(other_group.__data)
        sybase.vjoin(self.__data, input_list, input_index, output_index, fill,
                     minimum_increment)

    def __contains__(self, key):
        """Return True if key exists in this group or False otherwise."""
        return self.__data.has_column(key)

    def __delitem__(self, key):
        """Delete named data column."""
        del self.__data[key]

    def __getitem__(self, key):
        """Return named data column."""
        return Column(
            self.__data.get_column_attributes(key), self.__data, key)

    def __setitem__(self, key, column):
        self.__data.update_column(key, column._Column__data, column.name())
        return self[key]

    def __repr__(self):
        id_ = hex(id(self))
        return "<{} object {!r} at {}>:".format(
            self.__class__.__name__, self.name, id_)

    def __unicode__(self):
        keys = self.keys()
        col_count = len(keys)
        row_count = self.__data.number_of_rows()
        lines = [
            u"{!r}:".format(self),
            u"  Name: {}".format(self.name),
            u"  {} column{}: {}".format(col_count, plural(col_count), keys),
            u"  {} row{}".format(row_count, plural(row_count))]
        return u"\n".join(lines)


class NamedGroupContainer(filebase.PPrintUnicode):
    """Container class for group elements."""

    def __init__(self, record, name=None):
        self._record = record
        self._data = record.data
        self._cache = None
        self.attr = SAttributes(record.attr)
        self.name = name

    def keys(self):
        """Return the current group keys."""
        return [key for key, value in self.items()]

    def items(self):
        result = []
        keys = sorted(self._cache.keys(), key=lambda x: combined_key(x))
        for key in keys:
            result.append((key, self[key]))
        return result

    def values(self):
        return [value for key, value in self.items()]

    def create(self, key):
        """Create and add a new group. Return created group."""
        raise NotImplementedError

    def copy(self, key, other):
        """Copy existing element from other."""
        raise NotImplementedError

    def delete(self, key):
        """Delete keyed group from the container."""
        del self[key]

    def is_empty(self):
        return not bool(self.keys())

    def __contains__(self, key):
        return key in self._cache

    def __delitem__(self, key):
        """Delete keyed group."""
        del self._data[key]
        del self._cache[key]

    def __getitem__(self, key):
        """Return keyed group."""
        raise NotImplementedError

    def __setitem__(self, key, value):
        """Set keyed group."""
        raise NotImplementedError


class SystemGroupContainer(NamedGroupContainer):
    """Container class for SystemGroup elements."""

    def __init__(self, data, name=None):
        self.name = name
        self._data = data
        self._cache = OrderedDict.fromkeys(data.keys())

    def create(self, key):
        """Create and add a new SystemGroup."""
        if key in self:
            raise ValueError('A system named {0} already exists.'.format(key))
        value = SystemGroup(
            _create_named_dict_child(self._data, key), key)
        self._cache[key] = value
        return value

    def copy(self, key, other, new_key=None):
        """Copy existing SystemGroup from other."""
        if new_key is None:
            new_key = key
        value = other._data[key].__deepcopy__()
        self._data[new_key] = value
        self._cache[new_key] = SystemGroup(value, new_key)

    def hjoin(self, other):
        for key in other.keys():
            self.copy(key, other)

    def __getitem__(self, key):
        """Returns keyed :class:`SystemGroup`"""
        group = self._cache[key]
        if group is None:
            group = SystemGroup(self._data[key], key)
            self._cache[key] = group
        return group

    def __setitem__(self, key, value):
        """Set keyed :class:`SystemGroup`"""
        new = typefactory.from_type(value._record.container_type)
        new.data = value._record.data
        new.attr = value._record.attr[:]
        SAttributes(new.attr).set('name', key)
        self._data[key] = new
        result = SystemGroup(new, key)
        self._cache[key] = result
        return result

    def __repr__(self):
        id_ = hex(id(self))
        count = len(self._cache)
        if not count:
            return "<Empty {} object at {}>".format(
                self.__class__.__name__, id_)
        return "<{} object at {}>:".format(self.__class__.__name__, id_)

    def __unicode__(self):
        systems = [system for system in self._cache.keys()]
        rasters = []
        for system in systems:
            rasters.extend(self[system].values())
        ts = []
        for raster in rasters:
            ts.extend(raster.keys())
        systems_list = u":\n    {}".format(systems) if systems else u""

        lines = [
            u"{!r}:".format(self),
            u"  {} time series in {} raster{}".format(
                len(ts), len(rasters), plural(len(rasters))),
            u"  {} measurement system{}{}".format(
                len(systems), plural(len(systems)), systems_list)]

        lines.extend(sys_warnings(self))
        return u"\n".join(lines)


class SystemGroup(NamedGroupContainer):
    """Container class for :class:`RasterN` elements."""
    def __init__(self, record, name=None):
        super(SystemGroup, self).__init__(record, name)
        self._cache = OrderedDict.fromkeys(self._data.keys())

    def create(self, key):
        """Create and add a new :class:`RasterN`."""
        if key in self:
            raise ValueError('A raster named {0} already exists.'.format(key))
        value = RasterN(
            _create_named_dict_child(self._data, key), self.name, key)
        self._cache[key] = value
        return value

    def copy(self, key, other, new_key=None):
        """Copy existing :class:`RasterN` from other."""
        if new_key is None:
            new_key = key
        value = other._data[key].__deepcopy__()
        self._data[new_key] = value
        self._cache[new_key] = RasterN(value, self.name, new_key)

    def __getitem__(self, key):
        """Return keyed :class:`RasterN`"""
        group = self._cache[key]
        if group is None:
            group = RasterN(self._data[key], self.name, key)
            self._cache[key] = group
        return group

    def __setitem__(self, key, value):
        """Set keyed :class:`RasterN`"""
        new = value._RasterN__data
        self._data[key] = new
        result = RasterN(new, key)
        self._cache[key] = result
        return result

    def __repr__(self):
        id_ = hex(id(self))
        count = len(self._cache)
        empty = "Empty " if not count else ""
        return "<{}{} object {!r} at {}>".format(
            empty, self.__class__.__name__, self.name, id_)

    def __unicode__(self):
        count = len(self._cache)
        s = plural(count)
        keys = self._cache.keys()
        lines = [u"{!r}:".format(self)]
        if count:
            lines.append(u"  {} raster{}: {}".format(count, s, keys))
        lines.extend(sys_warnings({None: self}))
        return u"\n".join(lines)


class RasterN(filebase.PPrintUnicode):
    """
    Represents a raster with a single time basis and any number of time series
    columns.
    """
    BASIS_NAME = '!ADAF_Basis!'

    def __init__(self, record, system, name):
        self.__record = record
        self.__data = record.data
        self.__cache = OrderedDict.fromkeys(
            (key for key in self.__data.columns() if key != self.BASIS_NAME))
        self.__basis = None
        self.system = system
        self.name = name

    def __attr_guard(self, arguments):
        for key in ['unit', 'description']:
            value = arguments.get(key, '')
            if not isinstance(value, basestring):
                raise ValueError(
                    u'{} attribute: {} must be a string'.format(
                        key, repr(value)))

    @property
    def attr(self):
        """Raster level attributes."""
        return Attributes(TAttributes(self.__data))

    def keys(self):
        """Return a list of names of the timeseries."""
        return [key for key, value in self.items()]

    def items(self):
        """
        Return a list of tuples, each with the name of a timeseries and the
        corresponding :class:`Timeseries` object.
        """
        uncached = {key: Timeseries(self, self.__data, key)
                    for key, value in self.__cache.items() if value is None}
        self.__cache.update(uncached)
        return self.__cache.items()

    def number_of_rows(self):
        """
        Return the number of rows (length of a time basis/time series) in the
        raster.
        """
        return self.__data.number_of_rows()

    def number_of_columns(self):
        """Return the number of signals including the basis."""
        return self.__data.number_of_columns()

    def values(self):
        """Return a list of all signal items."""
        return [value for key, value in self.items()]

    def basis_column(self):
        """
        Return the time basis for this raster. The returned object is of type
        :class:`Column`.
        """
        if self.__basis is None:
            self.__basis = Column(
                self.__data.get_column_attributes(self.BASIS_NAME),
                self.__data,
                self.BASIS_NAME)
        return self.__basis

    def create_basis(self, data, attributes=None, **kwargs):
        """
        Create and add a basis. The contents of the dictionary ``attributes``
        are added as attributes on the signal.

        .. versionchanged:: 1.2.1
           Added the ``attributes`` parameter. Using kwargs to set attributes
           is now considered obsolete and will result in a warning.
        """
        if kwargs:
            exceptions.sywarn(
                "Avoid using keyword arguments (kwargs), use 'attributes' "
                "instead.")

        if (self.__data.number_of_columns() and
                data.size != self.__data.number_of_rows()):
            raise ValueError(
                "Can't create basis of length {} in raster of length "
                "{}".format(data.size, self.__data.number_of_rows()))

        kwargs = attributes or kwargs or {}
        self.__data.set_column(self.BASIS_NAME, data)
        self.__data.set_name(kwargs.get('name', self.name))
        if kwargs:
            self.__attr_guard(kwargs)
            self.__data.get_column_attributes(self.BASIS_NAME).set(kwargs)
        self.__basis = None

    def create_signal(self, name, data, attributes=None, **kwargs):
        """
        Create and add a new signal. The contents of the dictionary
        ``attributes`` are added as attributes on the signal.

        .. versionchanged:: 1.2.1
           Added the ``attributes`` parameter. Using kwargs to set attributes
           is now considered obsolete and will result in a warning.
        """
        if kwargs:
            exceptions.sywarn(
                "Avoid using keyword arguments (kwargs), use 'attributes' "
                "instead.")

        if (self.__data.number_of_columns() and
                data.size != self.__data.number_of_rows()):
            raise ValueError(
                "Can't create signal of length {} in raster of length "
                "{}".format(data.size, self.__data.number_of_rows()))

        kwargs = attributes or kwargs or {}
        self.__attr_guard(kwargs)
        self.__data.set_column(name, data)
        self.__data.get_column_attributes(name).set(kwargs)
        self.__cache[name] = None

    def delete_signal(self, name):
        """Delete named signal."""
        del self.__data[name]
        self.__cache.pop(name, None)

    def to_table(self, basis_name=None):
        """Export all timeseries as a Table.

        When basis_name is given, the basis will be included in the table and
        given the basis_name, otherwise it will not be included in the table.
        """
        dst_table = ttable.File()
        src_table = ttable.File(data=self.__data)
        if basis_name is not None:
                dst_table.update_column(basis_name,
                                        src_table,
                                        self.BASIS_NAME)
        for column_name in src_table.column_names():
            if column_name != self.BASIS_NAME and column_name != basis_name:
                dst_table.update_column(column_name,
                                        src_table,
                                        column_name)
        dst_table.set_name(self.name)
        dst_table.set_table_attributes(src_table.get_table_attributes())
        return dst_table

    def from_table(self, table, basis_name=None, use_basis_name=True):
        """
        Set the content to that of table.

        This operation replaces the signals of the raster with the content of
        the table.

        When basis_name is used, that column will be used as basis, otherwise
        it will not be defined after this operation and needs to be
        set using create_basis.
        """
        dst_table = ttable.File()

        # Fill cache with all columns beside the basis.
        self.__cache = OrderedDict.fromkeys(table.column_names())
        self.__cache.pop(self.BASIS_NAME, None)
        self.__cache.pop(basis_name, None)

        # Fill the table with all columns beside the basis.
        for column_name in self.__cache.keys():
            dst_table.update_column(column_name, table, column_name)

        if basis_name is not None:
            # Let basis_column determine the name.
            if use_basis_name:
                self.__data.set_name(basis_name)

            # Fill the table with basis column.
            dst_table.update_column(self.BASIS_NAME, table, basis_name)

        dst_table.set_name(table.get_name())
        dst_table.set_table_attributes(table.get_table_attributes())

        self.__record.data = dst_table._data
        self.__data = dst_table._data
        self.__basis = None

    def vjoin(self, other_groups, input_index, output_index, fill,
              minimum_increment):
        """VJoin Group with other Group."""
        input_list = sylist(types.from_string('[sytable]'))
        for other_group in other_groups:
            input_list.append(other_group.__data)
        sybase.vjoin(self.__data, input_list, input_index, output_index, fill,
                     minimum_increment)

    def __contains__(self, key):
        """Return True if column ``key`` is in this raster."""
        return key in self.__cache

    def __getitem__(self, key):
        """Return named raster Column."""
        if key == self.BASIS_NAME:
            raise KeyError('Column cannot be named {0}'.format(key))
        else:
            if key in self:
                if self.__cache[key] is None:
                    self.__cache[key] = Timeseries(self, self.__data, key)
            else:
                raise KeyError(u'Missing {0}'.format(key))
        return self.__cache[key]

    def __setitem__(self, key, value):
        """Set named raster Column."""
        if key == self.BASIS_NAME:
            raise KeyError('Column cannot be named {0}'.format(key))
        else:
            self.__data[key] = value._Timeseries__data
            result = Timeseries(self, self.__data, key)
            self.__cache[key] = result
            return result

    def __repr__(self):
        id_ = hex(id(self))
        return "<{} object {!r} at {}>".format(
            self.__class__.__name__, self.name, id_)

    def __unicode__(self):
        keys = self.keys()
        col_count = len(keys)
        row_count = self.number_of_rows()
        try:
            basis = self.basis_column()
        except KeyError:
            basis = None
        lines = [
            u"{!r}".format(self),
            u"  Name: {}".format(self.name),
            u"  {} column{}: {}".format(col_count, plural(col_count), keys),
            u"  {} row{}".format(row_count, plural(row_count))]
        if not basis:
            lines.append(u"Warning: This raster has no basis")
        return u"\n".join(lines)


class Column(filebase.PPrintUnicode):
    """
    Class representing a named column with values and attributes.
    Get attributes with ``attr`` member.
    """

    def __init__(self, attributes, data, name):
        self.__attrs = attributes
        self.__data = data
        self.__name = name
        if not data.has_column(name):
            raise KeyError(u'Missing {0}'.format(name))
        self.attr = Attributes(MAttributes(attributes, name))

    def name(self):
        """Return the column name."""
        return self.__name

    def value(self):
        """Return the column value."""
        return self.__data.get_column(self.name())

    def size(self):
        """Return the size of the column."""
        return self.__data.number_of_rows()

    def __repr__(self):
        id_ = hex(id(self))
        return "<{} object {!r} at {}>".format(
            self.__class__.__name__, self.name(), id_)

    def __unicode__(self):
        dtype = self.value().dtype
        lines = [u"{!r}:".format(self),
                 u"  Name: {}".format(self.name()),
                 u"  Type: {} ({})".format(get_pretty_type(dtype), dtype),
                 u"  Length: {}".format(self.size())]
        if 'description' in self.attr:
            lines.append(u"  Description: {}".format(self.attr['description']))
        if 'unit' in self.attr:
            lines.append(u"  Unit: {}".format(self.attr['unit']))
        lines.append(u"  Values: {}".format(short_narray(self.value())))
        return u"\n".join(lines)


class Timeseries(filebase.PPrintUnicode):
    """
    Class representing a time series. The values in the time series can be
    accessed as a numpy array via the member ``y``. The time series is also
    connected to a time basis whose values can be accessed as a numpy array
    via the property ``t``.

    The time series can also have any number of attributes. The methods
    :meth:`unit` and :meth:`description` retrieve those two attributes. To get
    all attributes use the method :meth:`get_attributes`.
    """

    def __init__(self, node, data, name):
        self.__node = node
        self.__data = data
        self.__attrs = data.get_column_attributes(name)
        self.name = name

    @property
    def y(self):
        """Time series values as a numpy array."""
        return self.signal().value()

    @property
    def t(self):
        """Time basis values as a numpy array."""
        return self.basis().value()

    def unit(self):
        """Return the unit attribute or an empty string if it is not set."""
        try:
            return self.__attrs.get_attribute('unit')
        except KeyError:
            return ''

    def get_attributes(self):
        """Return all attributes (including unit and description)."""
        return self.__attrs.get()

    def description(self):
        """
        Return the description attribute or an empty string if it is not set.
        """
        try:
            return self.__attrs.get_attribute('description')
        except KeyError:
            return ''

    def signal_name(self):
        """Return the name of the time series data signal."""
        return self.name

    def system_name(self):
        """Return the name of the associated system."""
        return self.__node.system

    def raster_name(self):
        """Return the name of the associated raster."""
        return self.__node.name

    def basis(self):
        """Return the time series data basis as a :class:`Column`."""
        return self.__node.basis_column()

    def signal(self):
        """Return the time series data signal as a :class:`Column`."""
        return Column(self.__attrs, self.__data, self.name)

    def __repr__(self):
        id_ = hex(id(self))
        return "<{} object {!r} at {}>".format(
            self.__class__.__name__, self.name, id_)

    def __unicode__(self):
        warn_lines = []
        lines = [u"{!r}:".format(self),
                 u"  Name: {}".format(self.name),
                 u"  Type: {} ({})".format(
                     get_pretty_type(self.y.dtype), self.y.dtype),
                 u"  Raster: {}/{}".format(
                     self.system_name(), self.raster_name()),
                 u"  Length: {}".format(len(self.y))]
        if self.description():
            lines.append(u"  Description: {}".format(self.description()))
        if self.unit():
            lines.append(u"  Unit: {}".format(self.unit()))
        try:
            self.t
        except KeyError:
            warn_lines.append(
                u"Warning: Timeseries comes from a raster with no basis.")
        else:
            lines.append(u"  t: {}".format(short_narray(self.t)))
        lines.append(u"  y: {}".format(short_narray(self.y)))
        return u"\n".join(lines + warn_lines)


class TimeseriesGroup(filebase.PPrintUnicode):
    """Container class for :class:`Timeseries` elements."""
    def __init__(self, node):
        self.node = node

    def keys(self):
        """Return the current group keys."""
        return [key for system in self.node.values()
                for raster in system.values()
                for key in raster.keys()]

    def items(self):
        """Return a list of all signal items."""
        return [item for system in self.node.values()
                for raster in system.values()
                for item in raster.items()]

    def values(self):
        """Return a list of all signal items."""
        return [value for system in self.node.values()
                for raster in system.values()
                for value in raster.values()]

    def hjoin(self, other):
        """
        HJoin :class:`TimeseriesGroup` with other :class`TimeseriesGroup`.
        """
        sybase.hjoin(self.node, other.node)

    def __contains__(self, key):
        return key in self.keys()

    def __getitem__(self, key):
        """
        Return named :class:`Timeseries`. Consider using :meth:`items` because
        multiple calls of this method will be extremely inefficient.

        For multiple lookups, use items() and store the result.
        """
        return dict(self.items())[key]

    def __repr__(self):
        id_ = hex(id(self))
        return "<{} object at {}>".format(self.__class__.__name__, id_)

    def __unicode__(self):
        systems = [system for system in self.node.keys()]
        rasters = []
        for system in systems:
            rasters.extend(self.node[system].values())
        ts = []
        for raster in rasters:
            ts.extend(raster.keys())

        ts_str = u":\n    {}".format(ts) if ts else u""

        lines = [
            u"{!r}:".format(self),
            u"  {} time series (in {} raster{}){}".format(
                len(ts), len(rasters), plural(len(rasters)), ts_str)]

        lines.extend(sys_warnings(self.node))
        return u"\n".join(lines)


def _create_named_dict_child(parent, key):
    """
    Return a named child of a sydict of type {(attr:table, data:type)}
    named childs are encoded with type (attr:table, data:type) and named using
    the attr element name.
    """
    record = typefactory.from_type(parent.content_type)
    SAttributes(record.attr).set('name', key)
    parent[key] = record
    return record
