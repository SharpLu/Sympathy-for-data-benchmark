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
Part of the sympathy package.
"""
import os
import re
import socket
import copy
import functools

from . import os_support
from . import qt_compat
from . import state

QtCore = qt_compat.QtCore
QtGui = qt_compat.QtGui
from . exceptions import sywarn

from .. utils import port as port_util
from .. utils.prim import uri_to_path, nativepath
from .. utils.parameter_helper import (ParameterRoot, ParameterGroup,
                                       WidgetBuildingVisitor)
from .. utils.context import repeatcontext, PortDummy


def void(*args):
    pass


class NodeContext(object):
    def __init__(self, input, output, definition, parameters, typealiases,
                 objects=None):
        self.input = input
        self.output = output
        self.definition = definition
        self.parameters = parameters
        self.typealiases = typealiases
        self._objects = {} if objects is None else objects

    def __iter__(self):
        return iter((self.input, self.output, self.definition, self.parameters,
                    self.typealiases))

    def __len__(self):
        return sum(1 for _ in self)

    def manage_input(self, filename, fileobj):
        """
        Let the lifetime of fileobj be decided outside of the node.
        Normally, it will be more long-lived than regular inputs
        and outputs, making it possible to add inputs that need to be
        live when writeback takes place.
        """
        self._objects[filename] = fileobj

    def __enter__(self):
        return self

    def __exit__(self, *args):
        for obj in self._objects.values():
            try:
                obj.close()
            except:
                pass
        self._objects.clear()


def original(func):
    """
    Wrapper to track of if func has been overridden.
    If getattr(object.func, 'original', False) returns True, then it has been.
    """
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    inner.__name__ = func.__name__
    inner.__doc__ = func.__doc__
    inner.original = True
    return inner


def update_parameters(node, old_params):
    """
    Update parameters of old nodes using new node definition from library.
    """
    def default_params_update(definition_params, old_params):
        for key in definition_params:
            if key == 'type':
                continue
            elif (key in ('order', 'label', 'description') and
                    key in definition_params and
                    old_params.get(key) != definition_params[key]):
                old_params[key] = definition_params[key]
            elif key not in old_params:
                old_params[key] = definition_params[key]
            elif (isinstance(definition_params[key], dict) and
                    isinstance(old_params[key], dict)):
                default_params_update(definition_params[key], old_params[key])

    try:
        definition_params = node.parameters
        if isinstance(definition_params, ParameterGroup):
            definition_params = definition_params.parameter_dict

        # We need to make sure that definition parameters have correct values
        # for 'order'. The call to reorder will fix that, but does so by
        # mutating the parameter dictionary, so we make a copy of the
        # dictionary to avoid unwanted side-effects.
        definition_params = copy.deepcopy(definition_params)
        ParameterRoot(definition_params).reorder()
    except AttributeError:
        definition_params = {}

    # Node specific parameter updating if applicable.
    try:
        old_params = node.update_parameters_basic(old_params)
    except NotImplementedError:
        pass
    # And then default parameter updating.
    default_params_update(definition_params, old_params)


class BaseContextBuilder(object):
    def build(self, node, parameters, typealiases, exclude_output=False,
              exclude_input=False, read_only=False):
        """Build node context object."""
        # Creates a dictionary of typealiases with inter-references expanded.
        node_typealiases = port_util.typealiases_parser(typealiases)
        expanded_typealiases = port_util.typealiases_expander(node_typealiases)

        # Take input port definitions and convert to the required
        # structure for the node context object.
        if exclude_input:
            input_ports = []
            node_input = []
        else:
            input_ports = parameters['ports'].get('inputs', [])
            node_input = node._build_port_structure(input_ports,
                                                    expanded_typealiases,
                                                    'r')

        # Do the same for the output port. In some cases we are not
        # allowed to access the output port and this is when we set
        # the structure to None.
        if exclude_output:
            output_ports = []
            node_output = []
        else:
            # Generate output port object structure.
            output_ports = parameters['ports']['outputs']
            node_output = node._build_port_structure(
                output_ports,
                expanded_typealiases,
                'r' if read_only else 'w')

        # Users should not really need to have access to the node definition?
        node_definition = parameters

        # Copy parameter structure
        node_parameters = parameters['parameters'].get('data', {})
        update_parameters(node, node_parameters)

        # Initialize instance of NodeContext.
        return node.create_node_context(
            node_input,
            node_output,
            node_definition,
            node_parameters,
            node_typealiases.values())


class ManualContextBuilder(object):
    """
    Build node context object with the ability to supply inputs that override
    the ones provided by the parameters.  The resulting inputs and outputs are
    available for access and closing through public fields.
    """
    def __init__(self, inputs, outputs, is_output_node, port_dummies=False,
                 objects=None, check_fns=True):
        self.inputs = inputs
        self.outputs = outputs
        self.input_gens = {}
        self.output_gens = {}
        self.objects = {} if objects is None else objects
        self._port_dummies = port_dummies
        self._is_output_node = is_output_node
        self._check_fns = check_fns

    def build(self, node, parameters, typealiases, exclude_output=False,
              exclude_input=False, read_only=False):
        """Build node context object."""
        @repeatcontext
        def wrap(data):
            yield data

        # Creates a dictionary of typealiases with inter-references expanded.
        node_typealiases = port_util.typealiases_parser(typealiases)

        # Take input port definitions and convert to the required
        # structure for the node context object.
        if exclude_input:
            input_ports = []
            node_input = []
        else:
            input_ports = parameters['ports'].get('inputs', [])
            node_input = []
            for input_port in input_ports:
                filename = input_port['file']
                if self._check_fns:
                    assert(filename != '')
                data = self.inputs.get(filename)

                if data is None:
                    gen = port_util.port_generator(input_port, 'r', True,
                                                   expanded=node._expanded,
                                                   managed=node._managed)
                    try:
                        data = gen.gen.next()
                        data = data.__deepcopy__()
                        port = wrap(data)
                    except (IOError, OSError) as e:
                        # E.g. the file doesn't exist yet.
                        if self._port_dummies:
                            port = PortDummy(e)
                        else:
                            raise
                    self.input_gens[filename] = gen.gen
                    self.inputs[filename] = data
                    self.objects[filename] = data
                else:
                    port = wrap(data.__deepcopy__())
                    port.memdata = True

                node_input.append(port)

        # Do the same for the output port. In some cases we are not
        # allowed to access the output port and this is when we set
        # the structure to None.
        if exclude_output:
            output_ports = []
            node_output = []
        else:
            # Generate output port object structure.
            output_ports = parameters['ports'].get('outputs', [])
            node_output = []
            for output_port in output_ports:
                filename = output_port['file']
                if self._check_fns:
                    assert(filename != '')
                data = self.outputs.get(filename)

                if data is None:
                    if self._is_output_node:
                        gen = port_util.port_generator(output_port, 'r' if
                                                       read_only else 'w',
                                                       True,
                                                       expanded=node._expanded,
                                                       managed=node._managed)
                        self.output_gens[filename] = gen.gen
                        data = gen.gen.next()
                    else:
                        data = port_util.port_generator(output_port, None,
                                                        None,
                                                        no_datasource=True)
                    self.outputs[filename] = data
                    self.objects[filename] = data
                    port = wrap(data)

                else:
                    port = wrap(data)
                    port.memdata = True

                node_output.append(port)

        # Users should not really need to have access to the node definition?
        node_definition = parameters

        # Copy parameter structure
        node_parameters = parameters['parameters'].get('data', {})
        update_parameters(node, node_parameters)

        # Initialize instance of NodeContext.
        node_context = node.create_node_context(
            node_input,
            node_output,
            node_definition,
            node_parameters,
            node_typealiases.values(),
            self.objects)
        node_context.__exit__ = void
        return node_context


def open_server(server_address):
    """Always executed before main execution."""

    try:
        # Open new socket.
        active_socket = socket.socket(socket.AF_INET,
                                      socket.SOCK_STREAM)

        (address, port) = server_address.split(':')

        active_socket.connect((address, int(port)))
        active_socket.setblocking(0)
        active_file = active_socket.makefile('rb')
        return (active_socket, active_file)
    except IOError:
        sywarn('Could not establish socket connection '
               'between node and platform')
        return (None, None)


def close_server(server):
    """Always executed after main execution."""
    active_socket, active_file = server

    try:
        if active_file is not None:
            active_file.close()
    except IOError:
        pass

    try:
        if active_socket is not None:
            active_socket.close()
    except IOError:
        pass


class ParametersDialog(QtGui.QDialog):
    def __init__(self, parameters_changed=None, *args, **kwargs):
        super(ParametersDialog, self).__init__(*args, **kwargs)
        if parameters_changed is None:
            self._parameters_changed = lambda: False
        else:
            self._parameters_changed = parameters_changed
        self._widget = None
        self.accepted.connect(self._save_parameters)

    def set_configuration_widget(self, widget):
        self._widget = widget

    def keyPressEvent(self, event):
        # Only accept Ctrl+Enter as Ok and Esc as Cancel.
        # This is to avoid closing the dialog by accident.
        if ((event.key() == QtCore.Qt.Key_Return or
                event.key() == QtCore.Qt.Key_Enter) and
                event.modifiers() & QtCore.Qt.ControlModifier):
            self.accept()
        elif event.key() == QtCore.Qt.Key_Escape:
            self.reject_or_accept()

    def closeEvent(self, event):
        if not self.reject_or_accept():
            event.ignore()
        else:
            if (self._widget is not None and
                    hasattr(self._widget, 'sy_cleanup')):
                # Currently undocumented/unsupported API.
                self._widget.sy_cleanup()

    def _save_parameters(self):
        if (self._widget is not None and
                hasattr(self._widget, 'save_parameters')):
            self._widget.save_parameters()

    def reject_or_accept(self):
        """
        Ask the user if the dialog should be closed. Return True if the dialog
        should be closed.
        """
        # First notify the widget that it should save its parameters.
        self._save_parameters()
        if not self._parameters_changed():
            self.reject()
            return True

        choice = QtGui.QMessageBox.question(
            self, u'Save changes to configuration',
            "The node's configuration has changed. Save changes in node?",
            QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard |
            QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)

        if choice == QtGui.QMessageBox.Discard:
            self.reject()
            return True
        elif choice == QtGui.QMessageBox.Save:
            self.accept()
            return True
        else:
            return False


class BasicNode(object):
    """
    Base class for Sympathy nodes. Fully implements the
    language interface needed to work as a fully functional
    node inside the Sympathy platform. All Python2 nodes
    should extend this class.
    """

    def __init__(self):
        self.active_socket = None
        self.active_file = None
        self.address = None
        self.abort_flag = False
        self.filenames = []
        self._requested_filenames = None
        self._expanded = True
        self._managed = False

    def set_progress(self, value):
        """Set and send progress to main program."""

        if self.active_socket is not None:
            msg = 'PROGRESS %f\n' % float(value)
            try:
                self.active_socket.send(msg)
            except socket.error:
                pass

    def set_status(self, status):
        """Send status message to main program."""

        if self.active_socket is not None:
            msg = 'STATUS %s\n' % status
            try:
                self.active_socket.send(msg)
            except socket.error:
                pass

    def _sys_process_messages(self):
        """Process messages from server."""

        if self.active_file is not None:
            try:
                for msg in self.active_file:
                    msg = msg.rstrip()
                    if msg == "ABORT":
                        self.abort_flag = True
                    elif msg.startswith("FILENAMES"):
                        self.filenames = msg[10:].split(",")

            except socket.error:
                pass

    def check_abort(self):
        """
        Check if server has sent an abort message.
        Returns True if an abort message was sent.
        """
        self._sys_process_messages()
        return self.abort_flag

    def request_filenames(self, portname, filename_count,
                          filename_suffix='h5'):
        """Get file names for a specific port from platform."""
        if self.active_socket is not None:
            self.active_socket.send(
                'FILENAMES %s %d %s\n' % (portname,
                                          int(filename_count),
                                          filename_suffix))
            # Blocking.
            while len(self.filenames) != filename_count:
                self._sys_process_messages()
            self._requested_filenames = self.filenames
            self.filenames = []
            return self._requested_filenames

    # Methods to be overidden by user.
    @original
    def verify_parameters_basic(self, node_context):
        """Check if configuration is ok."""
        return True

    def update_parameters_basic(self, old_params):
        """
        Update parameters to newer version of node.
        Returns updated parameters.
        """
        raise NotImplementedError(
            'update_parameters() has no default implementation')

    def adjust_parameters_basic(self, node_context):
        """Adjust parameter object."""
        # Default to no changes.
        return node_context

    def custom_parameters_basic(self, node_context):
        """Override to create custom parameters."""
        return None

    def execute_basic(self, node_context):
        """
        Execute node. This method should always be extended by
        the inhereting class.
        """
        raise NotImplementedError('execute() must be implemented')

    def available_components(self):
        """
        Return a list of available visual components which the node
        can visualize things through.
        """
        return []

    def exec_parameter_view_basic(self, node_context):
        """
        Return parameter dictionary which was edited by the
        user. Accept and reject is handled by the platform.
        """
        raise NotImplementedError('Specialized class must be '
                                  'used for parameter view.')

    def _manual_context(self, node_context):
        # Used for enabling the user to close the context afterwards.
        # In this base class the close function, int, does nothing and is used
        # as an empty close action since the base behavior is manual
        # context management.
        close_function = int
        close_handles = {'inputs': {key: close_function
                                    for key in node_context.input},
                         'outputs': {key: close_function
                                     for key in node_context.output}}
        return node_context, close_handles

    def _execute_parameter_view(self, node_context, parameters_changed=None,
                                return_widget=False):
        dialog = None
        try:
            if not return_widget:
                try:
                    application = QtGui.QApplication([])
                except RuntimeError:
                    application = QtGui.QApplication.instance()
                dialog = ParametersDialog(parameters_changed)

                # Don't put newlines or other bad white spaces in window title
                app_name = re.sub(
                    r"\s+", u" ", node_context.definition['label'],
                    flags=re.UNICODE)
                name = u'{} - Parameter View'.format(app_name)
                application.setApplicationName(name)

            icon = node_context.definition.get('icon', None)
            if icon:
                try:
                    icon_data = QtGui.QIcon(uri_to_path(icon))
                except Exception as e:
                    print e
                if not return_widget:
                    application.setWindowIcon(QtGui.QIcon(icon_data))

            if not return_widget:
                layout = QtGui.QVBoxLayout()
                button_box = QtGui.QDialogButtonBox()
                help_button = button_box.addButton(QtGui.QDialogButtonBox.Help)
                ok_button = button_box.addButton(QtGui.QDialogButtonBox.Ok)
                cancel_button = button_box.addButton(
                    QtGui.QDialogButtonBox.Cancel)
                ok_button.setDefault(False)

            if hasattr(self, 'execute_parameter_view'):
                sywarn('Overriding execute_parameter_view '
                       'is no longer supported.')

            if (hasattr(self, 'has_parameter_view') or
                    hasattr(self, 'has_parameter_view_managed')):
                sywarn('Implementing has_parameter_view or '
                       'has_parameter_view_managed no '
                       'longer has any effect.')

            try:
                widget = self.exec_parameter_view_basic(node_context)
            except NotImplementedError:
                custom = self.custom_parameters_basic(node_context)
                handler, visitor = (custom if custom is not None
                                    else (None, WidgetBuildingVisitor))
                handler_i = handler() if handler is not None else handler
                proot = ParameterRoot(node_context.parameters, handler_i)
                widget_builder = visitor()
                proot.accept(widget_builder)
                widget = widget_builder.gui()
                # Controller support.
                controllers = getattr(self, 'controllers', None)
                if controllers is not None:
                    widget_dict = widget_builder.widget_dict()
                    try:
                        for controller in controllers:
                            controller.connect(widget_dict)
                    except TypeError:
                        controllers.connect(widget_dict)

            if not return_widget:
                # reducing white space around widgets
                widget.setContentsMargins(0, 0, 0, 0)
                widget.layout().setContentsMargins(0, 0, 0, 0)
                layout.addWidget(widget)
                layout.addWidget(button_box)
                dialog.set_configuration_widget(widget)
                dialog.setLayout(layout)
                dialog.setWindowFlags(QtCore.Qt.Window)

                help_button.clicked.connect(functools.partial(
                    self._open_node_documentation, node_context))
                ok_button.clicked.connect(dialog.accept)
                cancel_button.clicked.connect(dialog.reject_or_accept)

                dialog.setWindowTitle(name)
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
                QtCore.QTimer.singleShot(0, focus_widget(dialog))
                application.exec_()
                return dialog.result()
            else:
                return widget
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            # Ensure GC
            dialog = None

    def _sys_exec_parameter_view(self, parameters, type_aliases,
                                 return_widget=False,
                                 builder=BaseContextBuilder()):
        """Execute parameter view and return any changes."""
        # Remember old parameters.
        old = copy.deepcopy(parameters)

        adjusted_parameters = self._sys_adjust_parameters(parameters,
                                                          type_aliases,
                                                          builder=builder)

        node_context = self._build_node_context(adjusted_parameters,
                                                type_aliases,
                                                exclude_output=True,
                                                builder=builder)

        settings = state.node_state().attributes['settings']
        confirm_cancel = settings['Gui/nodeconfig_confirm_cancel']
        if confirm_cancel and not return_widget:
            adjusted_parameters_copy = copy.deepcopy(
                adjusted_parameters['parameters']['data'])

            # Save parameters in a closure so that ParameterDialog can check
            # them.
            def parameters_changed():
                return adjusted_parameters_copy != node_context.parameters
        else:
            parameters_changed = None

        result = self._execute_parameter_view(
            node_context, parameters_changed=parameters_changed,
            return_widget=return_widget)
        if return_widget:
            # In this case the result from self.exec_parameter_view is the
            # configuration widget
            return result
        elif result == QtGui.QDialog.Accepted:
            return adjusted_parameters
        else:
            return old

    def exec_port_viewer(self, parameters):
        from viewer import MainWindow as ViewerWindow
        try:
            try:
                application = QtGui.QApplication([])
            except RuntimeError:
                application = QtGui.QApplication.instance()
            viewer = ViewerWindow()
            viewer.open_from_filename(parameters)

            viewer.show()
            viewer.raise_()
            viewer.activateWindow()
            QtCore.QTimer.singleShot(0, focus_widget(viewer))
            application.exec_()
        finally:
            viewer = None

    def _sys_set_server(self, server):
        self.active_socket, self.active_file = server

    def _sys_before_execute(self, server_address):
        """Always executed before main execution."""
        self._sys_set_server(open_server(server_address))

    def _sys_execute(self, parameters, type_aliases,
                     builder=BaseContextBuilder()):
        """Called by the Sympathy platform when executing a node."""
        node_context = self._build_node_context(parameters, type_aliases,
                                                builder=builder)

        self.execute_basic(node_context)

        # Ensure all files were created
        if self._requested_filenames is not None:
            for requested_filename in self._requested_filenames:
                if not os.path.isfile(requested_filename):
                    raise IOError("All requested files weren't created")

    def _sys_after_execute(self):
        """Always executed after main execution."""
        close_server((self.active_socket, self.active_file))
        self._sys_set_server((None, None))

    def _sys_verify_parameters(self, parameters, type_aliases):
        """Check if parameters are valid."""
        node_context = self._build_node_context(parameters,
                                                type_aliases,
                                                exclude_output=True,
                                                exclude_input=True)
        try:
            return self.verify_parameters_basic(node_context)
        except:
            sywarn('Error in validate_parameters, input data should not be'
                   ' used for validation.')
            return False

    def _sys_adjust_parameters(self, parameters, type_aliases,
                               builder=BaseContextBuilder()):
        """Adjust node parameters."""
        adjusted_parameters = copy.deepcopy(parameters)
        node_context = self._build_node_context(adjusted_parameters,
                                                type_aliases,
                                                exclude_output=True,
                                                builder=builder)
        self.adjust_parameters_basic(node_context)
        return adjusted_parameters

    def _build_node_context(self, parameters, typealiases,
                            exclude_output=False,
                            exclude_input=False,
                            read_only=False,
                            builder=BaseContextBuilder()):
        """Build node context object."""
        return builder.build(self, parameters, typealiases,
                             exclude_output=exclude_output,
                             exclude_input=exclude_input,
                             read_only=read_only)

    def _build_port_structure(self, port_info, typealiases, mode):
        return [
            port_util.port_generator(value, mode, True,
                                     expanded=self._expanded,
                                     managed=self._managed)
            for value in port_info]

    @staticmethod
    def create_node_context(inputs, outputs, definition, parameters,
                            typealiases, objects=None):
        objects = {} if objects is None else objects
        input_ports = definition['ports'].get('inputs', [])
        output_ports = definition['ports'].get('outputs', [])

        return NodeContext(port_util.RunPorts(inputs,
                                              input_ports),
                           port_util.RunPorts(outputs,
                                              output_ports),
                           definition,
                           parameters,
                           typealiases,
                           objects)

    @classmethod
    def update_node_context(cls, node_context, inputs, outputs,
                            parameters=None):
        if parameters is None:
            parameters = node_context.parameters
        return cls.create_node_context(
            inputs, outputs, node_context.definition,
            parameters, node_context.typealiases, node_context._objects)

    def _open_node_documentation(self, node_context):
        path_in_library = os.path.dirname(os.path.relpath(
            uri_to_path(node_context.definition['source_file']),
            uri_to_path(node_context.definition['library'])))
        doc_path = nativepath(os.path.join(
            os.environ['SY_STORAGE'], 'doc', 'html', 'src', 'Library',
            path_in_library, self.__class__.__name__ + '.html'))

        if os.path.exists(doc_path):
            doc_url_ = QtCore.QUrl.fromLocalFile(doc_path)
            doc_url_.setScheme('file')
            QtGui.QDesktopServices.openUrl(doc_url_)
        else:
            QtGui.QMessageBox.warning(
                None, u"Documentation not available",
                u"No documentation available. Please use the option "
                u"'Create documentation' in the 'Help' menu of Sympathy to "
                u"create the documentation.")


def focus_widget(dialog):
    def inner():
        os_support.focus_widget(dialog)
    return inner
