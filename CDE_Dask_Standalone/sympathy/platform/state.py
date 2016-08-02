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
Methods for handling global state.
"""
import h5py
from contextlib import contextmanager


__node_state = None
__cache_state = None
__hdf5_state = None
__cache_hdf5_state = False


def node_state():
    global __node_state
    if __node_state is None:
        __node_state = NodeState()
    return __node_state


def hdf5_state():
    global __hdf5_state
    if __hdf5_state is None:
        __hdf5_state = Hdf5State()
    return __hdf5_state


def cache_state():
    global __cache_state
    if __cache_state is None:
        __cache_state = CacheState()
    return __cache_state


def cache_hdf5_state():
    global __cache_hdf5_state
    __cache_hdf5_state = True


@contextmanager
def state():
    """
    Produce a fresh state to run in.
    The original state is restored when the contextmanager finishes.

    Example:

    >>> with state():
    >>>    pass  # Do something.

    This is required for example when running debug in spyder to make sure
    that the current context is not cleared when the new state is set up.
    Otherwise this would lead to files being closed in a very unexpected
    manner.
    """
    global __node_state
    global __cache_state
    global __hdf5_state
    global __cache_hdf5_state

    old_node_state = __node_state
    old_cache_state = __cache_state
    old_hdf5_state = __hdf5_state
    old_cache_hdf5_state = __cache_hdf5_state

    __node_state = None
    __cache_state = None
    __hdf5_state = None
    __cache_hdf5_state = False

    yield

    __node_state = old_node_state
    __cache_state = old_cache_state
    __hdf5_state = old_hdf5_state
    __cache_hdf5_state = old_cache_hdf5_state


class NodeState(object):
    def __init__(self):
        self.attributes = {}
        self.hdf5 = hdf5_state()
        self.cache = cache_state()

    def create(self, **kwargs):
        self.hdf5.create()
        self.cache.create(**kwargs)
        self.attributes = kwargs

    def set_attributes(self, **kwargs):
        self.attributes = kwargs

    def clear(self):
        self.hdf5.clear()
        self.cache.clear()
        self.attributes = {}

    def cleardata(self):
        self.cache.close()
        self.hdf5.clear()


class CacheState(object):
    def __init__(self):
        self.filestate = None
        self.session_dir = None

    def create(self, **kwargs):
        self.clear()
        self.session_dir = kwargs.get('session_dir', None)

    def clear(self):
        self.close()
        self.session_dir = None
        self.filestate = None

    def add(self, cache):
        self.filestate = cache

    def close(self):
        if self.filestate is not None:
            try:
                self.filestate.cache.close()
            except ValueError:
                # Do not allow exceptions here due to already closed file.
                pass

    def get(self):
        return self.filestate


class Hdf5State(object):
    def __init__(self):
        self.filestate = {}
        self.filenum = {}

    def create(self):
        self.clear()
        self.filestate = {}
        self.filenum = {}

    def clear(self):
        for filename in list(self.filestate):
            self.close(filename)

    def add(self, filename, hdf5_file):
        if filename not in self.filestate:
            self.filestate[filename] = hdf5_file

    def open(self, filename, mode):
        if filename in self.filestate:
            return self.filestate[filename]
        else:
            hdf5_file = h5py.File(filename, mode)
            self.filestate[filename] = hdf5_file
            return hdf5_file

    def close(self, filename):
        hdf5_file = self.filestate.pop(filename)
        try:
            hdf5_file.flush()
            hdf5_file.close()
        except ValueError:
            # Do not allow exceptions here due to already closed file.
            pass

    def get(self, hdf5_file, entry):
        try:
            link = hdf5_file.get(entry, getlink=True)
        except KeyError:
            link = hdf5_file

        if isinstance(link, h5py.ExternalLink):
            link_hdf5_file = self.open(link.filename, 'r')
            return self.get(link_hdf5_file, link.path)
        else:
            return hdf5_file[entry]

    def getlink(self, hdf5_file, entry):
        link = hdf5_file.get(entry, getlink=True)
        if isinstance(link, h5py.ExternalLink):
            link_hdf5_file = self.open(link.filename, 'r')
            return self.get(link_hdf5_file, link.path)
        else:
            dataset = hdf5_file[entry]
            return h5py.ExternalLink(dataset.file.filename.encode('utf8'),
                                     dataset.name.encode('utf8'))
