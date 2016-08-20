# coding=utf8
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
"""
import shutil
import re
import os

from sympathy.api import qt as qt_compat
QtCore = qt_compat.QtCore # noqa
QtGui = qt_compat.import_module('QtGui') # noqa

from sympathy.api import node as synode
from sympathy.api import datasource as dsrc
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class SuperNode(object):
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '0.9'


class CopyFile(SuperNode, synode.Node):
    """
    Copy a file to another location. It is possible to name the copy using
    regular expressions.

    :Inputs:
        **Datasource** : DataSource
            Path to the file to copy.
    :Outputs:
        **Datasource** : DataSource
            Path to the copied file.
    :Configuration:
        **Configure the name of the new file.**

        **RegEx**
            Turn on/off naming using a regular expression.
        **RegEx pattern**
            Specify the regular expression that will be used for matching.
        **Replacement string**
            The string to replace the match found with the RegEx pattern.
        **Filename**
            Manually enter a filename, if not using a regular expression.
    """

    name = 'Copy file'
    description = 'Copy a file.'
    nodeid = 'org.sysess.sympathy.files.copyfile'
    tags = Tags(Tag.Disk.File)

    inputs = Ports([Port.Datasource(
        'Datasource of file to be copied', name='port1', scheme='text')])

    outputs = Ports([Port.Datasource(
        'Datasource of copied file', name='port1', scheme='text')])

    parameters = synode.parameters()
    parameters.set_boolean(
        'use_regex', label='RegEx', description='Use regular expressions.')
    parameters.set_string(
        'pattern', label='RegEx pattern',
        description='Replace the occurrences of the pattern in the input.')
    parameters.set_string(
        'replace', label='Replacement string',
        description='The replacement string.')
    parameters.set_string(
        'filename', label='Filename', description='A filename.')

    controllers = (
        synode.controller(
            when=synode.field('use_regex', state='checked'),
            action=(
                synode.field('filename', state='disabled'),
                synode.field('pattern', state='enabled'),
                synode.field('replace', state='enabled'),
            ),
        ),
    )

    def execute(self, node_context):
        parameters = node_context.parameters

        ds_in = node_context.input['port1'].decode()
        fq_infilename = ds_in['path']

        if parameters['use_regex'].value:
            new_filename = re.sub(
                parameters['pattern'].value,
                parameters['replace'].value,
                fq_infilename)
        else:
            new_filename = parameters['filename'].value

        shutil.copyfile(fq_infilename, new_filename)

        node_context.output['port1'].encode(
            dsrc.File.to_file_dict(new_filename))


class DeleteFile(synode.Node):
    """
    Delete a file.

    :Inputs:
        **Datasource** : DataSource
            Path to the file to delete.
    """

    name = 'Delete file'
    description = 'Delete a file.'
    author = "Magnus Sandén <magnus.sanden@combine.se>"
    copyright = "(C) 2016 System Engineering Software Society"
    version = '0.1'
    nodeid = 'org.sysess.sympathy.files.deletefile'
    tags = Tags(Tag.Disk.File)

    inputs = Ports([Port.Datasource(
        'Path to the file to delete.', name='port1')])
    outputs = Ports([Port.Datasource(
        'Path to deleted file', name='port1')])

    def execute(self, node_context):
        fq_infilename = node_context.input['port1'].decode_path()
        os.unlink(fq_infilename)
        node_context.output['port1'].encode_path(fq_infilename)
