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
"""Table Data source module."""
import numpy as np

from . import dsgroup


class NumpyTable(dsgroup.NumpyGroup):
    """Abstraction of a Numpy-table."""
    def __init__(self, table):
        self.record = dict((name, table[name]) for name in table.dtype.names)

    def read_columns(self, column_name):
        """Return np.rec.array with data from the given column name."""
        keys = list(self.record.keys())
        if column_name == "*":
            # Full selection used.
            rec_type = {'names': keys, 'formats': []}
            rec_data = []
            for key in keys:
                column = self.record[key]
                rec_data.append(column)
                rec_type['formats'].append(str(column.dtype))
        elif column_name in keys:
            # Named column selection used.
            column = self.record[column_name]
            rec_data = [column]
            rec_type = {'names': [column_name],
                        'formats': [str(column.dtype)]}
        # Construct the table as numpy array.
        return np.rec.array(rec_data, dtype=rec_type)

    def write_columns(self, table):
        """
        Stores columns in the table.
        """
        if self.record:
            first = self.record.itervalues().next()
            if first.shape != table.shape:
                raise ValueError(
                    "Table shape differs, original:{0} new:{1}".format(
                        first.shape, table.shape))
        for name in table.dtype.names:
            self.record[name] = table[name]

    def columns(self):
        """Return a list contaning the available column names."""
        return self.record.keys()
