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
Similar to the Table function selector, :ref:`F(x) Table`, one can with this
node apply non-general functions/scripts to the content of Tables.
The difference is that the considered node uses Matlab as scripting engine
instead of Python. Another difference is that the Python file coming in to
the function selector includes one or many selectable functions, which is
not the case for this node. Here, the Matlab file only consists of a single
written script.

In the matlab script one reaches the columns in the Table with the *hdfread*
command, like
::

    name_of_column_in_matlab = hdfread(infilename, '/name_of_column_in_Table');

and return the achieved results with *hdfwrite*
::

    hdfwrite(outfilename, 'Name_of_result', result_variable);

Do not change *infilename* and *outfilename* in the calls to *hdfread* and
*hdfwrite*, these are the names of variables transfered to Matlab from
Sympathy for Data. If several results are transmitted to the outgoing Table,
keep in mind that the length of the result arrays have the same length.

Here follows an example of a small script that can be applied the data in
cardata.csv, located in the Examples folder in the Sympathy for Data
directory,
::

    price = hdf5read(infilename, '/price');

    hdf5write(outfilename, 'MAX_PRICE', max(price), 'MIN_PRICE', min(price));

"""
import sys
import os
import tempfile
import subprocess
from sympathy.api.exceptions import SyNodeError

from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.platform.exceptions import NoDataError
from sympathy.platform import state


settings = state.node_state().attributes.get('settings', {})


class SuperNode(object):
    author = "Sara Gustafzelius <sara.gustafzelius@combine.se>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    description = 'Execute Matlab code'
    tags = Tags(Tag.DataProcessing.Calculate)

    def execute(self, node_context):
        try:
            matlab_path = settings['MATLAB/matlab_path'][0]
        except IndexError:
            matlab_path = ''
        disable_jvm = settings['MATLAB/matlab_jvm']
        input_table = node_context.input['port0']
        output_table = node_context.output['port1']
        input_script = node_context.input['port2']
        script = os.path.abspath(unicode(input_script.decode_path()))

        if node_context.input['port0'] is None:
            raise NoDataError(
                "Can't run calculation when empty input data is connected")

        in_tmp_file = tempfile.NamedTemporaryFile(
            prefix='node_matlab_', suffix='.sydata', delete=False)
        in_tmp_file_name = in_tmp_file.name
        in_tmp_file.close()

        out_tmp_file = tempfile.NamedTemporaryFile(
            prefix='node_matlab_', suffix='.sydata', delete=False)
        out_tmp_file_name = out_tmp_file.name
        out_tmp_file.close()

        # This helps to get file on correct format
        with table.FileList(
                filename=out_tmp_file_name, mode='w') as output_list:
            output_list.writeback()

        self.add_input(in_tmp_file_name, input_table)

        run_matlab_script(in_tmp_file_name, out_tmp_file_name, script,
                          matlab_path, disable_jvm)

        with table.FileList(
                filename=out_tmp_file_name, mode='r') as output_list:
            for tab in output_list:
                self.add_output(tab.to_dataframe(), output_table)


class MatlabTables(SuperNode, synode.Node):
    """
    Run Matlab code in Sympathy.

    :Inputs:
        **Table** : Table
            Table with data that is needed in the Matlab script.
    :Outputs:
        **TableOutput** : Table
            Table with the results from Matlab stored in separate columns.
    :Opposite node:
    :Ref. nodes: :ref:`F(x) Table`
    """

    name = 'Matlab Tables'
    nodeid = 'org.sysess.sympathy.matlab.matlabTables'
    inputs = Ports([Port.Datasource('M-file (*.m)', name='port2',
                                    requiresdata=True),
                    Port.Tables('Input Table', name='port0')])

    outputs = Ports([Port.Tables(
        'Tables with MATLAB script applied', name='port1')])

    def __init__(self):
        super(MatlabTables, self).__init__()

    def add_output(self, df, output_table):
        output_table.append(table.File.from_dataframe(df))

    def add_input(self, in_tmp_file_name, input_table):
        with table.FileList(filename=in_tmp_file_name, mode='w') as input_list:
            input_list.extend(input_table)


class Matlab(SuperNode, synode.Node):
    """
    Run Matlab code in Sympathy.

    :Inputs:
        **Table** : Table
            Table with data that is needed in the Matlab script.
    :Outputs:
        **TableOutput** : Table
            Table with the results from Matlab stored in separate columns.
    :Opposite node:
    :Ref. nodes: :ref:`F(x) Table`
    """

    author = ("Alexander Busck <alexander.busck@sysess.org>, "
              "Sara Gustafzelius <sara.gustafzelius@combine.se>")
    name = 'Matlab'
    nodeid = 'org.sysess.sympathy.matlab.matlab'

    inputs = Ports([Port.Datasource('M-file (*.m)', name='port2',
                                    requiresdata=True),
                    Port.Table('Input Table', name='port0')])

    outputs = Ports([Port.Table(
        'Tables with MATLAB script applied', name='port1')])

    def __init__(self):
        super(Matlab, self).__init__()

    def add_output(self, df, output_table):
        output_table.update(table.File.from_dataframe(df))

    def add_input(self, in_tmp_file_name, input_table):
        with table.File(filename=in_tmp_file_name, mode='w') as input:
            input.update(input_table)


def run_matlab_script(infilename, outfilename, mscript_filename,
                      matlab_executable_path, no_jvm):

    script_dir = os.path.split(mscript_filename)[0]
    full_path = os.path.realpath(__file__)
    dir_path = os.path.split(full_path)[0]
    matlib = os.path.abspath(os.path.join(
        dir_path, './../../../../Sympathy/Matlab'))

    matlab_code = (
        "cd('{0}'); \n" +
        "addpath('{1}'); \n" +
        "try \n" +
        "infilename = '{2}'; \n" +
        "outfilename = '{3}'; \n"
    ).format(script_dir, matlib, infilename, outfilename)

    matlab_code += (
        "run('{2}'); \n" +
        "quit; \n" +
        "catch err; \n" +
        "quit; \n" +
        "end; \n").format(infilename, outfilename, mscript_filename)

    command = [matlab_executable_path, '-r', '-wait', matlab_code]
    command.extend(['-nodesktop', '-nosplash'])
    if no_jvm:
        command.extend(['-nodisplay', '-nojvm'])

    p_open = None
    try:
        p_open = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)
        for line in iter(p_open.stdout.readline, ''):
            sys.stdout.write(line)
        p_open.wait()
    except:
        if p_open:
            p_open.kill()
        raise SyNodeError(
            'MATLAB could not be run. Have you set the MATLAB path in '
            'File/Preferences?')
