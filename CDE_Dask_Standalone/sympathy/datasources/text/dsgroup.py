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
"""Text group."""
from collections import OrderedDict
import json
IDENTIFIER = 'SFD TEXT'
VERSION_NUMBER = '1.2'


def read_header(filepath):
    """
    Read the header from text file and return an ordered dict with its content.
    """
    with open(filepath, 'rb') as textfile:
        return _read_header(textfile)


def _read_header(textfile):
    identifier = textfile.read(len(IDENTIFIER))
    line = textfile.readline()
    assert(identifier == IDENTIFIER)
    header_data = json.loads(
        line, object_pairs_hook=OrderedDict)
    return header_data


class TextGroup(object):
    """Abstraction of an Text-group."""
    def __init__(self,
                 factory,
                 create_content,
                 datapointer,
                 group,
                 can_write,
                 container_type,
                 create_path):

        self.factory = factory
        self.group = group
        self.container_type = container_type
        self.create_path = create_path
        self.create_content = create_content

        if group is not None:
            self.can_write = can_write
            self.datapointer = datapointer
            self.util = None
            self.filename = None
            self.mode = None
            self.path = None
            self.datatype = None
            self.type = None
        else:
            self.datapointer = datapointer
            self.util = datapointer.util()
            self.filename = self.util.file_path()
            self.mode = self.util.mode()
            self.path = self.util.path()
            self.can_write = can_write or self.mode in ['r+', 'w']
            self.datatype = self.util.datatype()
            self.type = self.util.abstype()

            with open(self.filename, self.mode) as textfile:
                if self.mode in ['r', 'r+']:
                    _read_header(textfile)
                    self.data = json.load(textfile,
                                          object_pairs_hook=OrderedDict)
                elif self.mode == 'w':
                    self.data = {'root':
                                 self.create_content(self.container_type)}
                self.group = self.create_path(
                    self.data['root'], self.container_type, self.path)

    def transferable(self, other):
        """
        Returns True if the content from datasource can be linked directly,
        and False otherwise.
        """
        return False

    def transfer(self, selfname, other, othername):
        """
        Performs linking if possible, this is only allowed if transferrable()
        returns True.
        """
        pass

    def shares_origin(self, other_datasource):
        """
        Checks if two datasources originate from the same resource.
        """
        return False

    def close(self):
        """Close the text file using the group member."""
        if self.data and self.mode == 'w':
            with open(self.filename, 'w') as textfile:
                textfile.write(IDENTIFIER)
                json.dump(OrderedDict([
                    ('version', VERSION_NUMBER),
                    ('datatype', self.util.datatype()),
                    ('type', self.util.abstype())]), textfile)
                textfile.write('\n')
                json.dump(self.data, textfile)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
