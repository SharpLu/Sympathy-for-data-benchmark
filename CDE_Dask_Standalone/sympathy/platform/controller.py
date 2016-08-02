import sys

from sympathy.platform import qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module('QtGui')

from sympathy.utils.parameter_helper import ParameterRoot
from sympathy.utils.parameter_helper_visitors import WidgetBuildingVisitor


class Field(object):
    def __init__(self, name, state):
        self._name = name
        self._state = state

    def signal(self, widget_dict):
        signal_name_dict = {'checked': ('stateChanged', int)}
        signal_name, signal_type = signal_name_dict[self._state]
        signal_no_type = getattr(widget_dict[self._name], signal_name)
        if signal_no_type is not None:
            signal = signal_no_type[signal_type]
        else:
            signal = signal_no_type
        return signal

    def slot(self, widget_dict, init_value=None):
        slot_name_dict = {
            'enabled': 'set_enabled',
            'disabled': 'set_disabled',
            'visible': 'set_visible'
        }
        slot_name = slot_name_dict[self._state]
        slot = getattr(widget_dict[self._name], slot_name)
        if init_value is not None:
            slot(init_value)
        return slot


class Controller(object):
    def __init__(self, when=None, action=None, function=None):
        # assert(when is not None and action is not None)
        self._when = when
        self._action = action
        self._function = function

    def connect(self, widget_dict):
        if self._when is not None and self._action is not None:
            self._connect_when_action(widget_dict)
        elif self._function is not None:
            self._connect_function(widget_dict)
        else:
            raise NotImplementedError('Not a valid controller choice.')

    def _connect_function(self, widget_dict):
        self._function(widget_dict)

    def _connect_when_action(self, widget_dict):
        init_value = widget_dict[self._when._name]._parameter_value.value
        try:
            for action in self._action:
                self._when.signal(widget_dict).connect(
                    action.slot(widget_dict, init_value))
        except TypeError:
            self._when.signal(widget_dict).connect(
                self._action.slot(widget_dict, init_value))


class ParameterLayoutObject(object):
    def __init__(self):
        pass


def main():
    from sympathy.api import node as synode

    app = QtGui.QApplication(sys.argv)

    def controller_logic(widget_dict):
        widget_dict['use_regex'].stateChanged[int].connect(
            widget_dict['filename3'].set_enabled)

    def list_logic(widget_dict):
        vlayout = QtGui.QVBoxLayout()
        base = QtGui.QWidget()
        base.setLayout(widget_dict['list'].layout())
        button_widget = QtGui.QPushButton('Add')
        lineedit_widget = QtGui.QLineEdit()
        vlayout.addWidget(lineedit_widget)
        vlayout.addWidget(base)
        vlayout.addWidget(button_widget)
        widget_dict['list'].setLayout(vlayout)

        def add_item():
            text = lineedit_widget.text()
            widget_dict['list'].editor().addItems([text])
            print widget_dict['list']._parameter_list.list

        button_widget.clicked.connect(add_item)

    controllers = (
        Controller(
            when=Field('use_regex', state='checked'),
            action=(
                Field('filename', state='enabled'),
                Field('filename2', state='visible')
            )
        ),
        Controller(
            function=controller_logic
        ),
        Controller(
            function=list_logic
        )
    )
    pg = ParameterRoot({})
    pg.set_boolean(
        'use_regex', label='RegEx', description='Use regular expressions.')
    pg.set_string('filename', label='Filename', description='A filename.')
    pg.set_string('filename2', label='Filename', description='A filename.')
    pg.set_string('filename3', label='Filename', description='A filename.')
    pg.set_list(
        'list', label='List', description='A filename.', value=[], plist=[],
        editor=synode.Util.basic_list_editor().value()
    )

    visitor = WidgetBuildingVisitor()
    pg.accept(visitor)
    widget_dict = visitor.widget_dict()
    print widget_dict

    for controller in controllers:
        controller.connect(widget_dict)

    # print pg
    widget = visitor.gui()
    widget.show()
    app.exec_()


if __name__ == '__main__':
    main()
