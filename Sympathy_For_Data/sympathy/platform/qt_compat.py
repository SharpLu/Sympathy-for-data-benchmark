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
import os

USES_PYSIDE = True


class QtBackend(object):
    """Abstract interface class to define the backend functionality."""
    def use_matplotlib_qt(self):
        raise NotImplementedError('use_matplotlib_qt')

    def use_ipython_qt(self):
        raise NotImplementedError('use_ipython_qt')


class PySideBackend(QtBackend):
    def __init__(self):
        super(PySideBackend, self).__init__()

    def use_matplotlib_qt(self):
        import matplotlib
        os.environ['QT_API'] = 'pyside'
        matplotlib.use('Qt4Agg', warn=False)
        matplotlib.rcParams['backend.qt4'] = 'PySide'
        matplotlib.rcParams['backend'] = 'Qt4Agg'

    def use_ipython_qt(self):
        os.environ['QT_API'] = 'pyside'


if USES_PYSIDE:
    backend = PySideBackend()
    import PySide
    from PySide import QtCore
    from PySide import QtGui
else:
    raise Exception('No Qt4 backend available')
    backend = QtBackend()


def import_module(moduleName):
    pyside = __import__('PySide', globals(), locals(), [moduleName], -1)
    return getattr(pyside, moduleName)

Signal = QtCore.Signal
Slot = QtCore.Slot
Property = QtCore.Property


if __name__ == "__main__":
    pass
