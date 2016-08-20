# coding=utf-8
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
The calculator node can apply calculations on each table in a list. The
calculations are defined in the configuration GUI of the node. The calculations
are written as extended Python code and can consist of simple arithmetic
calculations, Python function calls or calls to functions defined in plugins.

Some commonly used operators and functions can be found under the function tree
structure (labeled *Common functions*) and can be added to a calculation by
double-clicking or dragging the function name to the calculation area. If you
want more information about a function, hover its name and its documentation
will appear as a tooltip.

The signal that you access in the calculations are returned as a numpy arrays.
The same as if you had called :meth:`get_column_to_array` from the
:ref:`tableapi`. This means that simple arithmetics and the functions from
numpy and pandas work fine out of the box. But if you want to apply some other
function which only works on a single element of the column you may need to use
the numpy function vectorize_. For example::

  ${filenames} = np.vectorize(os.path.basename)(${filepaths})

.. _vectorize: http://docs.scipy.org/doc/numpy/reference/generated/numpy.vectorize.html

Calculations
^^^^^^^^^^^^
You declare each calculation by typing a name in the text line labeled *Signal
name* and entering the calculation in the textfield labeled *Calculation*. You
can use any of the signals in the list *Signal names* in your calculation. To
use a signal from the incoming table type ``${name_of_signal}`` or simply
drag-and-drop the signal name from the list of available signals to the
calculation and type (or drag-and-drop) a function name from the *Avaliable
functions* tree structure. Note that any signal that you reference in the
calculation must exist in all incoming tables.

To add a new calculation, press the *New* button and the *Calculation* field as
well as *Signal name* will be cleared.  If your want to edit a calculation
simply click on the calculation in the *List of calculations*.  The signal name
will then appear under *Signal name* and the calculation will appear in the
*Calculation* field.  The calculation will be updated in the *Calculation*
field, *List of calculations* and preview simultaneously.  To remove a
calculation, mark a calculation in *List of calculations* and press the
*Remove* button.

The result of your calculation is written to a column in an outgoing table.

Here are a few example calculations::

  ${New signal name} = ${Old signal} + 1
  ${area} = ${width} * ${height}
  ${result} = (${signal0} == 2) & ca.change_up(${signal1})
  ${index} = np.arange(len(${some signal}))
  ${sine} = np.sin(${angle})

As you can see in the last two examples the numpy module is available in the
calculator under the name ``np``. If something goes wrong when you define the
calculations you will get an error message in the preview window
marked with red.

Output
^^^^^^
When the option *Put results in common outputs* is enabled (the default) each
input table results in a single output table with all the new columns. This
means that all the calculated columns must be the same length. When disabled
each calculation instead generates a table with a single column. The length of
the outgoing list therefore depends on the number of incoming Tables and the
number of operations that are applied to each Table. As an example, if the
incoming list consist of five tables and there are two calculations, the number
of tables in the outgoing list will be 5*2=10.

Note that the incoming columns never propagate to the output table. If the
results of you calculations are of the same length as the input, and the option
*Put results in common outputs* is enabled you can use the node
:ref:`VJoin Tables` to add calculated results to the input table.

Each column of the output will have an *calculation* attribute with a string
representation of the calculation used to create that column.
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import itertools

from sympathy.api import table
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sylib.calculator import calculator_model as models
from sylib.calculator import calculator_gui


def common_output_writer(infiles, calc_list, outfiles):
    for infile in infiles:
        outfile = outfiles.create()
        output_data = []
        for calc_line in calc_list:
            new_output_data = models.python_calculator(
                infile, calc_line, dict(output_data))
            for column, output in new_output_data:
                outfile.set_column_from_array(column, output)
                outfile.set_column_attributes(
                    column, {'calculation': calc_line})
            output_data.extend(new_output_data)
        outfiles.append(outfile)


def sep_output_writer(infiles, calc_list, outfiles):
    for infile in infiles:
        output_data = []
        for calc_line in calc_list:
            new_output_data = models.python_calculator(
                infile, calc_line, dict(output_data))
            for column, output in new_output_data:
                outfile = outfiles.create()
                outfile.set_column_from_array(column, output)
                outfile.set_column_attributes(
                    column, {'calculation': calc_line})
                outfiles.append(outfile)
            output_data.extend(new_output_data)


def model_common_output_writer(infiles, calc_list, outfiles):
    calc_sorting, reverse_sorting = models.get_calculation_order(calc_list)
    for infile in infiles:
        outfile = outfiles.create()
        output_data = []
        for idx in calc_sorting:
            new_output_data = models.python_calculator(
                infile, calc_list[idx], dict(output_data))
            output_data.extend(new_output_data)

        for idx, calc_line in itertools.izip(reverse_sorting, calc_list):
            column, output = output_data[idx]
            outfile.set_column_from_array(column, output)
            outfile.set_column_attributes(column, {'calculation': calc_line})
        outfiles.append(outfile)


def model_sep_output_writer(infiles, calc_list, outfiles):
    calc_sorting, reverse_sorting = models.get_calculation_order(calc_list)
    for infile in infiles:
        output_data = []
        for idx in calc_sorting:
            new_output_data = models.python_calculator(
                infile, calc_list[idx], dict(output_data))
            output_data.extend(new_output_data)

        for idx, calc_line in itertools.izip(reverse_sorting, calc_list):
            column, output = output_data[idx]
            outfile = outfiles.create()
            outfile.set_column_from_array(column, output)
            outfile.set_column_attributes(column, {'calculation': calc_line})
            outfiles.append(outfile)


class CalculatorNode(synode.Node):
    """
    Perform user-defined Python calculations on a list of input Tables.

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
    :Ref. nodes: :ref:`Matlab Calculator`
    """

    name = 'Calculator Tables'
    description = 'Performs user-defined python calculations'
    author = ('Greger Cronquist <greger.cronquist@sysess.org>, '
              'Magnus Sandén <magnus.sanden@combine.se>, '
              'Sara Gustafzelius <sara.gustafzelius@combine.se>, '
              'Benedikt Ziegler <benedikt.ziegler@combine.se>')
    copyright = '(c) 2012 Combine AB'
    nodeid = 'org.sysess.sympathy.data.table.calculator'
    version = '3.0'
    icon = 'calculator.svg'
    tags = Tags(Tag.DataProcessing.Calculate)

    inputs = Ports([Port.Tables('Input Table', name='port0')])
    outputs = Ports([Port.Tables(
        'The input Table with added plot attributes', name='port1')])

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

    def update_parameters(self, old_params):
        # Old nodes without the same_length_res option work the same way as if
        # they had the option, set to False.
        if 'same_length_res' not in old_params:
            old_params['same_length_res'] = self.parameters['same_length_res']
            old_params['same_length_res'].value = False

    def exec_parameter_view(self, node_context):
        input_data = node_context.input['port0']
        if not input_data.is_valid():
            input_data = table.FileList()
        return calculator_gui.CalculatorWidget(
            input_data, node_context.parameters,
            backend='python', preview_calculator=models.python_calculator)

    def _update_calc(self, parameters, infiles, outfiles):
        calc_list = parameters['calc_list'].list
        same_length_res = parameters['same_length_res'].value

        if same_length_res:
            model_common_output_writer(infiles, calc_list, outfiles)
        else:
            model_sep_output_writer(infiles, calc_list, outfiles)

    def execute(self, node_context):
        """Execute"""
        self._update_calc(node_context.parameters,
                          node_context.input['port0'],
                          node_context.output['port1'])


class CalculatorTableNode(synode.Node):
    """
    Perform user-defined Python calculations on a list of input Tables.

    :Inputs:
        **Table** : Table
            Tables with data.
    :Outputs:
        **OutTable** : Table
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
    :Ref. nodes: :ref:`Matlab Calculator`
    """

    name = 'Calculator Table'
    description = 'Performs user-defined python calculations'
    author = ('Greger Cronquist <greger.cronquist@sysess.org>, '
              'Magnus Sandén <magnus.sanden@combine.se>, '
              'Sara Gustafzelius <sara.gustafzelius@combine.se>, '
              'Benedikt Ziegler <benedikt.ziegler@combine.se>')
    copyright = '(c) 2012 Combine AB'
    nodeid = 'org.sysess.sympathy.data.table.calculatortable'
    version = '3.0'
    icon = 'calculator.svg'
    tags = Tags(Tag.DataProcessing.Calculate)

    inputs = Ports([Port.Table('Input Table', name='port0')])
    outputs = Ports([Port.Table(
        'The input Table with added plot attributes', name='port1')])

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

    def update_parameters(self, old_params):
        # Old nodes without the same_length_res option work the same way as if
        # they had the option, set to False.
        if 'same_length_res' not in old_params:
            old_params['same_length_res'] = self.parameters['same_length_res']
            old_params['same_length_res'].value = False

    def exec_parameter_view(self, node_context):
        input_data = node_context.input['port0']
        if not input_data.is_valid():
            input_data = table.File()
        return calculator_gui.CalculatorWidget(
            input_data, node_context.parameters,
            backend='python', preview_calculator=models.python_calculator)

    def execute(self, node_context):
        """Execute"""
        out_list = table.FileList()
        model_common_output_writer([node_context.input['port0']],
                                   node_context.parameters['calc_list'].list,
                                   out_list)

        out_table = node_context.output['port1']
        out_table.update(out_list[0])
