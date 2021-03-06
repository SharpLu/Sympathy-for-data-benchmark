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
"""Text list."""
import dsgroup


class TextList(dsgroup.TextGroup):
    """Abstraction of an Text-list."""
    def __init__(self,
                 factory,
                 create_content,
                 datapointer,
                 group=None,
                 can_write=False,
                 container_type=None,
                 create_path=None):
        super(TextList, self).__init__(
            factory, create_content, datapointer, group, can_write,
            container_type, create_path)

    def read_with_type(self, index, content_type):
        """Reads element at index and returns it as a datasource."""
        return self.factory(
            self.datapointer, self.group[index], content_type, self.can_write)

    def write_with_type(self, index, value, content_type):
        """Write group at index and returns the group as a datasource."""
        key = str(index)

        if key in self.group:
            key_group = self.group[key]
        else:
            key_group = self.create_content(content_type)
            self.group.append(key_group)

        return self.factory(
            self.datapointer, key_group, content_type, self.can_write)

    def size(self):
        """Return the list size."""
        return len(self.group)
