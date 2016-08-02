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
"""Text Data source module."""
import numpy as np

import dsgroup


class Hdf5Text(dsgroup.Hdf5Group):
    """Abstraction of an HDF5-text."""
    def __init__(self, factory, group=None, datapointer=None, can_write=False,
                 can_link=False):
        super(Hdf5Text, self).__init__(
            factory, group, datapointer, can_write, can_link)

    def read(self):
        """Return stored text, or '' if nothing is stored."""
        try:
            return self.group['text'][...].tolist()[0].decode('utf8')
        except KeyError:
            return ''

    def write(self, text):
        """
        Stores text in the hdf5 file, at path,
        with data from the given text
        """
        self.group.create_dataset('text', data=np.array([text.encode('utf8')]))

    def transferable(self, other):
        return False
        # return (isinstance(self, Hdf5Text) and
        #         self.can_link and other.can_link)

    def transfer(self, name, other, other_name):
        return self.group.create_dataset('text', other.read('text'))
        # h5py.ExternalLink(
        #     dataset.file.filename, dataset.name)

        # dataset = other.group['text']
        # self.group['text'] = h5py.ExternalLink(
        #     dataset.file.filename, dataset.name)
