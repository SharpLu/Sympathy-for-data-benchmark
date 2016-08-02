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
import re
import fnmatch
import datetime

import numpy as np
import pandas

from sympathy.api import node as synode
from sylib.calculator import plugins


def line_parser(varname, calc, all_columns):
    """Make valid python code from the calculation string by replacing e.g.
    ${a} with col_0.

    Expands wilcards into multiple calculations. We support three cases:
      0: Only ever one match for all columns
      1: One with many matches, the rest with one
      2: All with the same number of matches

    Returns
    -------
    tuple
        A tuple with three elements:
            0. A dictionary mapping old column names to the new col_0 names.
            1. A list of calculations with replaced column names.
            2. A list of outgoing column names.

    Raises
    ------
    KeyError
        if a calculation uses a column name that isn't in all_columns.
    """
    if calc is None:
        return None, None, None
    columns = re.findall(r'\${([^{}]+)}', calc)
    outputs = []

    global col_ctr, column_names
    col_ctr = 0
    column_names = {}

    def replacer(match_):
        global col_ctr, column_names
        if isinstance(match_, basestring):
            match = match_
        else:
            match = match_.groups()[0]
        if match in column_names:
            name = column_names[match]
        else:
            name = 'col_{0}'.format(col_ctr)
            column_names[match] = name
            col_ctr += 1
        return name

    calcs = []
    filtered_columns = []
    for column in columns:
        filtered_column = [n for n in all_columns
                           if fnmatch.fnmatchcase(n, column)]

        # Raise KeyError if there is no match
        if not filtered_column:
            raise KeyError(column)

        filtered_columns.append((column, filtered_column))
    lengths = set([len(match) for c, match in filtered_columns])
    unique_matches = sorted((tuple(x) for c, x in filtered_columns),
                            key=lambda m: len(m), reverse=True)

    match_case = -1
    if len(lengths) == 1:
        if min(lengths) == 1:
            match_case = 0
        else:
            match_case = 2
    elif len(lengths) == 2:
        if min(lengths) == 1:
            match_case = 1
        elif min(lengths) == max(lengths):
            if len(unique_matches) == 1:
                match_case = 2

    # Construct the replaced calculations
    if match_case > 0:
        col_name, match_columns = max(
            filtered_columns, key=lambda m: len(m[1]))
        for column in match_columns:
            function_call = calc.replace(
                '${{{0}}}'.format(col_name), replacer(column))
            function_call = re.sub(r'\${([^{}]+)}', replacer, function_call)
            calcs.append(function_call)
            outputs.append(varname.replace('*', column))
    else:
        if match_case == 0:
            function_call = re.sub(r'\${([^{}]+)}', replacer, calc)
            calcs.append(function_call)
            outputs.append(varname)
        elif match_case == -1:
            calcs.append(calc)
            outputs.append(varname)

    return column_names, calcs, outputs


def python_calculator(in_table, calc_text, extra_globals=None):
    var, calc = calc_text.split('=', 1)
    var = var.strip()
    varname_match = re.match(r'\${([^{}]+)}', var)
    if varname_match:
        varname = varname_match.group(1)
    else:
        # TODO: smarter way to choose backup varname
        varname = var
    calc = calc.strip()
    column_names, calcs, outputs = line_parser(
        varname, calc, in_table.column_names() + extra_globals.keys())
    variables = {}
    for old_name in column_names:
        if old_name in extra_globals:
            variables[column_names[old_name]] = extra_globals[old_name]
        else:
            variables[column_names[old_name]] = in_table.get_column_to_array(
                old_name)
    variables.update(extra_globals or {})

    output_data = []
    for calc, col_name in zip(calcs, outputs):
        # Add col_0, col_1, etc to global variables:
        output = advanced_eval(calc, variables)
        if not isinstance(output, np.ndarray):
            output = np.array([output])
        output_data.append((col_name, output))
    return output_data


def advanced_eval(calc, globals_dict=None):
    """
    Evaluate expression in a standardized python environment with a few
    imports:
     - datetime
     - numpy as np
     - os
     - pandas
     - re

    globals_dict argument can be used to extend the environment.
    """
    context = {'datetime': datetime,
               'np': np,
               'os': os,
               'pandas': pandas,
               're': re}
    if globals_dict:
        context.update(globals_dict)
    for plugin in plugins.available_plugins():
        context.update(plugin.globals_dict())

    return eval(calc, context, {})


class CalculatorModel(object):
    """Model"""

    def __init__(self, in_tables, parameters, backend='python',
                 preview_calculator=None, parent=None):
        self._in_tables = in_tables
        self._parameter_root = synode.parameters(parameters)
        self._preview_calculator = preview_calculator

        if self._in_tables.is_valid():
            columns = set()
            for in_table in self._in_tables:
                columns.update(in_table.column_names())
            column_names = sorted(columns, key=lambda s: s.lower())
        else:
            column_names = []
        self._parameter_root.set_list('column_names', column_names)

        self._line_value = ""
        self._calc_list = self._parameter_root['calc_list'].list
        self._column_name_list = self._parameter_root['column_names'].list

        self.same_length_res = self._parameter_root['same_length_res'].value
        self._same_length_res_gui = (
            self._parameter_root['same_length_res'].gui())

        if backend == 'matlab':
            self._matlab_path_gui = self._parameter_root['matlab_path'].gui()
            self._nojvm_gui = self._parameter_root['nojvm'].gui()

    def get_calc_line_value(self):
        return self._line_value

    def same_len_res(self):
        return self.same_length_res

    def get_same_length_res_gui(self):
        return self._same_length_res_gui

    def get_calc_list(self):
        return self._calc_list

    def get_preview_calculator(self):
        return self._preview_calculator

    def get_input(self):
        return self._in_tables

    def get_column_names(self):
        return self._column_name_list

    def get_matlab_path_gui(self):
        return self._matlab_path_gui

    def get_nojvm_gui(self):
        return self._nojvm_gui

    def set_show_func_value(self, value):
        self._parameter_root['show_func'].value = value

    def set_calc_line_value(self, value):
        self._line_value = value

    def set_calc_list(self, value):
        self._calc_list = value
        self._parameter_root['calc_list'].list = self._calc_list
