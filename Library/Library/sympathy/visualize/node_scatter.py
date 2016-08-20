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
In Sympathy for Data the following nodes exist for visualising data:
    - :ref:`Scatter 2D Table`
    - :ref:`Scatter 2D Tables`
    - :ref:`Scatter 3D Table`
    - :ref:`Scatter 2D ADAF`
    - :ref:`Scatter 3D ADAF`
    - :ref:`Scatter 2D ADAF with multiple timebases`.

In comparison with :ref:`Scatter 2D ADAF`, the last node can handle signals
connected to different timebases in the same plot. :ref:`Scatter 2D ADAF`
does only plot signals that have a common timebasis.

In the configuration ADAF signals, or Table columns, are selected along the
axes in the plots. There exist differences between the nodes how to do this,
but the basic principle is the same. The exception is
:ref:`Scatter 2D ADAF with multiple timebases` which uses an alternative
approach. For the actual plots is possible to change both line/marker style and
plot style in the plot. Below, the available plot styles are listed. A plot
legend is, by default, shown in the plot, but can be hidden by a simple push of
a button. The navigation toolbar under the plot let the user zoom and pan the
plot window.

Available plot types (2D):
    - plot
    - step
    - fill
    - hist bar
    - hist step

Available plot types (3D):
    - scatter
    - surf
    - wireframe
    - plot
    - contour
    - heatmap

The advanced plot controller allows the user to draw two lines parallel to
the Y-axis. These can be moved along the X-axis while information about the
intersection points between these lines and the plotted data points is shown
in a table. If a line is drawn in between two points in the plotted data, the
line will always move to the closest point.
"""
import os
import numpy as np
import sys

from sympathy.api import table
from sympathy.api import datasource as dsrc
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import NoDataError
from sympathy.api import qt as qt_compat
from sympathy.api.exceptions import sywarn

QtCore = qt_compat.QtCore  # noqa
QtGui = qt_compat.import_module('QtGui')  # noqa

qt_compat.backend.use_matplotlib_qt()  # noqa

from matplotlib.backends.backend_qt4agg import (
    FigureCanvasQTAgg as FigureCanvas)
from matplotlib.backends.backend_agg import (
    FigureCanvasAgg as FigureCanvasNonInteractive)
from matplotlib.backends.backend_qt4agg import (
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

# For 3D plot
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D


def deprecationwarn():
    sywarn(
        "This node is being deprecated in an upcoming release of Sympathy. "
        "Please remove the node from your workflow.")


def mock_wrap(cls):
    """
    For avoiding problems related to subclassing mocked class.
    This is used for being able to import modules without having the imports
    installed.
    See http://www.voidspace.org.uk/python/mock/.
    """
    return cls if isinstance(cls, type) else cls()


def reinit_2d(node_context):
    parameter_root = synode.parameters(node_context.parameters)
    parameter_root['tb_names'].list = []
    parameter_root['tb_names'].value = [0]
    parameter_root['x_axis'].list = []
    parameter_root['x_axis'].value = [0]
    parameter_root['x_axis'].value_names = []
    parameter_root['y_axis'].list = []
    parameter_root['y_axis'].value = [0]
    parameter_root['y_axis'].value_names = []
    parameter_root['line_style'].value = [0]
    parameter_root['plot_func'].value = [0]
    parameter_root['filename_extension'].list = []
    parameter_root['filename_extension'].value = [0]
    parameter_root['advanced_controller'].value = False
    parameter_root['t0'].value = ''
    parameter_root['t1'].value = ''
    parameter_root['visible_legend'].value = True
    parameter_root['x_min'].value = 0.0
    parameter_root['x_max'].value = 0.0
    parameter_root['y_min'].value = 0.0
    parameter_root['y_max'].value = 0.0
    parameter_root['title'].value = ''
    parameter_root['xlabel'].value = ''
    parameter_root['ylabel'].value = ''


def reinit_2dmult(node_context):
    parameter_root = synode.parameters(node_context.parameters)
    parameter_root['x_axis'].list = []
    parameter_root['x_axis'].value = [0]
    parameter_root['x_axis'].value_names = []
    parameter_root['y_axis'].list = []
    parameter_root['y_axis'].value = [0]
    parameter_root['y_axis'].value_names = []
    parameter_root['line_style'].value = [0]
    parameter_root['plot_func'].value = [0]
    parameter_root['filename_extension'].list = []
    parameter_root['filename_extension'].value = [0]
    parameter_root['display_strings']['plot_list'].list = []
    parameter_root['display_strings']['tb_names'].list = []
    parameter_root['display_strings']['ts_names'].list = []
    parameter_root['visible_legend'].value = True


def reinit_3d(node_context):
    """Reinitialize parameter_root for 3d plot. Ex. when file datasource has
    changed.
    """
    parameter_root = synode.parameters(node_context.parameters)
    parameter_root['tb_names'].list = []
    parameter_root['tb_names'].value = [0]
    parameter_root['x_axis'].list = []
    parameter_root['x_axis'].value = [0]
    parameter_root['x_axis'].value_names = []
    parameter_root['y_axis'].list = []
    parameter_root['y_axis'].value = [0]
    parameter_root['y_axis'].value_names = []
    parameter_root['z_axis'].list = []
    parameter_root['z_axis'].value = [0]
    parameter_root['z_axis'].value_names = []
    parameter_root['line_style'].value = [0]
    parameter_root['plot_func'].value = [0]
    parameter_root['filename_extension'].list = []
    parameter_root['filename_extension'].value = [0]
    parameter_root['azim'].value = -60
    parameter_root['elev'].value = 30


def inf_fq_filename(directory, filename):
    return os.path.join(directory, filename)


def create_filenames_from_parameters(parameter_root, index=None,
                                     table_name=None):
    export_directory = parameter_root['directory'].value
    filename = parameter_root['filename'].value
    extension = parameter_root['filename_extension'].selected
    if table_name is not None:
        complete_filename = '{}{}'.format(table_name, extension)
    else:
        if index is not None:
            complete_filename = '{}_{}{}'.format(filename, index, extension)
        else:
            complete_filename = '{}{}'.format(filename, extension)
    fq_filename = inf_fq_filename(export_directory, complete_filename)
    return fq_filename


def get_adaf_info(adaffile):
    table_list = table.FileList()
    for system in adaffile.sys.keys():
        for basis in adaffile.sys[system].keys():
            basis_table = adaffile.sys[system][basis].to_table()
            basis_table.set_name('{}/{}'.format(system, basis))
            table_list.append(basis_table)
    return table_list


def get_adaf_info_timebasis(adaffile):
    """Get information about adaf"""
    adaf_ts = adaffile.ts
    tb_dict = {}
    tb_ts_dict = {}
    tb_name_dict = {}
    tb_tsunits_dict = {}

    for ts_key, ts in adaf_ts.items():
        tb_name = ts.system_name() + '/' + ts.raster_name()
        try:
            tb_name_dict[tb_name]
        except:
            tb_name_dict[tb_name] = ts.basis().name()
        try:
            ts_dict = tb_ts_dict[tb_name]
            ts_dict[ts_key] = ts.y
        except:
            tb_ts_dict[tb_name] = {ts_key: ts.y}
        try:
            tb_dict[tb_name]
        except:
            tb_dict[tb_name] = ts.t
        try:
            tb_tsunits_dict[tb_name]
            tb_tsunits_dict[tb_name][ts_key] = ts.unit()
        except:
            tb_tsunits_dict[tb_name] = {ts_key: ts.unit()}
        tb_tsunits_dict[tb_name][tb_name] = 'unknown'  # FIXA SEN!!
    return tb_ts_dict, tb_name_dict, tb_dict, tb_tsunits_dict


class NavigationToolbarCustom(NavigationToolbar):
    zoomChanged = qt_compat.Signal(float, float, float, float)
    zoomActive = qt_compat.Signal(bool)
    panActive = qt_compat.Signal(bool)
    panDragged = qt_compat.Signal(float, float, float, float)
    parameters_edited = qt_compat.Signal()
    home_clicked = qt_compat.Signal()
    _home = True

    def __init__(self, canvas, parent):
        NavigationToolbar.__init__(self, canvas, parent)
        self._forward = False
        self._back = False

    def draw(self):
        super(NavigationToolbarCustom, self).draw()
        if self._xypress is None or self._home:
            home_view = self._views.home()
            x_min, x_max = home_view[0][0:2]
            y_min, y_max = home_view[0][2:4]
        elif self._forward:
            self._views.back()
            forward_view = self._views.forward()
            x_min, x_max = forward_view[0][0:2]
            y_min, y_max = forward_view[0][2:4]
        elif self._back:
            self._views.forward()
            back_view = self._views.back()
            x_min, x_max = back_view[0][0:2]
            y_min, y_max = back_view[0][2:4]
        else:
            if self._active == 'PAN':
                a = self._xypress_save[0][0].figure.axes[0]
            elif self._active == 'ZOOM':
                _, _, a, _, _, _ = self._xypress[0]
            else:
                a = self.canvas.figure.get_axes()
            x_min, x_max = a.get_xlim()
            y_min, y_max = a.get_ylim()
        self.parameters_edited.emit()
        self.zoomChanged.emit(x_min, x_max, y_min, y_max)

    def pan(self, *args):
        super(NavigationToolbarCustom, self).pan()
        self.panActive.emit(self._active == 'PAN')

    def zoom(self, *args):
        super(NavigationToolbarCustom, self).zoom()
        self.zoomActive.emit(self._active == 'ZOOM')

    def home(self, *args):
        self._home = True
        super(NavigationToolbarCustom, self).home()
        self._home = False
        self.home_clicked.emit()
        self.parameters_edited.emit()

    def release_zoom(self, event):
        super(NavigationToolbarCustom, self).release_zoom(event)
        self._home = False
        self._xypress_save = None
        self.parameters_edited.emit()

    def forward(self, *args):
        self._forward = True
        super(NavigationToolbarCustom, self).forward(*args)
        self._forward = False

    def back(self, *args):
        self._back = True
        super(NavigationToolbarCustom, self).back(*args)
        self._back = False

    def release_pan(self, event):
        self._xypress_save = self._xypress
        super(NavigationToolbarCustom, self).release_pan(event)
        self._home = False
        self._xypress_save = None

    def drag_pan(self, event):
        a, ind = self._xypress[0]
        super(NavigationToolbarCustom, self).drag_pan(event)
        x_min, x_max = a.get_xlim()
        y_min, y_max = a.get_ylim()
        self.parameters_edited.emit()
        self.panDragged.emit(x_min, x_max, y_min, y_max)

    def edit_parameters(self):
        super(NavigationToolbarCustom, self).edit_parameters()
        self.parameters_edited.emit()


class FigureCanvasCustom(FigureCanvas):
    canvasResized = qt_compat.Signal()

    def __init__(self, canvas):
        super(FigureCanvasCustom, self).__init__(canvas)

    def resizeEvent(self, event):
        FigureCanvas.resizeEvent(self, event)
        self.canvasResized.emit()


class SuperNode(object):
    author = 'Helena Olen <helena.olen@combine.se>'
    copyright = '(C) 2013 Combine AB'
    version = '1.0'
    icon = 'scatter2d.svg'


class SuperTableNode(SuperNode):
    inputs = Ports(
        [Port.Table('Input Table', name='port1', requiresdata=True)])


class SuperTablesNode(SuperNode):
    inputs = Ports(
        [Port.Tables('Input Tables', name='port1', requiresdata=True)])


class SuperADAFNode(SuperNode):
    inputs = Ports([Port.ADAF('Input ADAF', name='port1', requiresdata=True)])


class Super2dNode(SuperNode):
    tags = Tags(Tag.Hidden.Deprecated)

    parameters = synode.parameters()
    parameters.set_list(
        'tb_names', label='Time basis',
        description='Combo of all timebasis.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'x_axis', label='X-axis',
        description='X-axis selection for plot.',
        editor=synode.Util.combo_editor().value())
    y_axis_editor = synode.Util.list_editor()
    y_axis_editor.set_attribute('filter', True)
    y_axis_editor.set_attribute('selection', 'multi')
    parameters.set_list(
        'y_axis', label='Y-axis', description='Y-axis selection for plot',
        editor=y_axis_editor.value())
    parameters.set_list(
        'line_style', label='Line style',
        plist=['o', '--', '-', '^', '*', '-o', '-*', '.', ':'],
        description='Selectable line styles.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'plot_func', label='Plot type',
        plist=['plot', 'step', 'fill', 'hist bar', 'hist step'],
        description='Selectable plot types.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'filename_extension',
        description='Filename extension.',
        editor=synode.Util.combo_editor().value())
    parameters.set_boolean(
        'advanced_controller', value=False,
        label='Use advanced plot controller',
        decription='Advanced plot controller option.')
    parameters.set_string('t0', value='')
    parameters.set_string('t1', value='')
    parameters.set_float('x_min', value=0.0)
    parameters.set_float('x_max', value=0.0)
    parameters.set_float('y_min', value=0.0)
    parameters.set_float('y_max', value=0.0)
    parameters.set_string('title', value='')
    parameters.set_string('ylabel', value='')
    parameters.set_string('xlabel', value='')
    parameters.set_boolean('visible_legend', value=True)


class Super2dMultTbNode(SuperNode):
    tags = Tags(Tag.Hidden.Deprecated)

    parameters = synode.parameters()
    parameters.set_list(
        'x_axis', label='X-axis',
        description='X-axis selection for plot.',
        editor=synode.Util.combo_editor().value())
    y_axis_editor = synode.Util.list_editor()
    y_axis_editor.set_attribute('filter', True)
    y_axis_editor.set_attribute('selection', 'multi')
    parameters.set_list(
        'y_axis', label='Y-axis',
        description='Y-axis selection for plot.',
        editor=y_axis_editor.value())
    parameters.set_list(
        'line_style', label='Line style',
        plist=['o', '--', '-', '^', '*', '-o', '-*', '.', ':'],
        description='Selectable line styles.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'plot_func', label='Plot type',
        plist=['plot', 'step', 'fill', 'hist bar', 'hist step'],
        description='Selectable plot types.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'filename_extension',
        description='Filename extension.',
        editor=synode.Util.combo_editor().value())


class Super3dNode(SuperNode):
    tags = Tags(Tag.Visual.Plot)

    icon = 'scatter3d.svg'
    parameters = synode.parameters()
    parameters.set_list(
        'tb_names', label='Time basis',
        description='Combo of all timebasis.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'x_axis', label='X-axis',
        description='X-axis selection for plot.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'y_axis', label='Y-axis',
        description='Y-axis selection for plot.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'z_axis', label='Z-axis',
        description='Z-axis selection for plot.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'line_style', label='Line style',
        plist=['o', '^', '*'],
        description='Selectable line styles.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'plot_func', label='Plot type',
        plist=['scatter', 'surf', 'wireframe', 'plot', 'contour', 'heatmap'],
        description='Selectable plot types.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'filename_extension',
        description='Filename extension.',
        editor=synode.Util.combo_editor().value())
    parameters.set_integer('azim', value=-60)
    parameters.set_integer('elev', value=30)


class Scatter2dNode(Super2dNode, SuperTableNode, synode.Node):
    """
    Plot data in Table in two dimensions.

    :Input:
        **TableInput** : Table
            Table with data to visualise
    :Configuration:
        **X-axis**
            Select column along the X-axis.
        **Y-axis**
            Select columns along the Y-axis. Here, it is possible to select
            one or many columns. In the plot the columns are
            separated with different colors.
        **Line style**
            Select line style used in the plot.
        **Plot type**
            Select plot type for the plot.
        **Show/hide legend**
            Turn on/off the legend in the plot window.
        **Output directory**
            Specify where in the file-tree to store an exported plot.
        **Filename**
            Specify filename and data format of an exported plot.
    :Ref. nodes: :ref:`Scatter 2D Tables`
    """

    name = 'Scatter 2D Table'
    description = 'A two dimensional scatter plot'
    nodeid = 'org.sysess.sympathy.visualize.scatter2dnode'

    def __init__(self):
        super(Scatter2dNode, self).__init__()

    def verify_parameters(self, node_context):
        parameters = node_context.parameters
        parameter_root = synode.parameters(parameters)
        try:
            filename = parameter_root['filename'].value
            directory = parameter_root['directory'].value
            if filename == '' or directory == '':
                return False
        except:
            return False
        return True

    def exec_parameter_view(self, node_context):
        """Create the parameter view"""
        table = []
        in_table = []
        try:
            if ('port1' in node_context.input and
                    node_context.input['port1'].is_valid()):
                if len(node_context):
                    in_table = node_context.input['port1']
                else:
                    in_table = node_context.input.ELEMENT()
                table.append(in_table)
        except NoDataError:
            # When no input is connected
            pass
        try:
            return Scatter2dWidget(node_context, table)
        except:
            reinit_2d(node_context)
            return Scatter2dWidget(node_context, table)

    def execute(self, node_context):
        """Execute"""
        fq_filename = create_filenames_from_parameters(node_context.parameters)
        fig = Figure()
        FigureCanvasNonInteractive(fig)
        axes = fig.add_subplot(111)
        tablefile = node_context.input['port1']
        tabledata = table.FileList()
        tabledata.append(tablefile)
        plot_widget = Scatter2dPlot(
            tabledata, node_context.parameters, axes, index_name='Index')
        plot_widget.update_figure()
        fig.savefig(fq_filename)


class Scatter2dNodeMultiple(Super2dNode, SuperTablesNode, synode.Node):
    """
    Plot data in Tables in two dimensions.

    :Input:
        **TableInput** : Tables
            Table with data to visualise
    :Configuration:
        **X-axis**
            Select column along the X-axis.
        **Y-axis**
            Select columns along the Y-axis. Here, it is possible to select
            one or many columns. In the plot the columns are
            separated with different colors.
        **Line style**
            Select line style used in the plot.
        **Plot type**
            Select plot type for the plot.
        **Show/hide legend**
            Turn on/off the legend in the plot window.
        **Output directory**
            Specify where in the file-tree to store an exported plot.
        **Filename**
            Specify filename and data format of an exported plot.
    :Ref. nodes: :ref:`Scatter 2D Table`
    """

    name = 'Scatter 2D Tables'
    description = 'A two dimensional scatter plot'
    nodeid = 'org.sysess.sympathy.visualize.scatter2dmulti'

    def __init__(self):
        super(Scatter2dNodeMultiple, self).__init__()

    def verify_parameters(self, node_context):
        try:
            filename = node_context.parameters['filename'].value
            directory = node_context.parameters['directory'].value
            if filename == '' or directory == '':
                return False
        except:
            return False
        return True

    def exec_parameter_view(self, node_context):
        """Create the parameter view."""
        tabledata = table.FileList()
        try:
            in_file = node_context.input['port1']
            if len(in_file):
                tablefile = in_file[0]
                tabledata.append(tablefile)
        except NoDataError:
            # When no input is connected
            pass

        try:
            return Scatter2dWidget(node_context, tabledata)
        except:
            reinit_2d(node_context)
            return Scatter2dWidget(node_context, tabledata)

    def execute(self, node_context):
        """Execute"""
        parameters = node_context.parameters
        dsrc_list = node_context.output['port1']
        input_list = node_context.input['port1']
        num_files = len(input_list)
        for idx, infile in enumerate(input_list):
            fq_filename = create_filenames_from_parameters(
                parameters, index=idx, table_name=infile.get_name())
            fig = Figure()
            FigureCanvasNonInteractive(fig)
            axes = fig.add_subplot(111)
            tabledata = table.FileList()
            tabledata.append(infile)
            plot_widget = Scatter2dPlot(
                tabledata, parameters, axes, index_name='Index')
            plot_widget.update_figure()
            fig.savefig(fq_filename)
            with dsrc.File() as dsrc_file:
                dsrc_file.encode_path(fq_filename)
                dsrc_list.append(dsrc_file)
            self.set_progress(100.0 * (1 + idx) / num_files)


class Scatter2dNodeADAF(Super2dNode, SuperADAFNode, synode.Node):
    """
    Plot data in ADAF in two dimensions. This node plots only signals that
    share a common timebasis.

    :Input:
        **TableInput** : ADAF
            ADAF with data to visualise
    :Configuration:
        **Time basis**
            Select time basis that is shared for the signals you want to plot.
        **X-axis**
            Select signal along the X-axis.
        **Y-axis**
            Select signals along the Y-axis. Here, it is possible to select
            one or many columns. In the plot the columns are
            separated with different colors.
        **Line style**
            Select line style used in the plot.
        **Plot type**
            Select plot type for the plot.
        **Show/hide legend**
            Turn on/off the legend in the plot window.
        **Output directory**
            Specify where in the file-tree to store an exported plot.
        **Filename**
            Specify filename and data format of an exported plot.
    :Ref. nodes: :ref:`Scatter 2D ADAF with multiple timebases`
    """

    name = 'Scatter 2D ADAF'
    description = 'A two dimensional scatter plot'
    nodeid = 'org.sysess.sympathy.visualize.scatter2dnodeadaf'

    def __init__(self):
        super(Scatter2dNodeADAF, self).__init__()

    def exec_parameter_view(self, node_context):
        """Create the parameter view"""
        in_table = []
        try:
            if ('port1' in node_context.input and
                    node_context.input['port1'].is_valid()):
                in_table = get_adaf_info(node_context.input['port1'])
        except NoDataError:
            # When no data is connected
            pass

        try:
            return Scatter2dWidget(node_context, in_table)
        except:
            reinit_2d(node_context)
            return Scatter2dWidget(node_context, in_table)

    def verify_parameters(self, node_context):
        try:
            filename = node_context.parameters['filename'].value
            directory = node_context.parameters['directory'].value
            if filename == '' or directory == '':
                return False
        except:
            return False
        return True

    def execute(self, node_context):
        """Execute"""
        fq_filename = create_filenames_from_parameters(node_context.parameters)
        fig = Figure()
        FigureCanvasNonInteractive(fig)
        axes = fig.add_subplot(111)
        tables = get_adaf_info(node_context.input['port1'])
        plot_widget = Scatter2dPlot(
            tables, node_context.parameters, axes, index_name='Index')
        plot_widget.update_figure()
        fig.savefig(fq_filename)


class Scatter2dNodeADAFMultipleTb(Super2dMultTbNode, SuperADAFNode,
                                  synode.Node):
    """
    Plot data in ADAF in two dimensions. Compared to :ref:`Scatter 2D ADAF`
    this node can handle signals connected to different timebases in the same
    plot.

    :Input:
        **TableInput** : ADAF
            ADAF with data to visualise
    :Configuration:
        **X-axis**
            Select timebasis along the X-axis.
        **Y-axis**
            Select signals along the Y-axis that is connected to the selected
            timebasis along the X-axis.
        **Add selection to plot list** : button
            Add selected combinations of timebasis along X-axis and signals
            along the Y-axis to plot list. It is first when the combinations
            appear in the plot list they will be drawn in the plot window.
        **Remove plot line** : button
            When pushed the marked combinations in the plot list will be
            removed from both the plot list and the plot window.
        **Line style**
            Select line style used in the plot.
        **Plot type**
            Select plot type for the plot.
        **Show/hide legend**
            Turn on/off the legend in the plot window.
        **Output directory**
            Specify where in the file-tree to store an exported plot.
        **Filename**
            Specify filename and data format of an exported plot.
    :Ref. nodes: :ref:`Scatter 2D ADAF`
    """

    name = 'Scatter 2D ADAF with multiple timebases'
    description = 'A two dimensional plot with multiple timebases.'
    nodeid = 'org.sysess.sympathy.visualize.scatter2dnodeadafmultipletb'

    def __init__(self):
        super(Scatter2dNodeADAFMultipleTb, self).__init__()

    def exec_parameter_view(self, node_context):
        """Create the parameter view"""
        tb_ts_dict = None
        tb_name_dict = None
        tb_dict = None
        units = None
        try:
            with node_context.input['port1'] as adaffile:
                (tb_ts_dict, tb_name_dict, tb_dict, units) = (
                    get_adaf_info_timebasis(adaffile))
        except NoDataError:
            # when no input is connected
            pass
        try:
            return Scatter2dWidgetMultipleTb(
                node_context, tb_ts_dict, tb_name_dict, tb_dict, units)
        except:
            reinit_2dmult(node_context)
            return Scatter2dWidgetMultipleTb(
                node_context, tb_ts_dict, tb_name_dict, tb_dict, units)

    def verify_parameters(self, node_context):
        try:
            filename = node_context.parameters['filename'].value
            directory = node_context.parameters['directory'].value
            if filename == '' or directory == '':
                return False
        except:
            return False
        return True

    def execute(self, node_context):
        """Execute"""
        fq_filename = create_filenames_from_parameters(node_context.parameters)
        fig = Figure()
        FigureCanvasNonInteractive(fig)
        axes = fig.add_subplot(111)
        with node_context.input['port1'] as adaffile:
            (tb_ts_dict, tb_name_dict, tb_dict, units) = (
                get_adaf_info_timebasis(adaffile))
        plot_widget = Scatter2dPlotMultipleTb(
            node_context.parameters, axes, tb_ts_dict, tb_name_dict, tb_dict,
            units)
        plot_widget.update_figure()
        fig.savefig(fq_filename)


class Scatter3dNode(Super3dNode, SuperTableNode, synode.Node):
    """
    Plot data in Table in three dimensions.

    :Input:
        **TableInput** : Table
            Table with data to visualise
    :Configuration:
        **X-axis**
            Select column along the X-axis.
        **Y-axis**
            Select column along the Y-axis.
        **Z-axis**
            Select column along the Z-axis.
        **Line style**
            Select line style used in the plot.
        **Plot type**
            Select plot type for the plot.
        **Output directory**
            Specify where in the file-tree to store an exported plot.
        **Filename**
            Specify filename and data format of an exported plot.
    :Ref. nodes: :ref:`Scatter 2D Table`
    """

    name = 'Scatter 3D Table'
    description = 'A three dimensional plot'
    nodeid = 'org.sysess.sympathy.visualize.scatter3dnode'

    def __init__(self):
        super(Scatter3dNode, self).__init__()

    def verify_parameters(self, node_context):
        parameters = node_context.parameters
        parameter_root = synode.parameters(parameters)
        try:
            filename = parameter_root['filename'].value
            directory = parameter_root['directory'].value
            if filename == '' or directory == '':
                return False
        except:
            return False
        return True

    def exec_parameter_view(self, node_context):
        """Create the parameter view"""
        tabledata = None
        try:
            with node_context.input['port1'] as tablefile:
                tabledata = tablefile.to_recarray()
        except NoDataError:
            # When no input is connected
            pass
        reinit_3d(node_context)
        return Scatter3dWidget(node_context, [tabledata])

    def execute(self, node_context):
        """Execute"""
        parameter_root = synode.parameters(node_context.parameters)
        fq_filename = create_filenames_from_parameters(parameter_root)
        fig = Figure()
        FigureCanvasNonInteractive(fig)
        axes = Axes3D(fig)
        with node_context.input['port1'] as tablefile:
            tabledata = tablefile.to_recarray()
        plot_widget = Plot3d(
            [tabledata], parameter_root, fig, axes)
        plot_widget.update_figure()
        fig.savefig(fq_filename)


class Scatter3dNodeADAF(Super3dNode, SuperADAFNode, synode.Node):
    """
    Plot data in ADAF in three dimensions. This node plots only signals that
    share a common timebasis.

    :Input:
        **TableInput** : ADAF
            ADAF with data to visualise
    :Configuration:
        **Time basis**
            Select time basis that is shared for the signals you want to plot.
        **X-axis**
            Select signal along the X-axis.
        **Y-axis**
            Select signal along the Y-axis.
        **Z-axis**
            Select signal along the Z-axis.
        **Line style**
            Select line style used in the plot.
        **Plot type**
            Select plot type for the plot.
        **Output directory**
            Specify where in the file-tree to store an exported plot.
        **Filename**
            Specify filename and data format of an exported plot.
    :Ref. nodes: :ref:`Scatter 2D ADAF`
    """

    name = 'Scatter 3D ADAF'
    description = 'A three dimensional plot'
    nodeid = 'org.sysess.sympathy.visualize.scatter3dnodeadaf'

    def __init__(self):
        super(Scatter3dNodeADAF, self).__init__()

    def exec_parameter_view(self, node_context):
        """Create the parameter view"""
        tables = None
        names = None
        names_short = None
        units = None
        in_table = []
        name = None
        name_short = None
        unit = None
        try:
            with node_context.input['port1'] as adaffile:
                (tables, names, names_short, units) = get_adaf_info(adaffile)
                in_table.append(tables.to_recarray())
                name = names[0].to_recarray()
                name_short = names_short[0].to_recarray()
                unit = units[0].to_recarray()
        except NoDataError:
            # When no input is connected
            pass
        try:
            return Scatter3dWidget(
                node_context, in_table, name, name_short, unit)
        except:
            reinit_3d(node_context)
            return Scatter3dWidget(
                node_context, in_table, name, name_short, unit)

    def verify_parameters(self, node_context):
        parameters = node_context.parameters
        parameter_root = synode.parameters(parameters)
        try:
            filename = parameter_root['filename'].value
            directory = parameter_root['directory'].value
            if filename == '' or directory == '':
                return False
        except:
            return False
        return True

    def execute(self, node_context):
        """Execute"""
        parameter_root = synode.parameters(node_context.parameters)
        fq_filename = create_filenames_from_parameters(parameter_root)
        fig = Figure()
        FigureCanvasNonInteractive(fig)
        axes = Axes3D(fig)
        with node_context.input['port1'] as adaffile:
            (tables, _, names_short, units) = get_adaf_info(adaffile)
        tables = tables.to_recarray()
        plot_widget = Plot3d(
            [tables], parameter_root, fig, axes, names_short, units)
        plot_widget.update_figure()
        fig.savefig(fq_filename)


@mock_wrap
class PlotWidget(QtGui.QWidget):
    def __init__(self, node_context):
        super(PlotWidget, self).__init__()
        self._node_context = node_context
        self._parameter_root = synode.parameters(node_context.parameters)
        self._x_axis_combobox = None
        self._y_axis = None
        self._line_style_combobox = None
        self._plot_combobox = None
        self._file_extension_combo = None
        self._outputs_hlayout = None
        self._projection = None
        self._background = None

        self._figure = None
        self._axes = None
        self._canvas = None
        self._toolbar = None

        self._plot = None

    def _init_gui(self):
        pass

    def _pre_init_gui_from_parameters(self):
        pass

    def _init_gui_from_parameters(self):
        pass

    def _create_figure_gui(self):
        if sys.platform == 'darwin':
            backgroundcolor = '#ededed'
        else:
            backgroundcolor = self.palette().color(
                QtGui.QPalette.Window).name()
        self._figure = Figure(facecolor=backgroundcolor)
        self._create_subplot()
        self._create_canvas_tool()

    def _create_subplot(self):
        """To be implemented by subclasses"""
        try:
            self._axes = self._figure.add_subplot(
                111, projection=self._projection)
        except ValueError:
            pass

    def _create_canvas_tool(self):
        """Create canvas and navigation toolbar."""
        self._canvas = FigureCanvasCustom(self._figure)
        policy = QtGui.QSizePolicy()
        policy.setHorizontalStretch(1)
        policy.setVerticalStretch(1)
        policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        policy.setVerticalPolicy(QtGui.QSizePolicy.Expanding)
        self._canvas.setSizePolicy(policy)
        self._toolbar = NavigationToolbarCustom(self._canvas, self)

    def _create_output_layout(self):
        """Create output layout with directory edit, file editor and file
        extension combo.
        """
        try:
            self._parameter_root['directory']
        except KeyError:
            self._parameter_root.set_string(
                "directory", label="Output directory",
                description="Select the directory where to export the files.",
                editor=synode.Util.directory_editor().value())
        try:
            self._parameter_root['filename']
        except KeyError:
            self._parameter_root.set_string(
                "filename", label="Filename",
                description="Filename without extension.")

        self._outputs_hlayout = QtGui.QHBoxLayout()
        self._outputs_hlayout.addWidget(
            self._parameter_root['directory'].gui())
        self._outputs_hlayout.addWidget(self._parameter_root['filename'].gui())
        self._file_extension_combo = (self._parameter_root[
            'filename_extension'].gui())
        self._outputs_hlayout.addWidget(self._file_extension_combo)


class Scatter2dWidget(PlotWidget):
    """Widget to plot a two dimensional scatter graph."""

    def __init__(self, node_context, tables):
        """
        Args: tables (list): table.FileList()
              names (list): list of names of the tables in tables
              tb_names (list): list of short time basis names,
                              corresponding to long names in names
              units: {table_name: {column_name1: column_unit1, ...}, ...}
        """
        super(Scatter2dWidget, self).__init__(node_context)

        self._tb_combobox = None
        self._pressed = False
        self._current_t = None
        self._actual_t = None
        self._t0_line = None
        self._t1_line = None
        self._names = []

        self._tables = tables

        if len(self._tables) and self._tables[0].is_valid():
            self._names = [t.get_name() for t in self._tables]
        self._no_lines_by_click = False
        self._index_name = 'Index'
        self._t_colors = {'t0': 'k', 't1': 'indigo'}
        self._init_gui()

    def _init_gui(self):
        self._column_names = []
        if len(self._tables) and self._tables[0].is_valid():
            self._column_names = sorted(list(self._tables[0].column_names()))
        # Create plot window
        self._create_figure_gui()
        self._pre_init_gui_from_parameters()
        vlayout = QtGui.QVBoxLayout()
        axes_hlayout = QtGui.QHBoxLayout()
        axes_hlayout.setSpacing(20)

        self._tb_combobox = self._parameter_root['tb_names'].gui()
        self._x_axis_combobox = self._parameter_root['x_axis'].gui()
        self._y_axis = self._parameter_root['y_axis'].gui()

        axis_vlayout = QtGui.QVBoxLayout()
        axis_vlayout.addWidget(self._tb_combobox)
        axis_vlayout.addWidget(self._x_axis_combobox)
        axis_vlayout.addWidget(self._y_axis)

        self._line_style_combobox = self._parameter_root['line_style'].gui()
        self._plot_combobox = self._parameter_root['plot_func'].gui()
        self._legend_button = QtGui.QPushButton('Show/hide legend')
        self._advanced_controller = QtGui.QCheckBox(
            'Use advanced plot controller')
        legend_vlayout = QtGui.QVBoxLayout()
        legend_vlayout.addSpacing(26)
        legend_vlayout.addWidget(self._legend_button)
        legend_vlayout.addSpacing(2)

        plot_style_hlayout = QtGui.QHBoxLayout()
        plot_style_hlayout.addWidget(
            self._line_style_combobox,
            alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        plot_style_hlayout.addWidget(
            self._plot_combobox,
            alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        plot_style_hlayout.addLayout(legend_vlayout)
        plot_style_hlayout.addWidget(
            self._advanced_controller,
            alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        plot_style_hlayout.insertStretch(0)
        plot_style_hlayout.setContentsMargins(0, 0, 0, 0)

        # Create output layout
        self._create_output_layout()

        # Create advanced plot controller widgets and layouyts
        self._reset_button = QtGui.QPushButton('Remove lines')
        self._t0_label = QtGui.QLabel('t0')
        self._t0_edit = QtGui.QLineEdit('')
        self._t1_label = QtGui.QLabel('t1')
        self._t1_label.setStyleSheet('color: indigo')
        self._t1_edit = QtGui.QLineEdit('')
        self._tdiff_label = QtGui.QLabel('t1-t0')
        self._tdiff_edit = QtGui.QLineEdit('')
        self._tdiff_edit.setReadOnly(True)
        self._ts_info_table = QtGui.QTableWidget()

        advanced_plot_layout = QtGui.QGridLayout()
        advanced_plot_layout.addWidget(self._reset_button, 0, 0, 1, 2)
        advanced_plot_layout.addWidget(self._t0_label, 1, 0)
        advanced_plot_layout.addWidget(self._t0_edit, 1, 1)
        advanced_plot_layout.addWidget(self._t1_label, 2, 0)
        advanced_plot_layout.addWidget(self._t1_edit, 2, 1)
        advanced_plot_layout.addWidget(self._tdiff_label, 3, 0)
        advanced_plot_layout.addWidget(self._tdiff_edit, 3, 1)
        advanced_plot_layout.addWidget(self._ts_info_table, 4, 0, 1, 2)

        plot_vlayout = QtGui.QVBoxLayout()
        plot_vlayout.addLayout(plot_style_hlayout)
        plot_vlayout.addWidget(self._canvas)
        plot_vlayout.addWidget(self._toolbar)

        plot_and_controller_splitlayout = QtGui.QSplitter(QtCore.Qt.Horizontal)
        axis_frame = QtGui.QFrame()
        axis_frame.setFrameShape(QtGui.QFrame.StyledPanel)
        axis_frame.setLayout(axis_vlayout)
        plot_and_controller_splitlayout.addWidget(axis_frame)
        plot_frame = QtGui.QFrame()
        plot_frame.setFrameShape(QtGui.QFrame.StyledPanel)
        plot_frame.setLayout(plot_vlayout)
        plot_and_controller_splitlayout.addWidget(plot_frame)
        advanced_controller_frame = QtGui.QFrame()
        advanced_controller_frame.setFrameShape(QtGui.QFrame.StyledPanel)
        advanced_controller_frame.setLayout(advanced_plot_layout)
        plot_and_controller_splitlayout.addWidget(advanced_controller_frame)

        outputs_widget = QtGui.QWidget()
        outputs_widget.setLayout(self._outputs_hlayout)
        policy = QtGui.QSizePolicy()
        policy.setVerticalPolicy(QtGui.QSizePolicy.Fixed)
        policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        outputs_widget.setSizePolicy(policy)

        vlayout.addWidget(plot_and_controller_splitlayout)
        vlayout.addWidget(outputs_widget)
        self.setLayout(vlayout)

        self._init_gui_from_parameters()

        self._x_axis_combobox.editor().currentIndexChanged[int].connect(
            self._x_axis_change)
        self._tb_combobox.editor().currentIndexChanged[int].connect(
            self._tb_names_change)
        self._y_axis.editor().itemChanged.connect(self._y_axis_changed)

        self._line_style_combobox.editor().currentIndexChanged[int].connect(
            self._line_style_changed)
        self._plot_combobox.editor().currentIndexChanged.connect(
            self._plot_func_changed)
        self._legend_button.clicked.connect(self._hide_legend)
        self._advanced_controller.stateChanged.connect(
            self._advanced_controller_changed)
        self._reset_button.clicked.connect(self._reset_lines)
        self._t0_edit.editingFinished.connect(self._t0_changed)
        self._t1_edit.editingFinished.connect(self._t1_changed)
        self._figure.canvas.mpl_connect(
            'button_press_event', self._canvas_mouse_clicked)
        self._figure.canvas.mpl_connect(
            'button_release_event', self._canvas_mouse_released)
        self._figure.canvas.mpl_connect(
            'motion_notify_event', self._move_t)
        self._toolbar.zoomChanged.connect(self._zoom_changed)
        self._toolbar.panActive.connect(self._pan_active)
        self._toolbar.zoomActive.connect(self._zoom_active)
        self._toolbar.panDragged.connect(self._pan_dragged)
        self._canvas.canvasResized.connect(self._canvas_resized)
        self._toolbar.parameters_edited.connect(self._store_plot_parameters)
        self._toolbar.home_clicked.connect(self._reset_plot)

    @qt_compat.Slot()
    def _reset_plot(self):
        self._parameter_root['x_min'].value = 0
        self._parameter_root['x_max'].value = 0
        self._parameter_root['y_min'].value = 0
        self._parameter_root['y_max'].value = 0
        self._update_figure()

    @qt_compat.Slot()
    def _store_plot_parameters(self):
        axis = self._figure.axes[0]
        pars = {
            'x_min': axis.get_xlim()[0],
            'x_max': axis.get_xlim()[1],
            'y_min': axis.get_ylim()[0],
            'y_max': axis.get_ylim()[1],
            'title': axis.get_title(),
            'xlabel': axis.get_xlabel(),
            'ylabel': axis.get_ylabel()}

        for parameter, function in pars.items():
            self._parameter_root[parameter].value = function

    def _restore_plot_parameters(self):
        axis = self._axes
        x_min = self._parameter_root['x_min'].value
        x_max = self._parameter_root['x_max'].value
        if x_min < x_max:
            axis.set_xlim((x_min, x_max))
        y_min = self._parameter_root['y_min'].value
        y_max = self._parameter_root['y_max'].value
        if y_min < y_max:
            axis.set_ylim((y_min, y_max))
        axis.set_title(self._parameter_root['title'].value)
        axis.set_xlabel(self._parameter_root['xlabel'].value)
        axis.set_ylabel(self._parameter_root['ylabel'].value)

    def _pre_init_gui_from_parameters(self):
        """Init comboboxes created in parameter_root"""
        x_axis_list = self._get_x_axis_list(self._column_names)

        if self._parameter_root['tb_names'].list and self._names:
            self._parameter_root['tb_names'].list = self._names
            self._parameter_root['tb_names'].value = [0]

        if not self._parameter_root['x_axis'].list:
            self._parameter_root['x_axis'].list = x_axis_list
            self._parameter_root['x_axis'].value = [0]

        if not self._parameter_root['y_axis'].list:
            self._parameter_root['y_axis'].list = self._column_names
            self._parameter_root['y_axis'].value = [0]

        if not self._parameter_root['filename_extension'].list:
            supported_files_dict = (self._figure.canvas.
                                    get_supported_filetypes())
            supported_files = supported_files_dict.keys()
            supported_files = (['.' + supported_file
                                for supported_file in supported_files])
            self._parameter_root['filename_extension'].list = supported_files
            self._parameter_root['filename_extension'].value = [0]

    def _init_gui_from_parameters(self):
        """Init gui from parameters"""
        if 'visible_legend' in self._parameter_root:
            self._parameter_root.set_boolean('visible_legend', value=True)

        if len(self._names) == 0:
            self._tb_combobox.editor().setEnabled(False)

        self._plot = Scatter2dPlot(
            self._tables, self._parameter_root, self._axes, self._index_name)

        self._t0_edit.blockSignals(True)
        self._t1_edit.blockSignals(True)
        self._t0_edit.setText(self._parameter_root['t0'].value)
        self._t1_edit.setText(self._parameter_root['t1'].value)
        self._t0_edit.blockSignals(False)
        self._t1_edit.blockSignals(False)

        self._advanced_controller.setChecked(
            self._parameter_root['advanced_controller'].value)
        self._hide_advanced_controller()
        self._background = None
        self._canvas_size = None

        # Enable/disable plot function widges and update figure
        self._plot_func_changed()
        QtCore.QTimer.singleShot(0, self._update_figure)

    def resizeEvent(self, event):
        """Update background and figure when widget is resized."""
        if self._canvas_size != self._canvas.size():
            self._background = None
            self.repaint()
            self.update()
            self._canvas_size = self._canvas.size()
        self._update_figure()

    def _canvas_resized(self):
        """Update background and figure when canvas is resized."""
        if self._canvas_size != self._canvas.size():
            self._background = None
            self.repaint()
            self.update()
            self._canvas_size = self._canvas.size()
        self._update_figure()

    def _canvas_mouse_clicked(self, event):
        if (self._parameter_root['advanced_controller'].value and
                event.button == 1 and not self._no_lines_by_click):
            time = event.xdata
            table_ind = self._parameter_root['tb_names'].value[0]
            x_name = self._parameter_root['x_axis'].selected
            if x_name == self._index_name:
                time_array = self._get_index_array()
            else:
                time_array = (self._tables[table_ind][x_name])
            nearest_t, _ = self._get_nearest_value(time_array, time)
            if self._parameter_root['t0'].value in ['', None, 'None']:
                self._parameter_root['t0'].value = unicode(nearest_t)
                self._current_t = 't0'
            elif self._parameter_root['t1'].value in ['', None, 'None']:
                self._current_t = 't1'
                self._parameter_root['t1'].value = unicode(nearest_t)
            else:
                t0 = self._parameter_root['t0'].value
                t1 = self._parameter_root['t1'].value
                try:
                    t0 = float(t0)
                except:
                    pass
                try:
                    t1 = float(t1)
                except:
                    pass
                t_vals = np.array([t0, t1])

                t_str = ['t0', 't1']
                nearest_click, nearest_click_ind = self._get_nearest_value(
                    t_vals, time)
                try:
                    click_dist = np.abs(nearest_click - time)
                    x_ax = self._axes.get_xlim()
                    # If clicked close enough to one line, move that line.
                    if float(click_dist) / (x_ax[1] - x_ax[0]) < 0.05:
                        self._current_t = t_str[nearest_click_ind]
                    else:
                        self._current_t = None
                except:
                    self._current_t = None

                # Check if near lines. then move with mouse.
            self._actual_t = None
            self._update_figure(only_line_changed=True)
            self._pressed = True

    def _move_t(self, event):
        """Mouse motion."""
        if (self._pressed and
                self._parameter_root['advanced_controller'].value and
                self._current_t is not None and not self._no_lines_by_click):
            # Only do something if advanced plot controller activated and
            # mouse is pressed. Check if inside axis. Otherwise set line to
            # first/last t_value
            time = event.xdata
            table_ind = self._parameter_root['tb_names'].value[0]
            x_name = self._parameter_root['x_axis'].selected
            if x_name == self._index_name:
                time_array = self._get_index_array()
            else:
                time_array = (self._tables[table_ind]
                              [self._parameter_root['x_axis'].selected])
            nearest_t, _ = self._get_nearest_value(time_array, time)
            if self._current_t == 't0':
                self._parameter_root['t0'].value = nearest_t
            else:
                self._parameter_root['t1'].value = nearest_t
            self._actual_t = time
            self._update_figure(only_line_changed=True)

    def _canvas_mouse_released(self, event):
        """Mouse released."""
        self._pressed = False
        if (self._parameter_root['advanced_controller'].value and
                self._current_t is not None and not self._no_lines_by_click):
            self._actual_t = None
            time = event.xdata
            table_ind = self._parameter_root['tb_names'].value[0]
            x_name = self._parameter_root['x_axis'].selected
            if x_name == self._index_name:
                time_array = self._get_index_array()
            else:
                time_array = (self._tables[table_ind]
                              [self._parameter_root['x_axis'].selected])
            nearest_t, _ = self._get_nearest_value(time_array, time)
            if nearest_t is None:
                nearest_t = ''
            if self._current_t == 't0':
                self._parameter_root['t0'].value = unicode(nearest_t)
            elif self._current_t == 't1':
                self._parameter_root['t1'].value = unicode(nearest_t)
            self._update_figure(only_line_changed=True)

        self._current_t = None
        self._actual_t = None

    def _update_table(self):
        """Update table with values for curves."""
        self._ts_info_table.clear()
        y_list = self._parameter_root['y_axis'].value_names
        self._ts_info_table.setRowCount(len(y_list))
        self._ts_info_table.setColumnCount(3)
        row_labels = ['y(t0)', 'y(t1)', 'y(t1)-y(t0)']
        self._ts_info_table.setHorizontalHeaderLabels(row_labels)
        self._ts_info_table.setVerticalHeaderLabels(y_list)
        t0_nearest, t0_ind = self._get_t_value(
            self._parameter_root['t0'].value)
        t1_nearest, t1_ind = self._get_t_value(
            self._parameter_root['t1'].value)

        self._update_t(t0_nearest, t1_nearest)

        for ind, y_name in enumerate(y_list):
            self._update_y(ind, y_name, t0_ind, t1_ind)
        self._ts_info_table.resizeColumnsToContents()

    def _update_t(self, t0_nearest, t1_nearest):
        """Update values for t0, t1 and t diff."""
        if t0_nearest is None:
            self._t0_edit.setText('')
        else:
            self._t0_edit.setText(unicode(t0_nearest))
        if t1_nearest is None:
            self._t1_edit.setText('')
        else:
            self._t1_edit.setText(unicode(t1_nearest))
        self._set_tdiff(t0_nearest, t1_nearest)

    def _update_y(self, ind, y_name, t0_ind, t1_ind):
        """Update one table column."""
        # Get data and calculate y(t0), y(t1) and y(t1)-y(t0)
        if t0_ind is None:
            y0 = '--'
        else:
            y0 = self._get_y_value(y_name, t0_ind)
        if t1_ind is None:
            y1 = '--'
        else:
            y1 = self._get_y_value(y_name, t1_ind)
        try:
            y_diff = y1 - y0
        except:
            y_diff = '--'
        self._ts_info_table.setItem(
            ind, 0, QtGui.QTableWidgetItem(unicode(y0)))
        self._ts_info_table.setItem(
            ind, 1, QtGui.QTableWidgetItem(unicode(y1)))
        self._ts_info_table.setItem(
            ind, 2, QtGui.QTableWidgetItem(unicode(y_diff)))

    def _get_y_value(self, y_name, time_ind):
        """Get value at index time_ind in array with y_axis name."""
        # Get ts value at time_ind
        if time_ind is not None:
            table_index = self._parameter_root['tb_names'].value[0]
            y_array = self._tables[table_index][y_name]
            y_value = y_array[time_ind]
        else:
            y_value = None
        return y_value

    def _get_index_array(self):
        """Get array of index for the data."""
        table_index = self._parameter_root['tb_names'].value[0]
        nbr_points = len(self._tables[
            table_index][self._tables[table_index].dtype.names[0]])
        index_array = np.arange(0, nbr_points)
        return index_array

    def _get_t_value(self, time_str):
        """Get nearest time value from time_str and index for that value."""
        try:
            time = float(time_str)
            table_index = self._parameter_root['tb_names'].value[0]
            x_name = self._parameter_root['x_axis'].selected
            if x_name == self._index_name:
                time_array = self._get_index_array()
            else:
                time_array = (self._tables[table_index]
                              [self._parameter_root['x_axis'].selected])
            nearest, ind = self._get_nearest_value(time_array, time)
        except:
            nearest = None
            ind = None
        return nearest, ind

    def _get_nearest_value(self, time_array, time):
        """Get nearest value and index from array with times using time var."""
        try:
            ind = (np.abs(time_array - time)).argmin()
            return time_array[ind], ind
        except:
            return None, None

    def _t0_changed(self):
        """t0 line changed, update figure."""
        text = self._t0_edit.text()
        t_nearest, _ = self._get_t_value(unicode(text))
        self._parameter_root['t0'].value = unicode(t_nearest)
        self._set_tdiff(
            self._parameter_root['t0'].value, self._parameter_root['t1'].value)
        self._update_figure()

    def _t1_changed(self):
        """t1 line changed, update figure."""
        text = self._t1_edit.text()
        t_nearest, _ = self._get_t_value(unicode(text))
        self._parameter_root['t1'].value = unicode(t_nearest)
        self._set_tdiff(
            self._parameter_root['t0'].value, self._parameter_root['t1'].value)
        self._update_figure()

    def _set_tdiff(self, t0, t1):
        """Calculate t1-t0 and update tdiff edit."""
        try:
            diff = (float(t1) - float(t0))
            self._tdiff_edit.setText(unicode(diff))
        except:
            self._tdiff_edit.setText('')

    def _tb_names_change(self, index):
        """Update x_axis and y_axis comboboxes and update figure."""
        column_names = sorted(list(self._tables[index].dtype.names))
        x_axis_list = self._get_x_axis_list(column_names)
        x_editor = self._x_axis_combobox.editor()
        x_editor.blockSignals(True)
        x_editor.clear()
        x_editor.addItems(x_axis_list)
        x_editor.blockSignals(False)
        self._parameter_root['y_axis'].list = column_names
        self._parameter_root['y_axis'].value = [0]
        self._y_axis.editor().blockSignals(True)
        self._y_axis.editor().clear()
        self._y_axis.editor().addItems(column_names)
        self._y_axis.editor().blockSignals(False)
        self._update_figure()

    def _get_x_axis_list(self, column_names):
        """Append index_name to x_axis_list."""
        x_axis_list = []
        x_axis_list.extend(column_names)
        x_axis_list.append(self._index_name)
        x_axis_list.sort()
        return x_axis_list

    def _x_axis_change(self, index):
        """Update figure when x-axis has changed."""
        self._parameter_root['x_min'].value = 0
        self._parameter_root['x_max'].value = 0
        self._parameter_root['y_min'].value = 0
        self._parameter_root['y_max'].value = 0
        self._update_figure()

    def _y_axis_changed(self):
        """Update figure when y_axis selection changed"""
        self._parameter_root['y_min'].value = 0
        self._parameter_root['y_max'].value = 0
        self._update_figure()

    def _line_style_changed(self, index):
        """Update figure with new selected line style"""
        self._update_figure()

    def _enable_choices(self, state):
        """Enable or disable x-axis combo and line stylecombo"""
        self._enable_x_axis(state)
        self._enable_line(state)

    def _enable_line(self, state):
        """Enable or disable line style combo"""
        self._line_style_combobox.editor().setEnabled(state)

    def _enable_x_axis(self, state):
        """Enable or disable x-axis combo"""
        self._x_axis_combobox.editor().setEnabled(state)

    def _plot_func_changed(self):
        """Update figure with new plot function selection"""
        plot_func = self._parameter_root['plot_func'].selected
        if plot_func == 'plot':
            self._enable_choices(True)
        elif plot_func in ['fill', 'step']:
            self._enable_x_axis(True)
            self._enable_line(False)
        else:
            self._enable_choices(False)
        self._update_figure()

    def _update_figure(self, only_line_changed=False, lim=None):
        """Update figure"""
        self._update_background(only_line_changed=only_line_changed, lim=lim)
        self._plot_lines()
        self._restore_plot_parameters()

    def _resize_temp(self):
        size = self.size()
        h = size.height()
        w = size.width()
        size.setHeight(h + 5)
        size.setWidth(w + 5)
        self.resize(size)
        size.setWidth(w)
        size.setHeight(h)
        self.resize(size)
        self._update_figure()

    def _update_background(self, only_line_changed=False, lim=None):
        """Update canvas background."""
        if only_line_changed and self._background is not None and lim is None:
            self._canvas.restore_region(self._background)
        else:
            self._plot.update_figure(lim=lim)
            self._canvas.draw()
            self._background = self._canvas.copy_from_bbox(self._figure.bbox)

    def _plot_lines(self):
        """Plot lines on background."""
        if self._parameter_root['advanced_controller'].value:
            if self._actual_t is not None:
                if self._current_t == 't0':
                    self._t1_line = self._plot_or_update_line(
                        self._parameter_root['t1'].value, self._t1_line,
                        color=self._t_colors['t1'])
                    self._t0_line = self._plot_or_update_line(
                        self._actual_t, self._t0_line,
                        color=self._t_colors['t0'])
                elif self._current_t == 't1':
                    self._t0_line = self._plot_or_update_line(
                        self._parameter_root['t0'].value,
                        self._t0_line, color=self._t_colors['t0'])
                    self._t1_line = self._plot_or_update_line(
                        self._actual_t, self._t1_line,
                        color=self._t_colors['t1'])
            else:
                self._t0_line = self._plot_or_update_line(
                    self._parameter_root['t0'].value, self._t0_line,
                    color=self._t_colors['t0'])
                self._t1_line = self._plot_or_update_line(
                    self._parameter_root['t1'].value, self._t1_line,
                    color=self._t_colors['t1'])
            self._update_table()
            try:
                self._canvas.blit(self._figure.bbox)
            except:
                pass

    def _plot_or_update_line(self, t, line, color=None):
        """Plot or update data in line at time t."""
        if line is None:
            line = self._plot_line(t, color=color)
        else:
            self._update_plot_line(t, line)
        if line is not None and self._axes is not None:
            self._axes.draw_artist(line)
        return line

    def _plot_line(self, t, lim=None, color=None):
        """Plot line at time t."""
        try:
            t_float = float(t)
            line = self._plot.plot_line(
                t_float, animated=True, lim=lim, color=color)
        except:
            line = None
        return line

    def _update_plot_line(self, t, line, lim=None):
        """Update data for line line at time t."""
        try:
            t_float = float(t)
            self._plot.update_plot_line(t_float, line, lim=lim)
        except:
            pass

    def _hide_legend(self):
        """Hide or show legend."""
        self._parameter_root['visible_legend'].value = (
            not self._parameter_root['visible_legend'].value)
        xlim = self._figure.axes[0].get_xlim()
        ylim = self._figure.axes[0].get_ylim()
        lim = list(xlim)
        lim.extend(list(ylim))
        self._update_figure(lim=lim)

    def _advanced_controller_changed(self):
        """Activate/deactivate advanced plot controller."""
        self._parameter_root['advanced_controller'].value = (
            self._advanced_controller.isChecked())
        self._hide_advanced_controller()
        self._background = None
        self.update()
        self.repaint()
        self._update_figure()

    def _hide_advanced_controller(self):
        """Hide advanced controller if box unchecked. Else show controller."""
        self._hide_advanced_controller_custom(
            self._parameter_root['advanced_controller'].value)

    def _hide_advanced_controller_custom(self, state):
        """Hide advanced controller if state false. Else show controller."""
        if state:
            self._reset_button.show()
            self._t0_label.show()
            self._t0_edit.show()
            self._t1_label.show()
            self._t1_edit.show()
            self._tdiff_label.show()
            self._tdiff_edit.show()
            self._ts_info_table.show()
        else:
            self._reset_button.hide()
            self._t0_label.hide()
            self._t0_edit.hide()
            self._t1_label.hide()
            self._t1_edit.hide()
            self._tdiff_label.hide()
            self._tdiff_edit.hide()
            self._ts_info_table.hide()

    def _reset_lines(self):
        self._t0_edit.blockSignals(True)
        self._t1_edit.blockSignals(True)
        self._t0_edit.setText('')
        self._t1_edit.setText('')
        self._parameter_root['t0'].value = ''
        self._parameter_root['t1'].value = ''
        self._t0_line = None
        self._t1_line = None
        self._t0_edit.blockSignals(False)
        self._t1_edit.blockSignals(False)
        self._update_figure()

    def _zoom_changed(self, x_min, x_max, y_min, y_max):
        new_lim = [x_min, x_max, y_min, y_max]
        self._background = None
        self._update_figure(lim=new_lim)

    def _pan_active(self, state):
        self._no_lines_by_click = state

    def _zoom_active(self, state):
        self._no_lines_by_click = state

    def _pan_dragged(self, x_min, x_max, y_min, y_max):
        lim = [x_min, x_max, y_min, y_max]
        self._background = None
        self._update_figure(lim=lim)


class Scatter2dWidgetMultipleTb(PlotWidget):
    """Widget to plot a two dimensional scatter graph."""

    def __init__(self, node_context, tb_ts_dict, tb_name_dict, tb_dict,
                 units=None):
        super(Scatter2dWidgetMultipleTb, self).__init__(node_context)

        self._tb_ts_dict = tb_ts_dict
        self._tb_name_dict = tb_name_dict
        self._tb_dict = tb_dict
        self._units = units

        self._plot_list = None
        self._add_button = None
        self._remove_button = None

        self._init_gui()

    def _init_gui(self):
        max_height = 100
        max_width = 300

        # Create plot window.
        self._create_figure_gui()
        self._pre_init_gui_from_parameters()

        vlayout = QtGui.QVBoxLayout()

        axes_hlayout = QtGui.QHBoxLayout()
        axes_hlayout.setSpacing(20)

        self._x_axis_combobox = self._parameter_root['x_axis'].gui()
        self._y_axis = self._parameter_root['y_axis'].gui()
        self._line_style_combobox = self._parameter_root['line_style'].gui()
        self._plot_combobox = self._parameter_root['plot_func'].gui()

        self._add_button = QtGui.QPushButton('Add selection to plot list')
        self._remove_button = QtGui.QPushButton('Remove plot line')
        self._legend_button = QtGui.QPushButton('Show/hide legend')

        self._plot_list = QtGui.QListWidget()
        self._plot_list.setMaximumHeight(max_height)
        self._plot_list.setMaximumWidth(max_width)

        button_hlayout = QtGui.QHBoxLayout()
        button_hlayout.addWidget(self._add_button)
        button_hlayout.addWidget(self._remove_button)

        plot_list_vlayout = QtGui.QVBoxLayout()
        plot_list_vlayout.addLayout(button_hlayout)
        plot_list_vlayout.addWidget(self._plot_list)

        legend_vlayout = QtGui.QVBoxLayout()
        legend_vlayout.addSpacing(20)
        legend_vlayout.addWidget(self._legend_button)

        plot_style_hlayout = QtGui.QHBoxLayout()
        plot_style_hlayout.addWidget(self._line_style_combobox)
        plot_style_hlayout.addWidget(self._plot_combobox)
        plot_style_hlayout.addLayout(legend_vlayout)
        plot_style_hlayout.insertStretch(0)

        axes_vlayout = QtGui.QVBoxLayout()
        axes_vlayout.addWidget(self._x_axis_combobox)
        axes_vlayout.addWidget(self._y_axis)
        axes_vlayout.addLayout(plot_list_vlayout)

        # Create output layout
        self._create_output_layout()

        plot_vlayout = QtGui.QVBoxLayout()
        plot_vlayout.addLayout(plot_style_hlayout)
        plot_vlayout.addWidget(self._canvas)
        plot_vlayout.addWidget(self._toolbar)

        plot_splitlayout = QtGui.QSplitter(QtCore.Qt.Horizontal)
        axis_frame = QtGui.QFrame()
        axis_frame.setFrameShape(QtGui.QFrame.StyledPanel)
        axis_frame.setLayout(axes_vlayout)
        plot_splitlayout.addWidget(axis_frame)
        plot_frame = QtGui.QFrame()
        plot_frame.setFrameShape(QtGui.QFrame.StyledPanel)
        plot_frame.setLayout(plot_vlayout)
        plot_splitlayout.addWidget(plot_frame)

        outputs_widget = QtGui.QWidget()
        outputs_widget.setLayout(self._outputs_hlayout)
        policy = QtGui.QSizePolicy()
        policy.setVerticalPolicy(QtGui.QSizePolicy.Fixed)
        policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        outputs_widget.setSizePolicy(policy)

        vlayout.addWidget(plot_splitlayout)
        vlayout.addWidget(outputs_widget)
        self.setLayout(vlayout)

        self._init_gui_from_parameters()

        self._x_axis_combobox.editor().currentIndexChanged[int].connect(
            self._x_axis_change)
        self._line_style_combobox.editor().currentIndexChanged[int].connect(
            self._line_style_changed)
        self._plot_combobox.editor().currentIndexChanged.connect(
            self._plot_func_changed)
        self._add_button.clicked.connect(self._add_plot_line)
        self._remove_button.clicked.connect(self._remove_plot_line)
        self._legend_button.clicked.connect(self._hide_legend)

    def _pre_init_gui_from_parameters(self):
        """Init widgets already created in parameter_root"""
        if not self._parameter_root['x_axis'].list:
            if self._tb_name_dict is not None:
                self._parameter_root['x_axis'].list = self._tb_name_dict.keys()
            self._parameter_root['x_axis'].value = [0]

        if not self._parameter_root['y_axis'].list:
            if (self._tb_ts_dict is not None and
                    self._parameter_root['x_axis'].selected is not None):
                ts = (self._tb_ts_dict[
                    self._parameter_root['x_axis'].selected].keys())
                self._parameter_root['y_axis'].list = ts
                self._parameter_root['y_axis'].value_names = [ts[0]]
            self._parameter_root['y_axis'].value = [0]

        if not self._parameter_root['filename_extension'].list:
            supported_files_dict = (
                self._figure.canvas.get_supported_filetypes())
            supported_files = supported_files_dict.keys()
            supported_files = (
                ['.' + supported_file for supported_file in supported_files])
            self._parameter_root['filename_extension'].list = supported_files
            self._parameter_root['filename_extension'].value = [0]

    def _init_gui_from_parameters(self):
        try:
            self._parameter_root['display_strings']
        except:
            disp_group = self._parameter_root.create_group('display_strings')
            disp_group.set_list('plot_list')
            disp_group.set_list('tb_names')
            disp_group.set_list('ts_names')
        try:
            self._parameter_root['visible_legend']
        except:
            self._parameter_root.set_boolean('visible_legend', value=True)

        self._plot_list.addItems(
            self._parameter_root['display_strings']['plot_list'].list)
        self._plot = Scatter2dPlotMultipleTb(
            self._parameter_root, self._axes, self._tb_ts_dict,
            self._tb_name_dict, self._tb_dict, units=self._units)
        self._plot_func_changed()
        self._update_figure()

    def _x_axis_change(self, index):
        """Update y-axis and figure with new selected x-axis value"""
        column_names = (
            self._tb_ts_dict[self._parameter_root['x_axis'].selected].keys())
        self._y_axis.blockSignals(True)
        self._parameter_root['y_axis'].list = column_names
        self._parameter_root['y_axis'].value = []
        self._y_axis.editor().clear()
        self._y_axis.editor().addItems(column_names)
        self._y_axis.blockSignals(False)

    def _line_style_changed(self, index):
        """Update figure with new selected line style"""
        self._update_figure()

    def _enable_line(self, state):
        """Enable or disable line style combo"""
        self._line_style_combobox.editor().setEnabled(state)

    def _plot_func_changed(self):
        """Update plot function selection"""
        plot_func = self._parameter_root['plot_func'].selected
        if plot_func == 'plot':
            self._enable_line(True)
        else:
            self._enable_line(False)
        self._update_figure()

    def _update_figure(self):
        """Update figure"""
        self._plot.update_figure()
        self._canvas.draw()

    def _remove_plot_line(self):
        """Remove selected plot line and update figure."""
        ind = self._plot_list.currentRow()
        if ind >= 0:
            item = self._plot_list.currentItem().text()
            items = [self._plot_list.item(index).text()
                     for index in xrange(self._plot_list.count())]
            items.remove(item)
            del(self._parameter_root['display_strings']['plot_list'].list[ind])
            del(self._parameter_root['display_strings']['tb_names'].list[ind])
            del(self._parameter_root['display_strings']['ts_names'].list[ind])
            self._plot_list.clear()
            self._plot_list.addItems(items)
            self._update_figure()

    def _add_plot_line(self):
        """Add plot lines from selection to plot list and update figure."""
        x_axis_name = self._parameter_root['x_axis'].selected
        columns = self._parameter_root['y_axis'].value_names
        items = [self._plot_list.item(index).text()
                 for index in xrange(self._plot_list.count())]
        for column in columns:
            new_list_item = x_axis_name + ' -- ' + column
            if new_list_item not in items:
                items.append(new_list_item)
                self._parameter_root[
                    'display_strings']['plot_list'].list.append(new_list_item)
                self._parameter_root[
                    'display_strings']['tb_names'].list.append(x_axis_name)
                self._parameter_root[
                    'display_strings']['ts_names'].list.append(column)
        self._plot_list.clear()
        self._plot_list.addItems(items)
        self._update_figure()

    def _hide_legend(self):
        self._parameter_root['visible_legend'].value = (
            not self._parameter_root['visible_legend'].value)
        self._update_figure()


class Scatter3dWidget(PlotWidget):
    """Widget to plot a two dimensional scatter graph"""

    def __init__(self, node_context, tables, names=None, names_short=None,
                 units=None):
        """
        Args: tables (list): list of numpy recarrays
              names (list): list of names of the tables in tables
              tb_names (list): list of short time basis names,
                               corresponding to lo0ng names in names
              units: {table_name: {column_name1: column_unit1, ...}, ...}
        """
        super(Scatter3dWidget, self).__init__(node_context)
        # Init all variables not in PlotWidget
        self._tables = tables

        self._names_short = names_short
        if names is None:
            self._names = []
        else:
            self._names = names
        self._units = units
        self._z_axis_combobox = None
        self._tb_combobox = None
        self._projection = '3d'
        self._init_gui()

    def _init_gui(self):
        """Init GUI"""
        # Create plot window.
        self._create_figure_gui()
        self._pre_init_gui_from_parameters()
        vlayout = QtGui.QVBoxLayout()

        axes_hlayout = QtGui.QHBoxLayout()
        axes_hlayout.setSpacing(20)
        self._tb_combobox = self._parameter_root['tb_names'].gui()
        self._x_axis_combobox = self._parameter_root['x_axis'].gui()
        self._y_axis_combobox = self._parameter_root['y_axis'].gui()
        self._z_axis_combobox = self._parameter_root['z_axis'].gui()

        self._line_style_combobox = self._parameter_root['line_style'].gui()

        self._plot_combobox = self._parameter_root['plot_func'].gui()

        axes_hlayout.addWidget(self._tb_combobox)
        axes_hlayout.addWidget(self._x_axis_combobox)
        axes_hlayout.addWidget(self._y_axis_combobox)
        axes_hlayout.addWidget(self._z_axis_combobox)
        axes_hlayout.addWidget(self._line_style_combobox)
        axes_hlayout.addWidget(self._plot_combobox)
        axes_hlayout.insertStretch(-1)

        # Create outputlayout
        self._create_output_layout()

        vlayout.addItem(axes_hlayout)
        vlayout.addWidget(self._canvas)
        vlayout.addWidget(self._toolbar)
        vlayout.addLayout(self._outputs_hlayout)

        self.setLayout(vlayout)

        self._init_gui_from_parameters()

        self._x_axis_combobox.editor().currentIndexChanged[int].connect(
            self._x_axis_change)
        self._tb_combobox.editor().currentIndexChanged[int].connect(
            self._tb_names_change)
        self._y_axis_combobox.editor().currentIndexChanged[int].connect(
            self._y_axis_change)
        self._z_axis_combobox.editor().currentIndexChanged[int].connect(
            self._z_axis_change)
        self._line_style_combobox.editor().currentIndexChanged[int].connect(
            self._line_style_changed)
        self._plot_combobox.editor().currentIndexChanged.connect(
            self._plot_func_changed)
        self._figure.canvas.mpl_connect(
            'button_release_event', self._update_view)

    def _pre_init_gui_from_parameters(self):
        column_names = []
        if (self._tables is not None and len(self._tables) and
                self._tables[0] is not None):
            column_names = list(self._tables[0].dtype.names)

        if self._parameter_root['tb_names'].list and self._names:
            self._parameter_root['tb_names'].list = self._names
            self._parameter_root['tb_names'].value = [0]

        if not self._parameter_root['x_axis'].list:
            self._parameter_root['x_axis'].list = column_names
            self._parameter_root['x_axis'].value = [0]

        if not self._parameter_root['y_axis'].list:
            self._parameter_root['y_axis'].list = column_names
            self._parameter_root['y_axis'].value = [0]

        if not self._parameter_root['z_axis'].list:
            self._parameter_root['z_axis'].list = column_names
            self._parameter_root['z_axis'].value = [0]

        if not self._parameter_root['filename_extension'].list:
            supported_files_dict = (self._figure.canvas.
                                    get_supported_filetypes())
            supported_files = supported_files_dict.keys()
            supported_files = (['.' + supported_file
                                for supported_file in supported_files])
            self._parameter_root['filename_extension'].list = supported_files
            self._parameter_root['filename_extension'].value = [0]

    def _init_gui_from_parameters(self):
        """Init GUI from parameters"""
        # variables for figure view.
        try:
            self._parameter_root['azim']
        except:
            self._parameter_root.set_float('azim', value=-60)
        try:
            self._parameter_root['elev']
        except:
            self._parameter_root.set_float('elev', value=30)

        if len(self._names) == 0:
            self._tb_combobox.editor().setEnabled(False)

        self._plot = Plot3d(
            self._tables, self._parameter_root, self._figure, self._axes,
            self._names_short, self._units)
        self._plot_func_changed()
        self._update_figure()

    def _tb_names_change(self, index):
        """Update axis combobox items when timebasis is changed"""
        column_names = list(self._tables[index].dtype.names)
        x_editor = self._x_axis_combobox.editor()
        x_editor.blockSignals(True)
        x_editor.clear()
        x_editor.addItems(column_names)
        x_editor.blockSignals(False)
        y_editor = self._y_axis_combobox.editor()
        y_editor.blockSignals(True)
        y_editor.clear()
        y_editor.addItems(column_names)
        y_editor.blockSignals(False)
        z_editor = self._z_axis_combobox.editor()
        z_editor.blockSignals(True)
        z_editor.clear()
        z_editor.addItems(column_names)
        z_editor.blockSignals(False)
        self._update_figure()

    def _x_axis_change(self, index):
        """Update figure with new x_axis value"""
        self._update_figure()

    def _y_axis_change(self, index):
        """Update figure with new y_axis value"""
        self._update_figure()

    def _z_axis_change(self, index):
        """Update figure with new z_axis value"""
        self._update_figure()

    def _line_style_changed(self, index):
        """Update figure with new line_style"""
        self._update_figure()

    def _enable_line(self, state):
        """Enable or disable line style combo"""
        self._line_style_combobox.editor().setEnabled(state)

    def _plot_func_changed(self):
        """Update GUI and figure when plot function changed"""
        plot_func = self._parameter_root['plot_func'].selected
        if plot_func == 'plot':
            self._enable_line(False)
        elif plot_func == 'scatter':
            self._enable_line(True)
        else:
            self._enable_line(False)
        self._update_figure()

    def _update_figure(self):
        """Update figure"""
        self._plot.update_figure()
        try:
            self._canvas.draw()
        except ValueError:
            self._axes.clear()
            self._canvas.draw()

    def _update_view(self, event):
        """Update view when figure rotated"""
        self._plot.update_view()


class Plot2D(object):
    def __init__(self, parameter_root, axes):
        """Init plot"""
        self._axes = axes
        self._parameter_root = parameter_root

    def update_figure(self, lim=None):
        """Update figure. To be implemented in subclasses"""
        pass

    def plot_line(self, t, animated=False, lim=None, color=None):
        """Plot line in figure."""
        set_data = True
        if color is None:
            color = 'k-'
        if lim is None:
            ylim = self._axes.get_ylim()
        else:
            ylim = lim[2:4]
            if not (lim[0] <= t <= lim[1]):
                set_data = False
        if set_data and self._axes is not None:
            line, = self._axes.plot([t, t], ylim, color, animated=animated)
            return line
        else:
            return None

    def update_plot_line(self, t, line, lim=None):
        """Update plot line line in figure."""
        set_data = True

        if lim is None and self._axes is not None:
            ylim = self._axes.get_ylim()
        else:
            ylim = lim[2:4]
            if not (lim[0] <= t <= lim[1]):
                set_data = False
        if set_data:
            line.set_xdata([t, t])
            line.set_ydata(ylim)

    def _set_labels(self, x_column_name, x_units=[], y_units=[]):
        """Set labels on axes."""
        plot_func = self._parameter_root['plot_func'].selected
        set_labels = plot_func not in ['hist step', 'hist bar']
        if set_labels:
            if len(y_units) > 0 and self._axes is not None:
                self._axes.set_ylabel('[' + y_units[0] + ']')
            elif self._axes is not None:
                self._axes.set_ylabel('')
            if len(x_units) > 0:
                x_label = self._get_label(x_column_name, x_units[0])
            else:
                x_label = self._get_label(x_column_name, '')
        x_label = ''
        if self._axes is not None:
            self._axes.set_xlabel(x_label)
            if self._parameter_root['visible_legend'].value:
                self._axes.legend()

    def _plot_x_y(self, x_data, y_data, y_column_name, y_unit=None):
        """Plot x_data and y_data with y_column_name and y_unit as legend"""
        plot_func = self._parameter_root['plot_func'].selected
        line_style = self._parameter_root['line_style'].selected
        if y_unit is None:
            y_unit = ''
        if type(y_unit) is list:
            y_unit = ', '.join(y_unit)
        if np.all(np.isreal(x_data)) and np.all(np.isreal(y_data)):
            if y_unit not in ['', 'unknown']:
                y_unit_label = ' [' + y_unit + ']'
            else:
                y_unit_label = ''
            y_label = (unicode(y_column_name) + unicode(y_unit_label))
            if self._axes is not None:
                if plot_func == 'hist step':
                    self._axes.hist(y_data, 50, histtype='step', label=y_label)
                elif plot_func == 'plot':
                    self._axes.plot(x_data, y_data, line_style, label=y_label)
                elif plot_func == 'step':
                    self._axes.step(x_data, y_data, label=y_label)
                elif plot_func == 'fill':
                    self._axes.fill(x_data, y_data, label=y_label)
                elif plot_func == 'hist bar':
                    self._axes.hist(y_data, 50, histtype='bar', label=y_label)
                else:
                    pass

    def _get_units(self, x_column_name, y_column_name, table_index=None):
        """Get units of axis. To be implemented by subclasses."""
        pass

    def _get_special_unit(self, unit):
        """Handle deg, ^2, ^3 in units"""
        if u'\xb0' in unit:
            unit_temp = unit.split(u'\xb0')
            unit = r'$^\circ$'.join(unit_temp)
        elif u'\xb2' in unit:
            unit_temp = unit.split(u'\xb2')
            unit = '$^2$'.join(unit_temp)
        elif u'\xb3' in unit:
            unit_temp = unit.split(u'\xb3')
            unit = '$^3$'.join(unit_temp)
        return unit

    def _get_label(self, column_name, unit=''):
        """Get axis label"""
        if unit != 'unknown' and unit != '':
            label = unicode(column_name) + ' [' + unit + ']'
        else:
            label = unicode(column_name)
        return label

    def _is_valid_units_tb(self):
        """Check if units not None and if tb_names not empty"""
        return (self._units is not None)


class Scatter2dPlot(Plot2D):
    def __init__(self, tables, parameter_root, axes, index_name=None):
        super(Scatter2dPlot, self).__init__(
            parameter_root, axes)
        self._tables = tables
        self._index_name = index_name

    def update_figure(self, lim=None):
        """Update figure"""
        x_column_name = ''
        x_data = []
        y_data = []
        y_units = []
        x_units = ''

        if self._axes is not None:
            self._axes.clear()
        if len(self._parameter_root['x_axis'].value):
            x_column_name = self._parameter_root['x_axis'].list[
                self._parameter_root['x_axis'].value[0]]
        else:
            x_column_name = self._parameter_root['x_axis'].list[0]
        y_column_names = self._parameter_root['y_axis'].value_names
        table_index = self._parameter_root['tb_names'].value[0]

        if len(self._tables) and self._tables[table_index] is not None:
            if x_column_name == self._index_name:
                x_data = np.arange(
                    0, self._tables[table_index].number_of_rows())
            elif x_column_name in self._tables[table_index]:
                x_data = self._tables[table_index].get_column_to_array(
                    x_column_name)

            # Get units for axis
            if len(self._parameter_root['tb_names'].list) > 0:
                x_units = self._get_units(x_column_name, table_index)

            for y_column_name in y_column_names:
                y_data = self._tables[table_index].get_column_to_array(
                    y_column_name)
                y_unit = self._get_units(y_column_name, table_index)
                y_units.append(y_unit)
                # Only plot real numbers

                self._plot_x_y(x_data, y_data, y_column_name, y_unit)

        # Add y-label if units exist, all y-axis columns have same units
        # and unit nos unknown.
        if lim is not None and self._axes is not None:
            self._axes.set_ylim(lim[2:4])
            self._axes.set_xlim(lim[0:2])
        self._set_labels(x_column_name, [x_units], y_units)
        self._restore_plot_parameters()

    def _restore_plot_parameters(self):
        axis = self._axes
        x_min = self._parameter_root['x_min'].value
        x_max = self._parameter_root['x_max'].value
        if x_min < x_max:
            axis.set_xlim((x_min, x_max))
        y_min = self._parameter_root['y_min'].value
        y_max = self._parameter_root['y_max'].value
        if y_min < y_max:
            axis.set_ylim((y_min, y_max))
        axis.set_title(self._parameter_root['title'].value)
        axis.set_xlabel(self._parameter_root['xlabel'].value)
        axis.set_ylabel(self._parameter_root['ylabel'].value)

    def _get_units(self, column_name, table_index=0):
        """Get units of axis and handle deg to be displayed correctly in
        plot.
        """
        attrs = {}
        unit = ''
        if 'unit' in attrs:
            return self._get_special_unit(unit)
        else:
            return ''

    def _is_valid_units_tb(self):
        """Check if units not None and if tb_names not empty"""
        return (self._units is not None and
                len(self._parameter_root['tb_names'].list) > 0)


class Scatter2dPlotMultipleTb(Plot2D):
    def __init__(self, parameter_root, axes, tb_ts_dict, tb_names, tb_dict,
                 units=None):

        super(Scatter2dPlotMultipleTb, self).__init__(parameter_root, axes)
        self._tb_ts_dict = tb_ts_dict
        self._tb_names = tb_names
        self._tb_dict = tb_dict
        self._units = units

    def update_figure(self, lim=None):
        """Update figure"""
        if self._axes is not None:
            self._axes.clear()
        y_units = []
        plot_list = self._parameter_root['display_strings']['plot_list'].list
        for ind, plot_line in enumerate(plot_list):
            x_column_name = (
                self._parameter_root['display_strings']['tb_names'].list[ind])
            y_column_name = (
                self._parameter_root['display_strings']['ts_names'].list[ind])

            x_data = self._tb_dict[x_column_name]
            y_data = self._tb_ts_dict[x_column_name][y_column_name]
            y_unit = self._get_units(x_column_name, y_column_name)
            if y_unit != '':
                y_units.append(y_unit)
            self._plot_x_y(x_data, y_data, y_column_name, y_unit)
        self._set_labels('time', y_units=y_units)

    def _get_units(self, x_column_name, y_column_name, table_index=None):
        """Get units of axis and handle deg to be displayed correctly in
        plot.
        """
        unit = ''
        if self._units is not None:
            unit = self._units[x_column_name][y_column_name]
            unit = self._get_special_unit(unit)
        return unit


class Plot3d(object):
    def __init__(self, tables, parameter_root, fig, axes,
                 names_short=None, units=None, cb=None):
        self._fig = fig
        self._axes = axes
        self._parameter_root = parameter_root
        self._tables = tables
        self._units = units
        self._tb_names_short = names_short
        self._cb = cb
        self._nbr_points = 100
        self._2d_axes = False
        self._rotation = None

    def update_figure(self):
        """Update figure"""
        x_column_name = ''
        x_data = []
        y_data = []
        z_data = []

        plot_func = self._parameter_root['plot_func'].selected
        table_index = self._parameter_root['tb_names'].value[0]

        if len(self._parameter_root['x_axis'].list):
            x_column_name = self._parameter_root[
                'x_axis'].list[self._parameter_root['x_axis'].value[0]]

        y_column_name = self._parameter_root['y_axis'].selected
        z_column_name = self._parameter_root['z_axis'].selected

        if (self._tables is not None and len(self._tables) and
                self._tables[table_index] is not None):
            x_data = self._tables[table_index][x_column_name]
            y_data = self._tables[table_index][y_column_name]
            z_data = self._tables[table_index][z_column_name]

        if self._axes is not None:
            self._axes.clear()
            if not self._2d_axes:
                self._axes.mouse_init()
        if len(self._parameter_root['tb_names'].list) > 0:
            tb_name = self._parameter_root['tb_names'].selected

        # Get units for axis
        if (self._units is not None and
                len(self._parameter_root['tb_names'].list) > 0):
            x_units = self._get_units(tb_name, x_column_name, table_index)
            y_units = self._get_units(tb_name, y_column_name, table_index)
            z_units = self._get_units(tb_name, z_column_name, table_index)

        else:
            x_units = ''
            y_units = ''
            z_units = ''

        # Only plot real numbers
        if (np.all(np.isreal(x_data)) and np.all(np.isreal(y_data)) and
                np.all(np.isreal(z_data))):
            if plot_func == 'surf':
                self._axes_2d_to_3d()
                if len(x_data) >= 1 and len(y_data) >= 1 and len(z_data) >= 1:
                    self._surf_plot(x_data, y_data, z_data)
            elif plot_func == 'contour':
                self._axes_2d_to_3d()
                if len(x_data) >= 1 and len(y_data) >= 1 and len(z_data) >= 1:
                    self._contour_plot(x_data, y_data, z_data)
            elif plot_func == 'scatter':
                self._axes_2d_to_3d()
                self._check_cb()
                if self._axes is not None:
                    self._axes.scatter(
                        x_data, y_data, z_data,
                        marker=self._parameter_root['line_style'].selected)
                self._cb = None
            elif plot_func == 'plot':
                self._axes_2d_to_3d()
                self._check_cb()
                if self._axes is not None:
                    self._axes.plot(x_data, y_data, z_data)
                self._cb = None
            elif plot_func == 'wireframe':
                self._axes_2d_to_3d()
                self._wireframe_plot(x_data, y_data, z_data)
            elif plot_func == 'heatmap':
                self._heatmap_plot(
                    x_data, y_data, z_data, z_column_name, z_units)
            else:
                pass
        if self._axes is not None:
            self._axes.set_xlabel(self._get_label(x_column_name, x_units))
            self._axes.set_ylabel(self._get_label(y_column_name, y_units))
        if not self._2d_axes and self._axes is not None:
            self._axes.azim = self._parameter_root['azim'].value
            self._axes.elev = self._parameter_root['elev'].value
            self._axes.set_zlabel(self._get_label(z_column_name, z_units))

    def update_view(self):
        """Update figure rotation if 3d figure"""
        if not self._2d_axes and self._axes is not None:
            self._parameter_root['azim'].value = self._axes.azim
            self._parameter_root['elev'].value = self._axes.elev

    def _get_label(self, column_name, unit):
        """Get axis label"""
        if self._units is not None and unit != 'unknown' and unit != '':
            label = unicode(column_name) + ' [' + unit + ']'
        else:
            label = unicode(column_name)
        return label

    def _interpolate_data(self, data):
        """Linear interpolation of data when data more than predefined
        nbr of points.
        """
        len_data = len(data)
        if len_data > self._nbr_points:
            x_interp = range(0, len_data)
            new_x_points = np.linspace(0, len_data - 1, self._nbr_points)
            new_data = np.interp(new_x_points, x_interp, data)
            return new_data
        return data

    def _interpolate_all(self, x_data, y_data, z_data):
        """Interpolate x_data, y_data and z_data"""
        x_data_new = self._interpolate_data(x_data)
        y_data_new = self._interpolate_data(y_data)
        z_data_new = self._interpolate_data(z_data)
        return x_data_new, y_data_new, z_data_new

    def _surf_plot(self, x_data, y_data, z_data):
        """3d surface plot"""
        x_data_new, y_data_new, z_data_new = self._interpolate_all(
            x_data, y_data, z_data)
        X, Y, Z = self._get_xyz(
            x_data_new, y_data_new, z_data_new)
        self._check_cb()
        if self._axes is not None:
            surf = self._axes.plot_surface(
                X, Y, Z, cmap=cm.coolwarm, rstride=1, cstride=1,
                linewidth=0, antialiased=False)

        if len(x_data) > 1 and len(y_data) > 1 and len(z_data) > 1:
            self._cb = self._fig.colorbar(surf, format='%d')  # ?????
        else:
            self._cb = None

    def _contour_plot(self, x_data, y_data, z_data):
        """3d contour plot"""
        x_data_new, y_data_new, z_data_new = self._interpolate_all(
            x_data, y_data, z_data)
        X, Y, Z = self._get_xyz(
            x_data_new, y_data_new, z_data_new)
        if self._axes is not None:
            cset = self._axes.contour(X, Y, Z, cmap=cm.coolwarm)
            self._axes.clabel(cset, fontsize=9, inline=1)
        self._check_cb()
        self._cb = None

    def _wireframe_plot(self, x_data, y_data, z_data):
        """3d wireframe plot"""
        x_data_new, y_data_new, z_data_new = self._interpolate_all(
            x_data, y_data, z_data)
        X, Y, Z = self._get_xyz(
            x_data_new, y_data_new, z_data_new)
        if self._axes is not None:
            self._axes.plot_wireframe(
                X, Y, Z, rstride=1, cstride=1, alpha=0.4)
        self._check_cb()
        self._cb = None

    def _heatmap_plot(self, x_data, y_data, z_data, z_column_name, z_units):
        """2d heatmap plot with z_axis as colour"""
        x_data_new, y_data_new, z_data_new = self._interpolate_all(
            x_data, y_data, z_data)
        X, Y, Z = self._get_xyz(
            x_data_new, y_data_new, z_data_new)

        x = X.ravel()
        y = Y.ravel()
        z = Z.ravel()
        gridsize = 30

        self._check_cb()
        self._fig.delaxes(self._axes)
        self._axes = self._fig.add_subplot(111)
        self._2d_axes = True

        if (len(x_data) > 1 and len(y_data) > 1 and len(z_data) > 1 and
                self._axes is not None):
            heat = self._axes.hexbin(
                x, y, C=z, gridsize=gridsize, cmap=cm.jet, bins=None)
            self._axes.axis([x.min(), x.max(), y.min(), y.max()])
            self._cb = self._fig.colorbar(heat)
            z_label = self._get_label(z_column_name, z_units)
            self._cb.set_label(z_label)
        else:
            self._cb = None

    def _axes_2d_to_3d(self):
        """Create new 3d figure and delete old figure"""
        self._check_cb()
        if self._axes is not None:
            self._fig.delaxes(self._axes)
        self._axes = Axes3D(self._fig)
        self._2d_axes = False

    def _check_cb(self):
        """Check if colorbar exists, and then delete it"""
        if self._cb:
            try:
                self._fig.delaxes(self._fig.axes[1])
            except:
                pass

    def _get_units(self, tb_name, column_name, table_index):
        """Get units of axis and handle deg to be displayed correctly in
        plot.
        """
        try:
            unit = self._units[tb_name][column_name]
        except:
            try:
                if (column_name) == self._tb_names_short[table_index]:
                    unit = self._units[tb_name][(
                        self._parameter_root['tb_names'].list[
                            table_index])]
                else:
                    unit = ''
            except:
                unit = ''
        # Handle deg in units
        if '\xb0' in unit:
            unit_temp = unit.split('\xb0')
            unit = r'$^\circ$'.join(unit_temp)
        return unit

    def _get_xyz(self, x_data, y_data, z_data):
        """Get matrices X,Y,Z from 1D arrays"""
        x, y = np.meshgrid(x_data, y_data)
        z = np.tile(z_data, (len(z_data), 1))
        return x, y, z
