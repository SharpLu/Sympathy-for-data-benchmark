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
"""HDF5 dict."""
import dsgroup
from sympathy.platform.state import hdf5_state


class Hdf5Dict(dsgroup.Hdf5Group):
    """Abstraction of an HDF5-dict."""
    def __init__(self, factory, group=None, datapointer=None, can_write=False,
                 can_link=False):
        super(Hdf5Dict, self).__init__(factory, group, datapointer, can_write,
                                       can_link)

    def read_with_type(self, key, content_type):
        """Reads element at key and returns it as a datasource."""
        key = dsgroup.replace_slash(key)
        group = hdf5_state().get(self.group, key)
        return self.factory(group, content_type, self.can_write,
                            self.can_link)

    def write_with_type(self, key, value, content_type):
        """Write group at key and returns the group as a datasource."""
        key = dsgroup.replace_slash(key)
        if key in self.group:
            key_group = self.group[key]
        else:
            key_group = self.group.create_group(key)

        return self.factory(
            key_group, content_type, self.can_write, self.can_link)

    def link_with(self, key, value):
        key = dsgroup.replace_slash(key)

        if key in self.group:
            assert(False)
        else:
            self.group[key] = value.link()

    def items(self, content_type):
        return [
            (dsgroup.restore_slash(key),
             self.factory(value, content_type, self.can_write, self.can_link))
            for key, value in self.group.iteritems()]

    def contains(self, key):
        return dsgroup.replace_slash(key) in self.group

    def keys(self):
        """Return the keys."""
        return [dsgroup.restore_slash(key) for key in self.group.keys()]

    def size(self):
        """Return the dict size."""
        return len(self.group)
