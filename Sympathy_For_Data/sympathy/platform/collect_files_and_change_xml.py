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

from xml.dom import minidom
import json
from shutil import copy
import os
import random
import re
import argparse

from sympathy.common.filename_retriever_gui import FilenameRetriever


def copy_files_to_dir(filenames):
    """ Copy all files to current directory  if filename not already in
        current directory. """
    for filename in filenames.keys():
        if not in_current_dir(filename):
            copy_file_to_dir(filename, filenames[filename])


def copy_file_to_dir(fq_filename, new_filename):
    """ Copy one file to current directory. """
    copy(fq_filename, new_filename)


def copy_dirs(dirnames):
    """ Copy directories with containing files. """
    #Dirnames dict with dirnames as keys and destination folders as values
    for dirname in dirnames.keys():
        if not in_current_dir(dirname):
            copy_dir(dirname, dirnames[dirname])


def copy_dir(dirname, dest):
    """ Copy files from directory dirname to directory dest. """
    src_files = os.listdir(dirname)
    for file_name in src_files:
        full_file_name = os.path.join(dirname, file_name)
        if (os.path.isfile(full_file_name)):
            copy(full_file_name, unicode(dest))


def create_dirs(dirnames):
    """ Create directories in dirnames if not already existing. """
    for dirname in dirnames.keys():
        # If dirname not in current folder, create new directory
        if not in_current_dir(dirname):
            new_dir = dirnames[dirname]
            full_new_dir = os.path.abspath(new_dir)
            if not os.path.exists(full_new_dir):
                os.makedirs(full_new_dir)


def create_dir_dict(dirnames, patterns=None, pattern_files_only=False):
    """ Create directory dictionary with old directory names as keys
        and new names as values. """
    dirnames_dict = {}
    for ind, dirname in enumerate(dirnames):
        if pattern_files_only and patterns is not None:
            dir_key = dirname + patterns[ind]
        else:
            dir_key = dirname
        if dir_key not in dirnames_dict.keys():
            if not in_current_dir(dir_key):
                new_dest = os.path.join(
                    os.path.curdir, 'data_%d' % (random.randrange(0, 100000)))
                while (new_dest in dirnames_dict.values() and not
                        os.path.exists(os.path.abspath(new_dest))):
                    new_dest = os.path.join(
                        os.path.curdir,
                        'data_%d' % (random.randrange(0, 100000)))
                dirnames_dict[dir_key] = new_dest
            else:
                dirnames_dict[dir_key] = dir_key

    return dirnames_dict


def in_current_dir(dir_key):
    """ Check if directory or file already is in current directory. """
    if os.path.abspath(dir_key).startswith(os.path.abspath(os.path.curdir)):
        return True
    return False


def get_file_names(filenames, dirnames, patterns, rename=True):
    """ Get filename list from filenames, dirnames and search patterns. """
    for dirname, pattern in zip(dirnames, patterns):
        filename_retriever = FilenameRetriever(dirname, pattern)
        selected_fq_filenames = filename_retriever.filenames(
            fully_qualified=True,
            recursive=False)  # self._parameters['recursive'].value)??
        for selected_filename in selected_fq_filenames:
            add_filename(filenames, selected_filename, rename=rename)


def add_filename(filenames, filename, rename=True):
    """ Add a filename to dictionary filenames if not already a key. """
    base_filename = os.path.join(os.path.curdir, os.path.basename(filename))
    if not filename in filenames.keys():
        if rename:
            filenames[filename] = get_nonexisting_filename(
                filenames, base_filename)
        else:
            filenames[filename] = base_filename


def get_nonexisting_filename(filenames, base_filename):
    """ Get a filename that does not already exist in current directory.
        If base_filename exist, a number is added to the filename.
    """
    base_filename_new = base_filename
    k = 1
    while base_filename_new in filenames.values():
        split_name = os.path.splitext(base_filename)
        base_filename_new = (unicode(split_name[0]) + unicode(k) +
                             unicode(split_name[1]))
        k += 1
    return base_filename_new


def get_file_info(doc, rename=True):
    """ Get information about files used in the xml-file. """
    filenames = {}
    roots = doc.childNodes
    root = roots[1]
    dirnames = []
    patterns = []

    first_node = root.getElementsByTagName('nodes')
    node_list = first_node[0].getElementsByTagName('node')
    for node in node_list:
        node_id = node.getAttribute('identifier')
        param_dict = get_param_dict(node)
        if node_id == 'org.sysess.sympathy.datasources.filedatasource':
            try:
                filename = param_dict['parameters']['filename']['value']
                add_filename(filenames, filename, rename=rename)
            except:
                pass
        elif node_id == 'org.sysess.sympathy.datasources.filedatasourcemultiple':
            try:
                dirname = param_dict['parameters']['directory']['value']
                pattern = param_dict['parameters']['search_pattern']['value']
                dirnames.append(dirname)
                patterns.append(pattern)
            except:
                pass

    return filenames, dirnames, patterns


def get_param_dict(node):
    """ Get dictionary 'parameters' from input node. """
    node_params = node.getElementsByTagName('parameters')
    node_param = node_params[0]
    if node_param.getAttribute('type') == 'json':
        regex = re.compile("<!\[CDATA\[({.*)]\]>", re.MULTILINE | re.DOTALL)

        c_data_sect_list = [n for n in node_param.childNodes
                            if n.nodeType == node_param.CDATA_SECTION_NODE][0]
        c_data_sect = c_data_sect_list.toxml()
        param_dict = regex.findall(c_data_sect)
        return json.loads(param_dict[0])
    return {}


def set_param_dict(doc, node, param_dict):
    """ Get dictionary 'parameters' from input node. """
    node_params = node.getElementsByTagName('parameters')
    node_param = node_params[0]
    if node_param.getAttribute('type') == 'json':
        c_data_sect = [n for n in node_param.childNodes
                       if n.nodeType == node_param.CDATA_SECTION_NODE][0]
        param_str = json.dumps(param_dict)

        new_c_data = doc.createCDATASection(param_str)
        node_param.replaceChild(new_c_data, c_data_sect)


def change_file_info(doc, filenames, dirnames, out_filename):
    """ Get information about files used in the xml-file. """
    roots = doc.childNodes
    root = roots[1]
    first_node = root.getElementsByTagName('nodes')
    node_list = first_node[0].getElementsByTagName('node')
    for node in node_list:
        node_id = node.getAttribute('identifier')
        param_dict = get_param_dict(node)
        if node_id == 'org.sysess.sympathy.datasources.filedatasource':
            try:
                filename = param_dict['parameters']['filename']['value']
                new_filename = filenames[filename]
                param_dict['parameters']['filename']['value'] = new_filename
                set_param_dict(doc, node, param_dict)
            except:
                pass
        elif node_id == 'org.sysess.sympathy.datasources.filedatasourcemultiple':
            try:
                dirname = param_dict['parameters']['directory']['value']
                new_dirname = dirnames[dirname]
                param_dict['parameters']['directory']['value'] = new_dirname
                set_param_dict(doc, node, param_dict)
            except:
                pass
    with open(out_filename, 'wb') as f:
        doc.writexml(f)


def copy_and_change(path_xml, out_filename=None, rename=True):
    """ Collect and copy files to current directory. If rename=True, files
        with same basename will be renamed. If no out_filename is given,
        out_filename will overwrite infile path_xml."""
    if out_filename is None:
        out_filename = path_xml
    xmldoc = minidom.parse(path_xml)
    filenames, dirnames, _ = get_file_info(xmldoc, rename=rename)
    dirnames_dict = create_dir_dict(dirnames)
    copy_files_to_dir(filenames)
    create_dirs(dirnames_dict)
    copy_dirs(dirnames_dict)
    change_file_info(xmldoc, filenames, dirnames_dict, out_filename)


def main():
#    path_xml = "C:/Users/Helena/Documents/Helena/XML parsing/test_flow.xml"
#    out_filename = "C:/Users/Helena/Documents/Helena/XML parsing/outfile.xml"
#    copy_and_change(path_xml, out_filename=out_filename, rename=True)
    parser = argparse.ArgumentParser(
        'Collect all files used in a flow, copy these to the directory of '
        'the flow and change paths in the xml-file to refer to the copied '
        'files.')
    parser.add_argument(
        'infile', action='store', help='Filename path to the flow')

    parser.add_argument(
        '-r', '--rename', action='store', default=True,
        help='Rename files if several files with same base name are used.')

    parser.add_argument(
        '-o', '--outfile', action='store', default=None,
        help=('Output filename. NOTE: If not set, input file will'
        ' be overwritten.'))
    results = parser.parse_args()
    results_dict = vars(results)
    print results_dict
    try:
        copy_and_change(
            results_dict['infile'], rename=results_dict['rename'],
            out_filename=results_dict['outfile'])
    except:
        raise ValueError('Filename paths not valid.')


if __name__ == '__main__':
    main()
