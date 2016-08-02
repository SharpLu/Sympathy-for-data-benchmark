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
"""Apply function(s) on Table(s)."""
import os.path
import itertools

from sympathy.platform import qt_compat
QtGui = qt_compat.import_module('QtGui') # noqa
QtCore = qt_compat.QtCore # noqa
from sympathy.platform import gennode
from sympathy.api import table
from sympathy.api.exceptions import SyDataError, SyConfigurationError
from sympathy.api.nodeconfig import Tag, Tags
from . function_selector import PyfileWrapper


def mock_wrap(cls):
    """
    For avoiding problems related to subclassing mocked class.
    This is used for being able to import modules without having the imports
    installed.
    See http://www.voidspace.org.uk/python/mock/.
    """
    return cls if isinstance(cls, type) else cls()


def functions_filename(datasource):
    """Returns file datasource filename."""
    path = datasource.decode_path()
    if path:
        return os.path.abspath(unicode(path))


@mock_wrap
class FunctionSelectorGui(QtGui.QWidget):
    def __init__(self, node_context, parent=None):
        super(FunctionSelectorGui, self).__init__(parent)
        self._node_context = node_context
        self._parameters = node_context.parameters
        self._init_gui()

    def _init_gui(self):
        self._clean = self._parameters['clean_output'].gui()
        self._functions = self._parameters['selected_functions'].gui()
        self._edit = QtGui.QPushButton('Edit source file')
        self._edit.setToolTip(
            'Brings up the source file in the system default editor')
        self._edit.setEnabled(self._node_context.input['port1'].is_valid())
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self._clean)
        layout.addWidget(self._functions)
        layout.addWidget(self._edit)
        self.setLayout(layout)
        self._edit.clicked[bool].connect(self._edit_source)

    @qt_compat.Slot(bool)
    def _edit_source(self, checked):
        fq_functions_filename = functions_filename(
            self._node_context.input['port1'])
        url = QtCore.QUrl.fromLocalFile(fq_functions_filename)
        url.setScheme('file')
        QtGui.QDesktopServices.openUrl(url)


class FunctionSelectorGuiList(FunctionSelectorGui):
    def __init__(self, node_context, parent=None):
        super(FunctionSelectorGuiList, self).__init__(node_context, parent)

    def _init_gui(self):
        super(FunctionSelectorGuiList, self)._init_gui()

        self._same_length_res = self._parameters['same_length_res'].gui()
        if not self._parameters['clean_output'].value:
            self._same_length_res.setEnabled(False)

        self._clean.stateChanged[int].connect(self._clean_changed)
        self.layout().insertWidget(
            0, self._same_length_res)

    def _clean_changed(self, checked):
        if checked == QtCore.Qt.CheckState.Checked:
            self._same_length_res.setEnabled(True)
        else:
            self._same_length_res.setEnabled(False)


def _super_node_parameters():
    parameters = gennode.parameters()
    editor = gennode.Util.selectionlist_editor('multi').value()
    editor['filter'] = True
    editor['buttons'] = True
    editor['passthrough'] = True
    parameters.set_boolean(
        'clean_output', value=True, label='Clean output',
        description='Do not copy the input data to the output.')
    parameters.set_list(
        'selected_functions', value=[], label='Select functions',
        description='Select the functions to apply.', editor=editor)
    return parameters


class SuperNode(object):
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2012 System Engineering Software Society"
    version = '1.0'
    icon = 'function_selector.svg'
    parameters = _super_node_parameters()
    tags = Tags(Tag.DataProcessing.Calculate)


class SuperNodeList(SuperNode):
    parameters = _super_node_parameters()
    parameters.set_boolean(
        'same_length_res', label='Put results in common outputs',
        value=True,
        description=(
            'Use this checkbox if you want to gather all the results '
            'generated from an incoming Table into a common output. '
            'This requires that the results will all have the same '
            'length. An exception will be raised if the lengths of '
            'the outgoing results differ.'))

    def update_parameters(self, old_params):
        # Old nodes without the same_length_res option work the same way as if
        # they had the option, set to False.
        if 'same_length_res' not in old_params:
            old_params['same_length_res'] = self.parameters['same_length_res']
            old_params['same_length_res'].value = False


class FunctionSelectorBase(object):
    def __init__(self, wrapper_class, in_filetype, out_filetype=None):
        super(FunctionSelectorBase, self).__init__()
        self._wrapper_class = wrapper_class
        self._in_filetype = in_filetype
        if out_filetype is None:
            self._out_filetype = self._in_filetype
        else:
            self._out_filetype = out_filetype

    def exec_parameter_view(self, node_context):
        return FunctionSelectorGui(node_context)

    def adjust_parameters(self, node_context):
        """Adjust parameters"""
        parameters = node_context.parameters
        if node_context.input['port1'].is_valid():
            fq_functions_filename = functions_filename(
                node_context.input['port1'])
            self._pyfile_wrapper = PyfileWrapper(
                fq_functions_filename, base_class=self._wrapper_class)
            function_names = self._pyfile_wrapper.function_names()
        else:
            function_names = parameters['selected_functions'].value_names
        parameters['selected_functions'].list = function_names
        parameters['selected_functions'].value_names = list(
            set(function_names).intersection(
                set(parameters['selected_functions'].value_names)))
        return node_context

    def execute_single(self, node_context, set_progress=None):
        in_datafile = node_context.input['port2']
        parameters = node_context.parameters
        fq_functions_filename = functions_filename(node_context.input['port1'])
        passthrough = parameters['selected_functions'].passthrough
        clean_output = parameters['clean_output'].value
        out_datafile = node_context.output['port3']
        if 'extra' in node_context.input:
            extra_input = node_context.input['extra']
        else:
            extra_input = None

        self._pyfile_wrapper = PyfileWrapper(
            fq_functions_filename, base_class=self._wrapper_class)

        if not clean_output:
            out_datafile.source(in_datafile)

        self.apply_selected_functions(
            fq_functions_filename,
            parameters['selected_functions'].value_names,
            in_datafile, out_datafile, extra_input,
            passthrough=passthrough, set_progress=set_progress)

    def execute_multiple(self, node_context, set_progress=None):
        input_list = node_context.input['port2']
        if len(input_list) == 0:
            return
        parameters = node_context.parameters
        fq_functions_filename = functions_filename(node_context.input['port1'])
        passthrough = parameters['selected_functions'].passthrough
        clean_output = parameters['clean_output'].value
        output_list = node_context.output['port3']

        same_length_res = parameters['same_length_res'].value

        if 'extra' in node_context.input:
            extra_input = node_context.input['extra']
            if isinstance(node_context.input['extra'], table.File):
                iterator = itertools.izip(
                    input_list, itertools.repeat(extra_input))
            else:
                iterator = itertools.izip(input_list, extra_input)
        else:
            iterator = itertools.izip(input_list, itertools.repeat(None))
            extra_input = None

        self._pyfile_wrapper = PyfileWrapper(
            fq_functions_filename, base_class=self._wrapper_class)

        function_names = self._pyfile_wrapper.function_names()
        functions_to_apply = parameters['selected_functions'].value_names
        if passthrough:
            functions_to_apply = function_names
        else:
            functions_to_apply = [f for f in functions_to_apply
                                  if f in function_names]
        class_list = [self._pyfile_wrapper.get_class(fname)
                      for fname in functions_to_apply]
        multiple_functions = [c for c in class_list if c.list_wrapper]
        single_functions = [c for c in class_list if not c.list_wrapper]

        number_of_inputs = len(input_list)
        calc_count = float(
            number_of_inputs * (len(multiple_functions) +
                                len(single_functions))) / 100.0
        index = 0
        if clean_output:
            for function in multiple_functions:
                with self._out_filetype.FileList() as temp_list:
                    try:
                        instance = function(input_list, temp_list, extra_input)
                    except:
                        instance = function(input_list, temp_list)
                    instance.execute()
                    index += number_of_inputs
                    output_list.extend(temp_list)
                    set_progress(index / calc_count)

            if same_length_res:
                out_datafile = self._out_filetype.File()
                for in_datafile, extra in iterator:
                    has_functions = False
                    for function in single_functions:
                        has_functions = True

                        try:
                            instance = function(in_datafile, out_datafile,
                                                extra)
                        except:
                            instance = function(in_datafile, out_datafile)
                        instance.execute()
                        index += 1
                        set_progress(index / calc_count)

                    if has_functions:
                        output_list.append(out_datafile)
            else:
                for in_datafile, extra in iterator:
                    for function in single_functions:
                        out_datafile = self._out_filetype.File()

                        try:
                            instance = function(in_datafile, out_datafile,
                                                extra)
                        except:
                            instance = function(in_datafile, out_datafile)
                        instance.execute()
                        index += 1
                        set_progress(index / calc_count)

                        output_list.append(out_datafile)
        else:
            if self._out_filetype is not self._in_filetype:
                raise SyConfigurationError(
                    "Input and output types differ. "
                    "Please use the 'Clean output' option.")
            if multiple_functions:
                raise SyDataError(
                    "Multiple functions such as TablesWrapper or "
                    "ADAFsWrapper can only be used with the "
                    "'Clean output' option.")

            for in_datafile, extra in iterator:
                out_datafile = self._out_filetype.File()
                out_datafile.source(in_datafile)
                for function in single_functions:
                    try:
                        instance = function(in_datafile, out_datafile, extra)
                    except:
                        instance = function(in_datafile, out_datafile)
                    instance.execute()
                    index += 1
                    set_progress(index / calc_count)
                output_list.append(out_datafile)

    def apply_selected_functions(self, fq_functions_filename,
                                 functions_to_apply,
                                 in_datafile, out_datafile, extra,
                                 passthrough=False, set_progress=None):
        """Applies selected functions on the input file."""
        if not set_progress:
            set_progress = lambda x: None
        self._pyfile_wrapper = PyfileWrapper(
            fq_functions_filename, base_class=self._wrapper_class)

        function_names = self._pyfile_wrapper.function_names()
        if passthrough:
            functions_to_apply = function_names
        else:
            functions_to_apply = list(
                set(function_names).intersection(set(functions_to_apply)))
        for i, fname in enumerate(functions_to_apply):
            set_progress(100.0 * i / len(functions_to_apply))
            class_ = self._pyfile_wrapper.get_class(fname)
            try:
                instance = class_(in_datafile, out_datafile, extra)
            except:
                instance = class_(in_datafile, out_datafile)
            instance.execute()


class FunctionSelectorBaseList(FunctionSelectorBase):

    def exec_parameter_view(self, node_context):
        return FunctionSelectorGuiList(node_context)
