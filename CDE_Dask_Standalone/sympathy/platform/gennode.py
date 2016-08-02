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
from collections import OrderedDict

from . import basicnode as synode
from .. utils.context import with_managers
from .. utils.parameter_helper import ParameterRoot
from . controller import Controller, Field


class Editor(object):
    def __init__(self, editor1=None, editor2=None):
        self.attr = OrderedDict()
        if editor1 is not None:
            self.attr.update(editor1.attr)
        if editor2 is not None:
            self.attr.update(editor2.attr)

    def set_type(self, etype):
        self.attr['type'] = etype

    def set_attribute(self, attribute, value):
        self.attr[attribute] = value

    def value(self):
        return self.attr


class Util(object):
    @staticmethod
    def bounded_editor(min_, max_):
        editor = Editor()
        editor.set_attribute('min', min_)
        editor.set_attribute('max', max_)
        return editor

    @staticmethod
    def decimal_editor(decimals):
        editor = Editor()
        editor.set_attribute('decimals', decimals)
        return editor

    @staticmethod
    def selection_editor(selection):
        editor = Editor()
        editor.set_attribute('selection', selection)
        return editor

    @staticmethod
    def lineedit_editor(placeholder=None):
        editor = Editor()
        editor.set_type('lineedit')
        if placeholder is not None:
            editor.set_attribute('placeholder', placeholder)
        return editor

    @staticmethod
    def bounded_lineedit_editor(min_, max_, placeholder=None):
        return Editor(Util.lineedit_editor(placeholder),
                      Util.bounded_editor(min_, max_))

    @staticmethod
    def spinbox_editor(step):
        editor = Editor()
        editor.set_type('spinbox')
        editor.set_attribute('step', step)
        return editor

    @staticmethod
    def bounded_spinbox_editor(min_, max_, step):
        editor = Editor(
            Util.spinbox_editor(step), Util.bounded_editor(min_, max_))
        return editor

    @staticmethod
    def decimal_spinbox_editor(step, decimals):
        editor = Editor(
            Util.spinbox_editor(step), Util.decimal_editor(decimals))
        return editor

    @staticmethod
    def bounded_decimal_spinbox_editor(min_, max_, step, decimals):
        editor = Editor(
            Util.bounded_spinbox_editor(min_, max_, step),
            Util.decimal_editor(decimals))
        return editor

    @staticmethod
    def filename_editor(filter_pattern=None):
        editor = Editor()
        editor.set_type('filename')
        editor.set_attribute('filter', filter_pattern or ['Any files (*)'])
        return editor

    @staticmethod
    def directory_editor():
        editor = Editor()
        editor.set_type('dirname')
        return editor

    @staticmethod
    def list_editor():
        editor = Editor()
        editor.set_type('listview')
        return editor

    @staticmethod
    def basic_list_editor():
        editor = Editor()
        editor.set_type('basiclist')
        return editor

    @staticmethod
    def selectionlist_editor(selection):
        editor = Editor(Util.list_editor(), Util.selection_editor(selection))
        return editor

    @staticmethod
    def combo_editor():
        editor = Editor()
        editor.set_type('combobox')
        return editor


def managed_context(function):
    """
    Decorator function used to provide automatic management of node_context
    input and output fields.

    When using a managed context the input and output fields will contain the
    value yielded by the generator instead of the generator itself.
    """
    def adapt(self, node_context, managers, **kwargs):
        """Adapter for running node function using 'with_managers'."""
        # Splitting inputs and outputs.
        length = len(node_context.input)
        inputs = managers[:length]
        outputs = managers[length:]

        managed_node_context = self.update_node_context(
            node_context, inputs, outputs,
            parameters(node_context.parameters))

        managed_node_context._objects = node_context._objects

        return function(
            self,
            managed_node_context,
            **kwargs)

    def wrapper(self, node_context, **kwargs):
        """
        The managers list argument contain both input and output, in the
        same list. The reason for this is the interface of with_managers.
        The input elements will be first and the output elements last.
        """
        def runner(managers):
            return adapt(self, node_context, managers, **kwargs)

        result = with_managers(runner,
                               list(node_context.input) +
                               list(node_context.output))
        node_context.__exit__()
        return result

    wrapper.function = function
    return wrapper


class BasicNode(synode.BasicNode):
    def __init__(self):
        super(BasicNode, self).__init__()


class Node(BasicNode):
    def __init__(self):
        super(Node, self).__init__()
        self._managed = True
        self._expanded = False

    def _manual_context(self,  node_context):
        # Rebuild input and output.
        close_handles = {
            'input': [
                value.close
                for value in node_context.input],
            'output': [
                value.close
                for value in node_context.output]}

        return (node_context, close_handles)

    # Methods to be overidden by user for manual node context management.
    @synode.original
    @managed_context
    def verify_parameters_basic(self, node_context):
        return self.verify_parameters(node_context)

    @managed_context
    def adjust_parameters_basic(self, node_context):
        return self.adjust_parameters(node_context)

    def custom_parameters_basic(self, node_context):
        return self.custom_parameters(node_context)

    def update_parameters_basic(self, old_params):
        params = parameters(old_params)
        self.update_parameters(params)
        return params.parameter_dict

    @managed_context
    def execute_basic(self, node_context):
        return self.execute(node_context)

    def exec_parameter_view_basic(self, node_context):
        return self.exec_parameter_view(node_context)

    @managed_context
    def _execute_parameter_view(self, node_context, parameters_changed=None,
                                return_widget=False):
        return super(Node, self)._execute_parameter_view(
            node_context, parameters_changed, return_widget)

    #   Methods to be overidden by user
    @synode.original
    def verify_parameters(self, node_context):
        return super(Node, self).verify_parameters_basic(node_context)

    def adjust_parameters(self, node_context):
        return super(Node, self).adjust_parameters_basic(node_context)

    def custom_parameters(self, node_context):
        return super(Node, self).custom_parameters_basic(node_context)

    def update_parameters(self, old_params):
        return super(Node, self).update_parameters_basic(old_params)

    def execute(self, node_context):
        return super(Node, self).execute_basic(node_context)

    def exec_parameter_view(self, node_context):
        return super(Node, self).exec_parameter_view_basic(node_context)


class ManagedNode(Node):
    """
    This class is still around as an option for writing nodes that are
    backwards compatible with 1.2.
    """

    def __init__(self, *args, **kwargs):
        super(ManagedNode, self).__init__(*args, **kwargs)

    @synode.original
    @managed_context
    def verify_parameters_basic(self, node_context):
        return self.verify_parameters_managed(node_context)

    @managed_context
    def adjust_parameters_basic(self, node_context):
        return self.adjust_parameters_managed(node_context)

    def custom_parameters_basic(self, node_context):
        return self.custom_parameters_managed(node_context)

    def update_parameters_basic(self, old_params):
        params = parameters(old_params)
        self.update_parameters_managed(params)
        return params.parameter_dict

    @managed_context
    def execute_basic(self, node_context):
        return self.execute_managed(node_context)

    def exec_parameter_view_basic(self, node_context):
        return self.exec_parameter_view_managed(node_context)

    @managed_context
    def _execute_parameter_view(self, node_context, parameters_changed=None,
                                return_widget=False):
        return super(Node, self)._execute_parameter_view(
            node_context, parameters_changed, return_widget)

    #   Methods to be overidden by user
    @synode.original
    def verify_parameters_managed(self, node_context):
        return super(Node, self).verify_parameters_basic(node_context)

    def adjust_parameters_managed(self, node_context):
        return super(Node, self).adjust_parameters_basic(node_context)

    def update_parameters_managed(self, old_params):
        return super(Node, self).update_parameters_basic(old_params)

    def custom_parameters_managed(self, node_context):
        return super(Node, self).custom_parameters_basic(node_context)

    def execute_managed(self, node_context):
        return super(Node, self).execute_basic(node_context)

    def exec_parameter_view_managed(self, node_context):
        return super(Node, self).exec_parameter_view_basic(node_context)


parameters = ParameterRoot
controller = Controller
field = Field
