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
import zipfile
from sylib.export import datasource as exportdatasource


class DataExtractZip(exportdatasource.DatasourceDataExporterBase):
    """Extractor for ZIP files."""
    EXPORTER_NAME = "ZIP"
    FILENAME_EXTENSION = None

    def __init__(self, custom_parameter_root):
        super(DataExtractZip, self).__init__(custom_parameter_root)

    def export_data(self, in_datasource, directory, progress=None):
        """Extract files in ZIP file."""
        filenames = self._create_filenames(in_datasource)
        zip_infile = zipfile.ZipFile(in_datasource.decode_path())
        zip_infile.extractall(directory)
        return filenames

    def create_filenames(self, node_context_input):
        filenames = []

        for item in node_context_input['port0']:
            try:
                filenames.extend(self._create_filenames(item))
            except:
                self.warn_invalid(item)
        return filenames

    def _create_filenames(self, in_datasource):
        return [
            filename for filename in zipfile.ZipFile(
                in_datasource.decode_path()).namelist()
            if not filename.endswith('/')]
