# Copyright (c) 2015, System Engineering Software Society
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
import os
import gzip
from sylib.export import datasource as exportdatasource


class DataExtractGz(exportdatasource.DatasourceDataExporterBase):
    """Extractor for GZIP files."""
    EXPORTER_NAME = "GZIP"
    FILENAME_EXTENSION = None

    def __init__(self, custom_parameter_root):
        super(DataExtractGz, self).__init__(custom_parameter_root)

    def export_data(self, in_datasource, directory, progress=None):
        """Extract GZIP file."""
        filename = self._create_filename(in_datasource)
        gz_file = gzip.GzipFile(in_datasource.decode_path())
        file_content = gz_file.read()
        gz_file.close()
        with open(os.path.join(directory, filename), 'wb') as f:
            f.write(file_content)
        return [filename]

    def create_filenames(self, node_context_input):
        filenames = []
        for item in node_context_input['port0']:
            try:
                filenames.append(self._create_filename(item))
            except:
                self.warn_invalid(item)
        return filenames

    def _create_filename(self, in_datasource):
        gzip.GzipFile(in_datasource.decode_path())
        filename = os.path.splitext(in_datasource.decode_path())[0]
        return os.path.split(filename)[1]
