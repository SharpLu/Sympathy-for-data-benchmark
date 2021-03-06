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
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module(b'QtGui')

from sympathy.api import adaf
from sylib.export import adaf as exportadaf


class DataExportHDF5Widget(exportadaf.TabbedDataExportWidget):
    pass


class DataExportHDF5(exportadaf.TabbedADAFDataExporterBase):
    """Exporter for HDF5 files."""
    EXPORTER_NAME = "HDF5"
    DISPLAY_NAME = 'SyData'
    FILENAME_EXTENSION = 'sydata'

    def __init__(self, custom_parameter_root):
        super(DataExportHDF5, self).__init__(custom_parameter_root)

    def parameter_view(self, node_context_input):
        return DataExportHDF5Widget(self._custom_parameter_root,
                                    node_context_input)

    def export_data(self, adafdata, fq_outfilename, progress=None):
        """Export ADAF to HDF5."""
        with adaf.File(filename=fq_outfilename, mode='w',
                       source=adafdata):
            pass
        progress(100.)
