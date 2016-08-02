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
import sys
import atexit

from sympathy.api import qt
QtCore = qt.QtCore
QtGui = qt.import_module('QtGui')
# from sympathy import syi as syi_module

from IPython.zmq.ipkernel import IPKernelApp
from IPython.lib.kernel import find_connection_file
from IPython.frontend.qt.kernelmanager import QtKernelManager
from IPython.frontend.qt.console.rich_ipython_widget import RichIPythonWidget
from IPython.config.application import catch_config_error


DEFAULT_INSTANCE_ARGS = ['qtconsole', '--pylab=inline', '--colors=linux']

QT_APP = None


class IPythonLocalKernelApp(IPKernelApp):
    @catch_config_error
    def initialize(self, argv=DEFAULT_INSTANCE_ARGS):
        """
        argv: IPython args

        example:

            app = QtGui.QApplication([])
            kernelapp = IPythonLocalKernelApp.instance()
            kernelapp.initialize()

            widget = IPythonConsoleQtWidget()
            widget.set_default_style(colors='linux')

            widget.connect_kernel(
                connection_file=kernelapp.get_connection_file())
            # if you won't to connect to remote kernel you don't need
            # kernelapp part, just widget part and:

            # widget.connect_kernel(connection_file='kernel-16098.json')

            # where kernel-16098.json is the kernel name
            widget.show()

            namespace = kernelapp.get_user_namespace()
            nxxx = 12
            namespace["widget"] = widget
            namespace["QtGui"]=QtGui
            namespace["nxxx"]=nxxx

            app.exec_()
        """
        # Disable logging to avoid irritating messages to stdout.
        self.log.disabled = True

        super(IPythonLocalKernelApp, self).initialize(argv)
        self.kernel.eventloop = self.loop_qt4_nonblocking
        self.kernel.start()
        self.start()

    def loop_qt4_nonblocking(self, kernel):
        """Non-blocking version of the ipython qt4 kernel loop"""
        kernel.timer = QtCore.QTimer()
        kernel.timer.timeout.connect(kernel.do_one_iteration)
        kernel.timer.start(1000 * kernel._poll_interval)

    def get_connection_file(self):
        """Returne current kernel connection file."""
        return self.connection_file

    def get_user_namespace(self):
        """Returns current kernel userspace dict"""
        return self.kernel.shell.user_ns


class IPythonConsoleQtWidget(RichIPythonWidget):
    def __init__(self):
        super(IPythonConsoleQtWidget, self).__init__()

    def connect_kernel(self, connection_file, heartbeat=False):
        """
        connection_file: str - is the connection file name, for example
        'kernel-16098.json'.
        heartbeat: bool - workaround, needed for right click/save as
                          ... errors ... i don't know how to
                          fix this issue. Anyone knows? Anyway it
                          needs more testing
            example1 (standalone):

                    app = QtGui.QApplication([])
                    widget = IPythonConsoleQtWidget()
                    widget.set_default_style(colors='linux')


                    widget.connect_kernel(
                        connection_file='some connection file name')

                    app.exec_()

            example2 (IPythonLocalKernelApp):

                    app = QtGui.QApplication([])

                    kernelapp = IPythonLocalKernelApp.instance()
                    kernelapp.initialize()

                    widget = IPythonConsoleQtWidget()

                    # Green text, black background ;)
                    widget.set_default_style(colors='linux')

                    widget.connect_kernel(
                        connection_file='kernelapp.get_connection_file())

                    app.exec_()

        """
        km = QtKernelManager(
            connection_file=find_connection_file(connection_file),
            config=self.config)
        km.load_connection_file()
        km.start_channels(hb=heartbeat)
        self.kernel_manager = km
        atexit.register(self.kernel_manager.cleanup_connection_file)


def main():
    global QT_APP
    QT_APP = QtGui.QApplication(sys.argv)

    # kernelapp = IPythonLocalKernelApp.instance()
    # kernelapp.initialize()

    # console = IPythonConsoleQtWidget()
    # console.set_default_style(colors='linux')
    # console.connect_kernel(connection_file=kernelapp.get_connection_file())

    # syi = syi_module.Syi()
    # NODE_CREATOR = syi.node_creator

    # data = syi.library.table.read_csv(fq_csvdata_filename)

    # namespace = kernelapp.get_user_namespace()
    # namespace.update(globals())
    # namespace.update(locals())

    return QT_APP.exec_()
