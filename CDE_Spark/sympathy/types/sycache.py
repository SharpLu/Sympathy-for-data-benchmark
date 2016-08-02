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
import h5py
import numpy as np
import os
import tempfile
import weakref
from sympathy.platform.state import cache_state

compress_threshold = 2048

ENCODING = 'e'
ENCODING_TYPE = 't'


encoded_types = {'datetime64[us]': 'f8',
                 'datetime64[D]': 'f8',
                 'timedelta64[us]': 'f8'}


def encode(array, encoding='utf-8'):
    """
    Encode numpy unicode typed array (array.dtype.kind == 'U') as a numpy
    string array.
    """
    data = array.tolist()
    if isinstance(data, list):
        return np.array([x.encode(encoding) for x in data])
    else:
        return np.array(data.encode(encoding))


def decode(array, encoding='utf-8'):
    """
    Decode string array dataset encoded in utf-8 as a numpy unicode typed array
    (array.dtype.kind == 'U').
    """
    data = array.tolist()
    if isinstance(data, list):
        return np.array([x.decode(encoding) for x in data])
    else:
        return np.array(data.decode(encoding))


def get_cache(maxsize):
    state = cache_state()
    if state.get() is None:
        state.add(NumpyHDF5Cache(maxsize))
    return state.get()


class HDF5Backend(object):
    def __init__(self):
        """
        Create a new HDF5 Backend for stroring data.
        If filename is None then a temporary file will be used.
        """
        state = cache_state()
        session_dir = state.session_dir
        if session_dir is not None:
            fd, self.__filename = tempfile.mkstemp(
                prefix='sycache_{}_'.format(os.getpid()), suffix='.h5',
                dir=session_dir)
            os.close(fd)
            self.__backend = h5py.File(self.__filename, mode='w')
        else:
            self.__backend = h5py.File('unused', driver='core',
                                       backing_store=False, mode='w')
            self.__filename = None
        self.__closed = False

    def close(self):
        """Close the referenced data file."""
        import os
        if not self.closed():
            self.__backend.flush()
            self.__backend.close()
            if self.__filename is not None and os.path.exists(self.__filename):
                os.remove(self.__filename)
        self.__backend = None
        self.__filename = None
        self.__closed = True

    def closed(self):
        """Check if the store is closed."""
        return self.__closed

    def type(self, name):
        name = str(name)
        dataset = self.__backend[name]
        if ENCODING_TYPE in dataset.attrs:
            return np.dtype(dataset.attrs[ENCODING_TYPE])
        else:
            return dataset.dtype

    def read(self, name):
        """Read stored column."""
        name = str(name)

        if self.__closed:
            return None
        column = self.__backend[name]
        if column.shape == (0,):
            # Avoid zero size selection problem in h5py.
            if ENCODING_TYPE in column.attrs:
                return np.array([], dtype=column.attrs[ENCODING_TYPE])
            return np.array([], dtype=column.dtype)
        elif ENCODING in column.attrs:
            # Repack array with unicode type.
            return decode(column[...], column.attrs[ENCODING])
        elif ENCODING_TYPE in column.attrs:
            # Repack type with encoding type.
            return column[...].astype(column.attrs[ENCODING_TYPE])
        else:
            return column[...]

    def write(self, name, column):
        """Write column to store."""
        name = str(name)

        if not self.__closed:
            if name in self.__backend:
                return

            if column.dtype.kind == 'U':
                # Unpack array from record array.
                if column.size > compress_threshold:
                    self.__backend.create_dataset(
                        name,
                        data=encode(column),
                        compression='lzf',
                        shuffle=True)
                else:
                    self.__backend[name] = encode(column)
                self.__backend[name].attrs.create(ENCODING, 'utf-8')
                self.__backend[name].attrs.create(ENCODING_TYPE,
                                                  column.dtype.str)
            else:
                dtype_name = column.dtype.name
                dtype_str = None
                if dtype_name in encoded_types:
                    dtype_str = column.dtype.str
                    column = column.astype(encoded_types[dtype_name])

                if column.nbytes > compress_threshold:
                    self.__backend.create_dataset(
                        name,
                        data=column,
                        compression='lzf',
                        shuffle=True)
                else:
                    self.__backend[name] = column

                if dtype_str is not None:
                    self.__backend[name].attrs.create(ENCODING_TYPE,
                                                      dtype_str)

    def delete(self, name):
        """Delete column from store."""
        name = str(name)

        if self.__closed:
            return
        del self.__backend[name]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class Cache(object):
    def __init__(self, maxsize, backend):
        """
        Create a new Cache for working with data.
        If filename is None then a temporary file will be used.
        """
        self.__size = 0
        self.maxsize = maxsize

        self.__backend = backend
        self.__store = collections.OrderedDict()
        self.__cache = collections.OrderedDict()

    def __store_data(self):
        size = self.__size
        maxsize = self.maxsize

        if size > maxsize:
            while size > maxsize / 2 and len(self.__cache) > 1:
                # We do not store the last element regardless of size.
                # Because, in that case, the cache would serve no purpose.
                # Alternatively, an exception could be raised.
                key, entry = self.__cache.popitem(False)

                data = entry.data()
                if data is not None:
                    # Weak reference is alive.
                    self.__store[key] = entry
                    self.__backend.write(key, data.get())
                    data.set(None)
                size -= entry.size
            self.__size = size

    def delete(self, key):
        if key in self.__cache:
            entry = self.__cache.pop(key)
            data = entry.data()

            if data is not None:
                # Avoid error when doing in the callback delete routine.
                data.set(None)
            self.__size -= entry.size
        elif key in self.__store:
            entry = self.__store.pop(key)
            self.__backend.delete(key)
        else:
            raise KeyError()

    def set(self, key, receipt):
        # Making sure to clean up previous entry.
        try:
            self.delete(key)
        except KeyError:
            pass

        # Create and add new entry for receipt.
        self.__cache[key] = Receipt(weakref.ref(
            receipt.data, receipt_callback(key, self)), receipt.size)
        self.__size += receipt.size
        self.__store_data()
        assert(receipt is not None)
        return receipt

    def get(self, receipt):
        key = hash(receipt.data)

        if key in self.__cache:
            # Moving entry forward in cache.
            entry = self.__cache.pop(key)
            data = entry.data().get()
            self.__cache[key] = entry
        elif key in self.__store:
            # Caching stored element.
            entry = self.__store.pop(key)
            data = self.__backend.read(key)
            entry.data().set(data)
            self.__cache[key] = entry
            self.__size = entry.size
            self.__store_data()
            if entry.data().get() is None:
                raise RuntimeError('Cannnot cache entry.')
        else:
            raise KeyError('Key is not cached or stored.')
        return receipt

    def type(self, key):
        if key in self.__cache:
            column = self.__cache[key]
            return column.data().get().dtype
        elif key in self.__store:
            return self.__backend.type(key)
        else:
            raise KeyError('key {} not available'.format(key))

    def __contains__(self, key):
        return key in self.__cache or key in self.__store

    def close(self):
        self.__cache.clear()
        self.__store.clear()
        self.__backend.close()
        self._backend = None


class Wrapper(object):
    def __init__(self, data):
        self.__data = data

    def get(self):
        return self.__data

    def set(self, data):
        self.__data = data


class Receipt(object):
    def __init__(self, data, size):
        self.data = data
        self.size = size


class NumpyHDF5Cache(object):
    def __init__(self, size):
        self.cache = Cache(size, HDF5Backend())

    def set(self, data):
        wrapper = Wrapper(data)
        receipt = Receipt(wrapper, data.itemsize * data.size)
        return self.cache.set(hash(wrapper), receipt)

    def get(self, receipt):
        internal_receipt = self.cache.get(receipt)
        result = internal_receipt.data.get()
        assert(result is not None)
        return result

    def type(self, receipt):
        result = self.cache.type(hash(receipt.data))
        return result


def receipt_callback(key, owner):
    def inner(ref):
        try:
            # Not allowing exceptions in delete callback.
            owner.delete(key)
        except:
            pass
    return inner
