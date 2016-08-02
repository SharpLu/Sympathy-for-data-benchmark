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
API for working with the Datasource type.

Import this module like this::

    from sympathy.api import datasource

Class :class:`datasource.File`
------------------------------
.. autoclass:: File
   :members:
   :special-members:

Class :class:`datasource.FileList`
----------------------------------
.. autoclass:: FileList
   :members: __getitem__, append

"""
import sys
import collections
import json

from .. datasources.info import get_fileinfo_from_scheme
from .. dataexporters import utils as dsutils
from .. utils import prim, filebase
from .. utils.context import inherit_doc
from . import text


def is_datasource(fq_filename):
    fileinfo = get_fileinfo_from_scheme('text')(fq_filename)
    try:
        return fileinfo.type() == str(File.container_type)
    except (KeyError, AttributeError, TypeError):
        pass
    try:
        data = File(filename=fq_filename, scheme='text')
        data.decode_path()
        data.decode_type()
        return True
    except:
        pass
    return False


def is_datasources(fq_filename):
    fileinfo = get_fileinfo_from_scheme('text')(fq_filename)
    try:
        return fileinfo.type() == str(FileList.container_type)
    except (KeyError, AttributeError, TypeError):
        pass
    try:
        data = FileList(filename=fq_filename, scheme='text')
        data[0].decode_path()
        data[0].decode_type()
        return True
    except:
        pass
    return False


@filebase.typeutil('sytypealias datasource = sytext')
@inherit_doc
class File(text.File):
    """
    A Datasource representing a sources of data. It can currently point to
    either a file on disk or to a database.

    Any node port with the *Datasource* type will produce an object of this
    kind.
    """

    def decode_path(self):
        """Return the path.

        In a file data source this corresponds to the path of a file. In a data
        base data source this corresponds to a connection string. That can be
        used for accessing the data base. Returns None if path hasn't been set.

        .. versionchanged:: 1.2.5
            Return None instead of raising KeyError if path hasn't been set.
        """
        return self.decode().get('path')

    def decode_type(self):
        """Return the type of this data source.

        It can be either ``'FILE'`` or ``'DATABASE'``. Returns None if type
        hasn't been set.

        .. versionchanged:: 1.2.5
            Return None instead of raising KeyError if type hasn't been set.
        """
        return self.decode().get('type')

    def decode(self):
        """Return the full dictionary for this data source."""
        datasource_json = self.get()
        if not datasource_json:
            return {}
        datasource_dict = json.loads(datasource_json)
        if datasource_dict.get('type') == 'FILE':
            datasource_dict['path'] = prim.nativepath(datasource_dict['path'])
        return datasource_dict

    @staticmethod
    def to_file_dict(fq_filename):
        """Create a dictionary to be used for creating a file data source.

        You usually want to use the convenience method :meth:`encode_path`
        instead of calling this method directly."""
        return collections.OrderedDict(
            [('path', fq_filename), ('type', 'FILE')])

    @staticmethod
    def to_database_dict(db_driver,
                         db_servername,
                         db_databasename,
                         db_user,
                         db_password='',
                         db_connection_string=''):
        """Create a dictionary to be used for creating a data base data source.

        You usually want to use the convenience method :meth:`encode_database`
        instead of calling this method directly."""
        if db_connection_string:
            return collections.OrderedDict(
                [('path', db_connection_string), ('type', 'DATABASE')])
        else:
            # Add driver, server and database information.
            connection_string = 'DRIVER={{{}}};SERVER={};DATABASE={}'.format(
                db_driver, db_servername, db_databasename)
            # Add authentication information.
            connection_string = '{0};UID={1};PWD={2}'.format(
                connection_string, db_user, db_password)
            if sys.platform.startswith('darwin'):
                # Replace {SQL Server} driver with TDS on OS X.
                connection_string = connection_string.replace(
                    '{SQL Server}', 'TDS')
                # TDS version must be set to 8.0 on OS X.
                tds_version = '8.0'
                connection_string = '{0};TDS_Version={1}'.format(
                    connection_string, tds_version)

            return collections.OrderedDict(
                [('path', connection_string), ('type', 'DATABASE')])

    def encode(self, datasource_dict):
        """Store the info from datasource_dict in this datasource.

        :param datasource_dict: should be a dictionary of the same format that
          you get from :meth:`to_file_dict` or :meth:`to_database_dict`.

        """
        datasource_dict = dict(datasource_dict)
        if datasource_dict.get('type') == 'FILE':
            datasource_dict['path'] = prim.unipath(datasource_dict['path'])

        self.set(json.dumps(datasource_dict))

    def encode_path(self, fq_filename):
        """Store a path to a file in this datasource.

        :param fq_filename: should be a string containing the path. Can be
          relative or absolute.

        """
        self.encode(self.to_file_dict(fq_filename))

    def encode_database(self,
                        db_driver,
                        db_servername,
                        db_databasename,
                        db_user,
                        db_password=''):
        """Store data base access info."""
        self.encode(self.to_database_dict(db_driver,
                                          db_servername,
                                          db_databasename,
                                          db_user,
                                          db_password=''))


def exporter_factory(exporter_type):
    return dsutils.datasource_exporter_factory(exporter_type)


@inherit_doc
class FileList(filebase.FileListBase):
    """
    The :class:`FileList` class is used when working with lists of Datasources.

    The main interfaces in :class:`FileList` are indexing or iterating for
    reading (see the :meth:`__getitem__()` method) and the :meth:`append()`
    method for writing.

    Any port with the *Datasources* type will produce an object of this kind.
    If it is an input port the :class:`FileList` will be in read-through mode,
    disallowing any write actions and disabling list level caching. If it is an
    output port the :class:`FileList` will be in write-through mode,
    disallowing any read actions and making methods like :meth:`append()`
    trigger an imidiate writeback of that element.
    """
    sytype = '[text]'
    scheme = 'text'
