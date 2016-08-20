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
With the considered node one can apply simple operations on the content of
Tables. The node has the same structure as the :ref:`Calculator Tables` node
with the difference that Matlab is used as scripting engine instead of Python.

In the line of text that declares the calculations one get access to the
columns in the incoming Tables by typing ${name_of_column}. In the same manner
a new column in the outgoing Table is declared. See the example below,
::

    ${New Column} = function(${Old Column}, 2.2, 'first') + 20.0

In the declaration of calculations the asterisk, \*, can be used for wild card
matching.
"""

import subprocess
import tempfile
import sys
import re
import os

from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sylib.calculator import calculator_model
from sylib.calculator import calculator_gui
from sympathy.api.exceptions import SyNodeError
from sympathy.platform import state


settings = state.node_state().attributes.get('settings', {})


def generate_matlab_script(input_filename, output_filename, num_inputs,
                           old_col_names, calc_list, extra_globals=dict([])):
    """Generates the script to be run in Matlab based on GUI calculations."""
    full_path = os.path.realpath(__file__)
    dir_path = os.path.split(full_path)[0]
    matlib = os.path.abspath(os.path.join(
        dir_path, './../../../../Sympathy/Matlab'))

    m_script = (
        "try\n" +
        "infilename = '{0}';\n" +
        "outfilename = '{1}';\n" +
        "addpath('{2}');\n" +
        "in = Files('', infilename);\n" +
        "out = Files(outfilename, '');\n").format(
            input_filename, output_filename, matlib)

    for table_index in xrange(num_inputs):
        string = ("in_table = in.get({0});\n" +
                  "in_attrs = in_table.get_table_attributes();\n" +
                  "out_table = File(outfilename, '{0}', '');\n" +
                  "out_table = out_table.set_table_attributes(in_attrs);\n")
        m_script += string.format(table_index)

        for calc_text in calc_list:
            var, calc = calc_text.split('=', 1)
            var = var.strip()
            var_name_match = re.match(r'\${([^{}]+)}', var)
            if var_name_match:
                var_name = var_name_match.group(1)
            else:
                var_name = var
            calc = calc.strip()
            col_names, func_calls, outputs = calculator_model.line_parser(
                var_name, calc, list(old_col_names) + extra_globals.keys())

            order = len(outputs) * len(calc_list)
            m_script += (
                "out_table = out_table.set_table_order({1});\n").format(
                    table_index, order)

            for old_name, calc, col_name in zip(
                    col_names, func_calls, outputs):
                m_script += (
                    "out_table = out_table.set_column_attributes(" +
                    "'/{0}/{1}', " +
                    "in_table.get_column_attributes('/{0}/{2}'));\n" +
                    "out_table = out_table.set_column_type(" +
                    "'/{0}/{1}', in_table.column_type('/{0}/{2}'));\n").format(
                        table_index, col_name, old_name)

                for name in col_names:
                    m_script += (
                        "{0} = in_table.get_column_data(" +
                        "'/{1}/{2}');\n").format(
                            col_names[name], table_index, name)

                m_script += ("output =  calc(\'{0}\', size({1}));\n").format(
                    calc, col_names[name])
                m_script += (
                    "out_table = out_table.set_column_data(" +
                    "'/{0}/{1}', output);\n" +
                    "out = out.set({0}, out_table);\n").format(
                        table_index, col_name)

            if not zip(col_names, func_calls, outputs) and order:
                for calc, col_name in zip(func_calls, outputs):
                    m_script += (
                        "out_table = out_table.set_column_type(" +
                        "'/{0}/{1}', H5T.copy('H5T_NATIVE_DOUBLE'));\n" +
                        "out_table = out_table.set_column_attributes(" +
                        "'/{0}/{1}', in_table.get_column_attributes(" +
                        "'/{0}/{1}'));\n" +
                        "out_table = out_table.set_column_attributes(" +
                        "'/{0}/{1}', containers.Map);\n" +
                        "out_table = out_table.set_table_order({2});\n" +
                        "output = calc('int32({3})');\n"
                        "out_table = out_table.set_column_data(" +
                        "'/{0}/{1}', output);\n" +
                        "out = out.set({0}, out_table);\n").format(
                            table_index, col_name, len(calc), calc)

    m_script += (
        '% Write everything to file \n' +
        'out.writeback(); \n' +
        'quit;\n' +
        'catch err \n' +
        'err \n' +
        'quit;\n' +
        'end\n')
    return m_script


def _execute_matlab(script, matlab_exe_path, no_jvm):
    # Create the matlab script as an m-script

    with tempfile.NamedTemporaryFile(
            prefix='node_matlab_calculator_',
            suffix='.m', delete=False) as script_file:
        script_file.write(script)
        script_file.flush()

    # Run matlab and copy the results.
    command = [
        matlab_exe_path, '-r', '-wait',
        "run('{0}'); quit".format(script_file.name)]
    command.extend(['-nodesktop', '-nosplash'])
    if no_jvm:
        command.extend(['-nodisplay', '-nojvm'])

    p_open = None
    try:
        p_open = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  stdin=subprocess.PIPE)
        for line in iter(p_open.stdout.readline, ''):
            print sys.stdout.write(line)
        for line in iter(p_open.stderr.readline, ''):
            print sys.stderr.write(line)
        p_open.wait()
    except:
        if p_open:
            p_open.kill()
        raise SyNodeError(
            'MATLAB could not be run. Have you set the MATLAB path in '
            'File/Preferences?')


class MatlabCalculator(synode.Node):
    """
    Perform user-defined Matlab calculations on a list of input Tables.

    :Inputs:
        **Table** : Tables
            Tables with data.
    :Outputs:
        **OutTable** : Tables
            Tables with results from the calculation performed by the node.
            The length of the outgoing list depends on the number of incoming
            Tables and the number of defined calculations. For example, if the
            incoming list consist of five Tables and 2 calculations have been
            defined, the number of outgoing Tables will be equal to 5*2=10.
    :Configuration:
        **Calculation**
            Type the calculation you want to be performed.
        **New** : button
            Clears the *Calculation* and *Signal name* field and makes it
            possible to enter a new calculation.
        **Signals**
            List with the available signals in the incoming Tables. One can
            drag and drop a signal to the *Calculation* field as well as the
            *Signal name* field instead of writing it yourself.
        **List of calculations**
            List with defined calculations. To edit a calculation click on the
            calculation and the calculation will appear in the *Calculation*
            field as well as the *Signal name* field. The calculation can then
            be edited.
        **Remove** : button
            Press *Remove* and the calculation marked in the *Calculation list*
            will be removed.
        **Put results in common outputs** : checkbox
            Use this checkbox if you want to gather all the results generated
            from an incoming Table into a common output. This requires that
            the results will all have the same length. An exception will be
            raised if the lengths of the outgoing results differ.
    :Ref. nodes: :ref:`Calculator Tables`
    """

    name = 'Matlab Calculator'
    description = 'Performs user-defined Matlab calculations'
    author = ("Greger Cronquist <greger.cronquist@sysess.org, "
              "Sara Gustafzelius <sara.gustafzelius@combine.se>")
    copyright = '(c) 2013 The Software Engineering Society'
    nodeid = 'org.sysess.sympathy.matlab.matlabcalculator'
    version = '0.1'
    icon = 'calculator.svg'
    tags = Tags(Tag.DataProcessing.Calculate)

    inputs = Ports([Port.Tables('Input Table', name='port0')])
    outputs = Ports([Port.Tables(
        'Table applied with MATLAB functions', name='port1')])

    parameters = synode.parameters()
    parameters.set_list(
        'calc_list', label='List of calculations',
        description='List of calculations.')
    parameters.set_boolean(
        'same_length_res', label='Put results in common outputs.',
        value=True, description=(
            'Gather all the results generated from an incoming Table into a '
            'common output table. This requires that the results all have the '
            'same length. An error will be given if the lengths of the '
            'outgoing results differ.'))

    def exec_parameter_view(self, node_context):
        return calculator_gui.OldCalculatorWidget(node_context.input['port0'],
                                                  node_context.parameters,
                                                  backend='matlab')

    def execute(self, node_context):
        try:
            matlab_path = settings['MATLAB/matlab_path'][0]
        except IndexError:
            matlab_path = ''
        disable_jvm = settings['MATLAB/matlab_jvm']
        input_table = node_context.input['port0']
        output_table = node_context.output['port1']

        parameters = node_context.parameters
        parameter_root = synode.parameters(parameters)
        calc_list = parameter_root['calc_list'].list

        if len(calc_list) == 0:
            return

        # Create new temporary files to ensure that all links are resolved
        in_tmp_file = tempfile.NamedTemporaryFile(
            prefix='node_matlab_calculator_', suffix='.sydata', delete=False)
        in_tmp_file_name = in_tmp_file.name
        in_tmp_file.close()

        if len(input_table) == 0:
            raise NotImplementedError(
                "Can't run calculation when empty input data is connected")

        with table.FileList(filename=in_tmp_file_name, mode='w') as input_list:
            number_of_inputs = len(input_table)
            input_list.extend(input_table)

        out_tmp_file = tempfile.NamedTemporaryFile(
            prefix='node_matlab_calculator_', suffix='.sydata', delete=False)
        out_tmp_file_name = out_tmp_file.name
        out_tmp_file.close()

        # This helps to get file on correct format
        with table.FileList(
                filename=out_tmp_file_name, mode='w') as output_list:
            output_list.writeback()

        column_names = input_table[0].column_names()
        matlab_code = generate_matlab_script(
            in_tmp_file_name, out_tmp_file_name, number_of_inputs,
            column_names, calc_list)

        _execute_matlab(matlab_code, matlab_path, disable_jvm)

        if len(column_names):
            with table.FileList(
                    filename=out_tmp_file_name, mode='r') as output_list:
                for tab in output_list:
                    df = tab.to_dataframe()
                    output_table.append(table.File.from_dataframe(df))
