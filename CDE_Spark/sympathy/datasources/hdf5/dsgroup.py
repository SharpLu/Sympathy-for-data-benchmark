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
"""HDF5 group."""
import h5py
import json
import math
from collections import OrderedDict
from sympathy.platform.state import hdf5_state


UTF8 = 'utf-8'
REPLACE_SLASH = chr(0x01)
USERBLOCK_MIN_SIZE = 512
VERSION = 'Version'
VERSION_NUMBER = '1.0'
TYPE = 'Type'
TYPEALIAS = 'TypeAlias'
IDENTIFIER = 'SFD HDF5'


def read_header(filepath):
    """
    Read the header from hdf5 file and return an ordered dict with its content.
    """
    with open(filepath, 'rb') as hdf5:
        identifier = hdf5.read(len(IDENTIFIER))
        line = hdf5.readline()
        assert(identifier == IDENTIFIER)
        header_data = json.loads(
            line, object_pairs_hook=OrderedDict)
        return header_data


def write_header(filepath, header_data):
    """
    Write header_data dictionary to the file at filepath.
    The file must have sufficient space in its userblock.
    """
    with open(filepath, 'r+b') as hdf5:
        hdf5.write(IDENTIFIER)
        hdf5.write(json.dumps(header_data) + '\n')


def _header_data(datatype, type):
    """Return dictionary of header data with data type included."""
    return OrderedDict([(VERSION, VERSION_NUMBER), (TYPE, datatype),
                        (TYPEALIAS, type)])


def _header_data_size(datatype, type):
    """Return length of header data with data type included."""
    length = len(json.dumps(_header_data(datatype, type)))
    return max(int(math.ceil(math.log(length + 2, 2))), USERBLOCK_MIN_SIZE)


def replace_slash(string):
    """
    Replace special '/' character with very rare unicode character 0xFFFF.
    """
    return string.replace('/', REPLACE_SLASH)


def restore_slash(string):
    """
    Restore special '/' character replaced with very rare unicode character
    0xFFFF.
    """
    return string.replace(REPLACE_SLASH, '/')


def create_path(h5file, path):
    """Create path in file returning the group at h5file[path]."""
    splitpath = [split for split in path.split("/") if split != '']
    curr_group = h5file
    for component in splitpath:
        try:
            next_group = curr_group[component]
        except KeyError:
            next_group = curr_group.create_group(component)
        curr_group = next_group
    return h5file[path]


class Hdf5Group(object):
    """Abstraction of an HDF5-group."""
    def __init__(self, factory, group, datapointer, can_write, can_link):
        self.factory = factory
        self.group = group
        if group:
            self.can_link = can_link
            self.can_write = can_write
            self.datatype = None
            self.type = None
            self.filepath = None
            self.mode = None
            self.path = None
            self.util = None
        else:
            util = datapointer.util()
            self.mode = util.mode()
            self.can_link = util.can_link()
            self.can_write = can_write or self.mode in ['r+', 'w']
            self.datatype = util.datatype()
            self.type = util.abstype()
            self.filepath = util.file_path()
            self.path = util.path()
            self.util = util

            if self.mode == 'r':
                try:
                    h5file = h5py.File(self.filepath, self.mode)
                except ValueError:
                    raise IOError(
                        'Could not open assumed hdf5-file : "{}"'.format(
                            self.filepath))
                hdf5_state().filestate[self.filepath] = h5file
                self.group = h5file[self.path]
            elif self.mode == 'w':
                # Create new hdf5 file with userblock set.
                header_data_size = _header_data_size(
                    util.datatype(), util.abstype())
                h5file = h5py.File(
                    self.filepath, self.mode, userblock_size=header_data_size)
                hdf5_state().filestate[self.filepath] = h5file

                self.group = create_path(h5file, self.path)

    def transferable(self, other):
        """
        Returns True if the content from datasource can be linked directly,
        and False otherwise.
        """
        return (self.can_link and other.can_link and
                isinstance(other, Hdf5Group))

    def transfer(self, name, other, other_name):
        """
        Performs linking if possible, this is only allowed if transferrable()
        returns True.
        """
        pass

    def link(self):
        return h5py.ExternalLink(
            self.group.file.filename.encode(UTF8),
            self.group.name.encode(UTF8))

    def shares_origin(self, other_datasource):
        """
        Checks if two datasources originate from the same resource.
        """
        try:
            return (
                self.group.file.filename ==
                other_datasource.group.file.filename and
                self.group.name == other_datasource.group.name)
        except:
            return False

    def close(self):
        """Close the hdf5 file using the group member."""
        # If open fails, avoid causing argument exception on close.
        if self.group:
            try:
                hdf5_state().close(self.filepath)
            except:
                self.group.file.flush()
                self.group.file.close()
            if self.mode == 'w':
                header_data = _header_data(
                    self.util.datatype(), self.util.abstype())
                write_header(self.filepath, header_data)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
