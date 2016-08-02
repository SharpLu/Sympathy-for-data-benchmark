# Copyright (c) 2016, System Engineering Software Society
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
import re

import numpy as np
from matplotlib import colors as mpl_colors

from sympathy.api import qt
from sylib.figure import colors

QtCore = qt.QtCore
QtGui = qt.QtGui


class SyMPLTextEdit(QtGui.QTextEdit):
    def __init__(self, *args, **kwargs):
        super(SyMPLTextEdit, self).__init__(*args, **kwargs)
        self.setTabChangesFocus(True)
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Fixed)
        self.setFixedHeight(self.sizeHint().height())

        self._completer = None

    def keyPressEvent(self, event):
        # always ignore return and enter keys
        if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            event.ignore()
            return

        if (self._completer and self._completer.popup() and
                self._completer.popup().isVisible()):
            # The following keys are forwarded by the completer to teh widget
            if event.key() in [QtCore.Qt.Key_Enter,
                               QtCore.Qt.Key_Return,
                               QtCore.Qt.Key_Escape,
                               QtCore.Qt.Key_Tab,
                               QtCore.Qt.Key_Backtab]:
                event.ignore()
                return

        # check the shortcut combination Ctrl+R
        is_shortcut = (event.modifiers() == QtCore.Qt.ControlModifier and
                       event.key() == QtCore.Qt.Key_R)

        if not self._completer or not is_shortcut:
            super(SyMPLTextEdit, self).keyPressEvent(event)

        no_text = event.text() == ''
        ctrl_or_shift = event.modifiers() in (QtCore.Qt.ControlModifier,
                                              QtCore.Qt.ShiftModifier)
        if ctrl_or_shift and no_text:
            # ctrl or shift key on it's own
            return

        if not is_shortcut:
            if self._completer.popup() and self._completer.popup().isVisible():
                self._completer.popup().hide()

        completion_prefix = self.test_under_cursor()

        # only start if at lest one letter is typed
        if len(completion_prefix) > 0:
            self._completer.setCompletionPrefix(completion_prefix)
            popup = self._completer.popup()
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
            cr = self.cursorRect()
            cr.setWidth(self._completer.popup().sizeHintForColumn(0) +
                        self._completer.popup().verticalScrollBar().sizeHint().width())
            self._completer.complete(cr)  # popup it up!

    def focusInEvent(self, event):
        if self.completer():
            self.completer().setWidget(self)
        super(SyMPLTextEdit, self).focusInEvent(event)

    def sizeHint(self):
        fm = QtGui.QFontMetrics(self.font())
        opt = QtGui.QStyleOptionFrameV3()
        text = self.document().toPlainText()

        h = max(fm.height(), 14) + 4
        w = fm.width(text) + 4

        opt.initFrom(self)

        return (self.style().sizeFromContents(
            QtGui.QStyle.CT_LineEdit,
            opt,
            QtCore.QSize(w, h),
            self))

    def insert_completion(self, completion):
        if self._completer.widget() is not self:
            return
        tc = self.textCursor()
        extra = len(completion) - len(self._completer.completionPrefix())
        if extra == 0:
            insert_text = ''
        else:
            insert_text = completion[-extra:]

        # tc.movePosition(QtGui.QTextCursor.Left)
        # tc.movePosition(QtGui.QTextCursor.EndOfWord)
        tc.insertText(insert_text)
        self.setTextCursor(tc)

    def test_under_cursor(self):
        tc = self.textCursor()
        text = self.toPlainText()
        pos = tc.position()

        text_under_cursor = ''
        rx = re.compile(ur'''[\w\.\(\)'"]+''')

        for m in rx.finditer(text):
            if m.start() <= pos <= m.end():
                text_under_cursor = m.group()[:pos-m.start()]
                break
        return text_under_cursor

    def set_completer(self, c):
        if self._completer:
            self._completer.disconnect(self)
        self._completer = c

        if not self._completer:
            return

        self._completer.setWidget(self)
        self._completer.setCompletionMode(QtGui.QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._completer.insert_text.connect(self.insert_completion)

    def completer(self):
        return self._completer

    def set_value(self, value):
        self.setPlainText(unicode(value))

    def get_value(self):
        return self.toPlainText()


class SyMPLComboBox(QtGui.QComboBox):
    def set_value(self, value):
        idx = self.findText(value)
        if idx != -1:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(0)

    def get_value(self):
        return unicode(self.currentText())

    def set_options(self, options):
        self.clear()
        self.addItems(sorted(options))


class SyMPLSpinBox(QtGui.QSpinBox):
    def set_value(self, value):
        self.setValue(float(value))

    def get_value(self):
        return unicode(self.value())

    def set_options(self, options):
        if len(options) > 0 and options[0] is not None:
            self.setMinimum(int(options[0]))
        if len(options) > 1 and options[1] is not None:
            self.setMaximum(int(options[1]))
        if len(options) > 2 and options[2] is not None:
            self.setSingleStep(int(options[2]))


class SyMPLDoubleSpinBox(QtGui.QDoubleSpinBox):
    def set_value(self, value):
        self.setValue(float(value))

    def get_value(self):
        return unicode(self.value())

    def set_options(self, options):
        if len(options) > 0 and options[0] is not None:
            self.setMinimum(float(options[0]))
        if len(options) > 1 and options[1] is not None:
            self.setMaximum(float(options[1]))
        if len(options) > 2 and options[2] is not None:
            self.setSingleStep(float(options[2]))


class SyMPLCheckBox(QtGui.QCheckBox):
    def set_value(self, value):
        self.setChecked(bool(value))

    def get_value(self):
        return unicode(self.checkState())


class SyMPLColorPicker(QtGui.QWidget):
    def __init__(self, parent=None):
        super(SyMPLColorPicker, self).__init__(parent)
        self._init_gui()

    def _init_gui(self):
        self.setContentsMargins(0, 0, 0, 0)
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.textedit = SyMPLTextEdit()
        # self.lineedit.setPlaceholderText('name or rgb(a) or hex')
        self.color_select = QtGui.QToolButton()

        layout.addWidget(self.textedit)
        layout.addWidget(self.color_select)
        self.setLayout(layout)

        self.color_select.clicked.connect(self._on_color_pick)
        self.textedit.textChanged.connect(self._eval_color)

    def focusInEvent(self, event):
        if not self.textedit.hasFocus():
            self.textedit.setFocus(QtCore.Qt.OtherFocusReason)

    def _eval_color(self):
        text = self.textedit.toPlainText()
        color = colors.parse_color_to_mpl_color(text)
        if color is None:
            is_valid_color = QtGui.QColor.fromRgb(228, 186, 189)
        else:
            is_valid_color = self.palette().color(QtGui.QPalette.Background)
            self._update_button_color(color)

        self.textedit.setStyleSheet("""
        QLineEdit {
            background-color: %s;
        }
        """ % is_valid_color.name())

    def _on_color_pick(self):
        # store old value and type
        old_value = self.get_value()
        old_color_dev = colors.get_color_dev(old_value)
        color = colors.get_color_as_rgba_f(old_value)
        color = np.array(color) * 255
        qcolor = QtGui.QColor(*color.astype(int))
        # create dialog
        dialog = QtGui.QColorDialog(self)
        dialog.setOption(QtGui.QColorDialog.ShowAlphaChannel, True)
        color = dialog.getColor(initial=qcolor)
        # convert the color to previous type if possible
        if old_color_dev == 'name':
            color_name = mpl_colors.rgb2hex(color.getRgbF())
            new_value = colors.COLORS_INV.get(color_name, color_name)
        elif old_color_dev in ['rgbf', 'rgbaf']:
            new_value = color.getRgbF()
            new_value = [round(i, 2) for i in new_value]
        elif old_color_dev in ['rgb', 'rgba']:
            new_value = color.getRgb()
        elif old_color_dev == 'hex':
            new_value = mpl_colors.rgb2hex(color.getRgbF())
        else:
            new_value = color.name()
        self.set_value(new_value)

    def _update_button_color(self, value):
        color = colors.get_color_as_rgba_f(value)
        if color is not None:
            color = [int(i * 255.) for i in color[:3]]
        else:
            # TODO: possibly replace with a big X to indicate
            # that the color cannot be shown/is invalid
            color = [0, 0, 0]
        style = """
        QToolButton {
            background-color: rgb%s;
            border: 2px;
            border-color: rgb(255, 255, 255);
        }
        """ % str(tuple(color))
        self.color_select.setStyleSheet(style)

    def set_completer(self, c):
        self.textedit.set_completer(c)

    def set_value(self, value):
        self.textedit.set_value(unicode(value))
        self._update_button_color(unicode(value))

    def get_value(self):
        return unicode(self.textedit.get_value())


