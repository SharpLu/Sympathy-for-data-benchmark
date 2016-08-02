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
from sympathy.api import qt
QtGui = qt.import_module('QtGui')

from .viewerbase import ViewerBase
from widget_library import SyNavigationToolbar


class FigureViewer(ViewerBase):
    def __init__(self, plot_data=None, console=None, parent=None):
        super(FigureViewer, self).__init__(parent)
        self._figure = plot_data
        self._mpl_figure = self._figure.get_mpl_figure()
        self._canvas = self._figure._get_qtcanvas()
        self._toolbar = SyNavigationToolbar(self._canvas, self)

        self._layout = QtGui.QVBoxLayout()
        self._layout.setSpacing(0)
        self._layout.addWidget(self._canvas)
        self._layout.addWidget(self._toolbar)
        self.setLayout(self._layout)

        self._set_figure_background_color()

    def _set_figure_background_color(self):
        # FIXME: setting the correct facecolor for matplotlib figures embedded
        # in QTabWidget or QGroupBox does not work
        color = self.palette().color(self.backgroundRole())
        self._canvas.figure.set_facecolor(color.name())

    def figure(self):
        return self._figure

    def data(self):
        return self.figure()

    def update_data(self, data):
        if data is not None:
            self._figure = data
            # replace the figure in the canvas and the canvas in the figure
            self._mpl_figure = self._figure.get_mpl_figure()
            self._mpl_figure.set_canvas(self._canvas)
            self._canvas.figure = self._mpl_figure
            self._set_figure_background_color()
            self._canvas.draw()  # is needed

