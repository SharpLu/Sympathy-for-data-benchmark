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
Utility functions needed to read and write tables from/to different
formats.
"""
import locale

from .. datasources.info import (get_fileinfo_from_scheme,
                                 get_scheme_from_file)
from .. types.types import (from_string_alias, from_type_expand,
                            from_string_expand)
from .. types import sylist
from .. types.types import manager as type_manager
from .. types.factory import typefactory
from .. types import types
from . import port as port_util
from contextlib import contextmanager
from .. platform import exceptions


class PPrintUnicode(object):
    """
    Base class for pretty printing in IPython.

    Any subclass will be printed with unicode(obj) instead of the default
    repr(obj) when they are the result of an expression in IPython. This allows
    for higher interactivity when working in IPython.
    """
    pass


def typeutil(typealias):
    def inner(cls):
        declaration = from_string_alias(typealias)
        cls.container_type = declaration
        type_manager.set_typealias_util(declaration.name(), cls)
        return cls
    return inner


def from_file(filename, scheme=None, sytype=None, external=True):
    link = not external

    if scheme is None:
        scheme = get_scheme_from_file(filename)

    fileinfo_ = fileinfo(filename, scheme)

    if sytype is None:
        sytype = fileinfo_.type()

    return port_util.port_generator(
        {'file': filename, 'scheme': scheme,
         'type': sytype}, 'r', link, True)


def to_file(filename, scheme, sytype, external=True):
    link = not external

    return port_util.port_generator(
        {'file': filename, 'scheme': scheme,
         'type': sytype}, 'w', link, True)


def _closegen(gen):
    try:
        # Run next to do the cleanup action.
        gen.next()
    except StopIteration:
        # Expecting StopIteration.
        pass
    finally:
        # Making sure to close the generator.
        gen.close()


@contextmanager
def from_type(sytype):
    yield typefactory.from_type(sytype)


def empty_from_type(sytype):
    return typefactory.from_type(sytype)


def fileinfo(filename, scheme=None):
    if scheme is None:
        scheme = get_scheme_from_file(filename)

    return get_fileinfo_from_scheme(scheme)(filename)


def is_type(sytype, filename, scheme='hdf5'):
    info = fileinfo(filename, scheme)
    try:
        return fileinfo.type() == str(sytype)
    except (KeyError, AttributeError, TypeError):
        pass
    try:
        return (str(from_string_expand(info.datatype()))
                == str(from_type_expand(sytype)))
    except TypeError:
        return False


class FileManager(PPrintUnicode):
    """FileManager handles data contexts for File and FileList."""
    container_type = None
    ELEMENT = None

    def __init__(self, gen, data, filename, mode, scheme, import_links=False):
        """
        Initialize FileManager
        FileManager handles:
        Generator input,
        Shared input data,
        Filename input data.
        """
        if filename is not None:
            if mode not in ['r', 'w']:
                raise AssertionError(
                    "Supported values for mode are: 'r' and 'w', but '{}'"
                    " was given.".format(mode))
        self._data = None

        if gen is not None:
            self.__gen = gen.gen
        elif data is not None:
            self.__gen = self.__shared_generator(data).gen
        elif filename is not None:
            if mode == 'w' and import_links:
                exceptions.sywarn(
                    "Argument: 'import_links' must be False for mode 'w'.")
                import_links = False

            self.__gen = open_file(
                filename=filename, mode=mode, external=not import_links,
                sytype=self.container_type, scheme='hdf5')
            self._data = self.__gen.next()._data
        else:
            self.__gen = self.__shared_generator(
                typefactory.from_type(self.container_type)._data).gen

        if self._data is None:
            self._data = self.__gen.next()
            if isinstance(self._data, type(self)):
                # Avoiding double wrapping with non-managed nodes.
                self._data = self._data._data

    def _copy_base(self):
        cls = type(self)
        obj = cls.__new__(cls)
        obj._data = self._data
        obj.__gen = self.__gen
        return obj

    def __copy__(self):
        return self._copy_base()

    def __deepcopy__(self, memo=None):
        obj = self._copy_base()
        obj._data = self._data.__deepcopy__()
        return obj

    def writeback(self):
        self._data.writeback()

    def _writeback(self, datasource, link=None):
        return self._data._writeback(datasource, link)

    @classmethod
    def is_type(cls, filename, scheme='hdf5'):
        return is_type(cls.container_type, filename, scheme)

    @staticmethod
    def is_valid():
        return True

    def close(self):
        """Close the referenced data file."""
        _closegen(self.__gen)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def __shared_generator(self, data):
        yield data


class FileBase(FileManager):
    """File represents the top level of a table"""
    container_type = None

    def __init__(self, gen=None, data=None, filename=None, mode='r',
                 scheme='hdf5', source=None, managed=False,
                 import_links=False):
        if filename is not None and mode is None:
            mode = 'r'
        super(FileBase, self).__init__(gen, data, filename, mode, scheme,
                                       import_links=import_links)
        self._extra_init(gen, data, filename, mode, scheme, source)

    def _extra_init(self, gen, data, filename, mode, scheme, source):
        if source:
            self._data.update(source._data)

    def source(self, other):
        """
        Update self with a deepcopy of the data from other, without keeping the
        old state.

        self and other must be of the exact same type.
        """
        raise NotImplementedError


class FileListBase(sylist, PPrintUnicode):
    """FileList represents a list of Files."""
    sytype = None  # str.
    scheme = None  # str.

    def __new__(cls, filename=None, mode='r', import_links=False):

        if mode == 'w' and import_links:
            exceptions.sywarn(
                "Argument: 'import_links' must be False for mode 'w'.")
            import_links = False

        gen = open_file(filename=filename, mode=mode,
                        external=not import_links,
                        sytype=types.from_string(cls.sytype),
                        scheme=cls.scheme)
        obj = gen.next()
        obj.__class__ = cls
        obj._gen = gen
        return obj

    def __init__(self, filename=None, mode='r'):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        _closegen(self._gen)

    def is_type(self, filename, scheme=None):
        return is_type(types.from_string(self.sytype), filename, scheme)

    def set_read_through(self):
        exceptions.sywarn('set_read_through is not implemented.')

    def set_write_through(self):
        exceptions.sywarn('set_write_through is not implemented.')

    def is_read_through(self):
        return False

    def is_write_through(self):
        return False

    def __str__(self):
        return unicode(self).encode(locale.getpreferredencoding())

    def __unicode__(self):
        repr_line = repr(self)
        elements_str = u"  {} element{}".format(
            len(self), u"s" if len(self) != 1 else u"")
        return repr_line + u":\n" + elements_str

    def __copy__(self):
        obj = super(FileListBase, self).__copy__()
        obj._gen = self._gen
        return obj

    def __deepcopy__(self, memo=None):
        obj = super(FileListBase, self).__deepcopy__()
        obj._gen = self._gen
        return obj

    def __repr__(self):
        mode = 'Buffered '
        id_ = hex(id(self))
        return "<{}FileList object at {}>".format(mode, id_)


def open_file(filename=None, mode='r', external=True, sytype=None,
              scheme='hdf5'):
    gen = None
    assert mode in 'rw', "Mode should be 'r' or 'w'"

    if filename is not None:
        if mode == 'r':
            gen = from_file(filename, external=external, sytype=sytype).gen
        elif mode == 'w':
            assert sytype is not None, "Mode 'w' requires sytype"
            assert scheme is not None, "Mode 'w' requires scheme"
            gen = to_file(filename, scheme, sytype, external=external).gen

    else:
        gen = from_type(sytype).gen
    return gen
