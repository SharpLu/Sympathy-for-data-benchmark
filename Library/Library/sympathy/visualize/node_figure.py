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
"""
A set of nodes to generate and manipulate Figures in a programmatic way
(type: Figure).

The node :ref:`Figure from Table with Table` allows to configure a figure with
a configuration table. The :ref:`Figure Compressor` node allows to compress a
list of Figures into one single Figure, while the
:ref:`Layout Figures in Subplots` generates a Figure with subplots. Figures
can be exported using the :ref:`Export Figures` node.

The configuration table consists of one parameter and a value column.
Currently properties can be set for the *line*, *axes* and *figure*
parameters.

Line
----

Every line/scatter is addressed with a unique
identifier *{id}*, which can be any string without a '.'. A
line parameter is constructed as with *line.{id}.{property}*
in the parameter column and the corresponding value in the
value column. Every line needs to have at least the 'xdata'
and 'ydata' specified. All line properties, except the 'ydata',
can also be given on a *global* level like *line.{property}*.
All properties given on a global level with be copied to all
configured lines without overriding locally declared properties.

Currently supported properties are (some properties allow
alternative names *longname/shortname*):

===================== =====================
Property              Type
===================== =====================
xdata                 unicode
ydata                 unicode
axes                  *axes id* (see below)
label                 unicode
marker                matplotlib marker (e.g. 'o', '.', '^', 'd', etc)
markersize            float
markeredgecolor       mpl color (see below)
markeredgewidth       float
markerfacecolor       mpl color (see below)
linestyle             matplotlib line style (e.g. '-', '--', '.-', etc)
linewidth             float
color                 mpl color (see below)
alpha                 float [0., 1.]
zorder                number
drawstyle             matplotlib drawstyle (e.g. default, steps, etc.)
===================== =====================

Please see the matplotlib_ documentation for sensible values of the
different types.

.. _matplotlib: http://matplotlib.org/api/lines_api.html

Example
^^^^^^^
An example assigning the 'index' column as x values and the
'SIGNAL' column as y values to a line with id='1', as well as
drawing it in red with a circular marker:

    ================ ================
    Parameters       Values
    ================ ================
    line.1.xdata     index
    line.1.ydata     SIGNAL
    line.1.color     red
    line.1.marker    o
    ================ ================

Axes
----

Axes are defined similar than lines. Currently different axes
correspond to different (x,y) axes which are overlaid on top
of each other. Every axes has also a unique identifier *{id}*
(without '.'). The parameter name is constructed as
*axes.{id}.{property}* on the local level or *axes.{property}*
for global properties, valid for all defined axes.

===================== =====================
Property              Type
===================== =====================
xaxis                 axes type ('x', 'x1', 'x2')
yaxis                 axes type ('y', 'y1', 'y2')
title                 unicode
xlabel                unicode
ylabel                unicode
xlim                  str of two comma separated numbers
ylim                  str of two comma separated numbers
xscale                'linear' or 'log'
yscale                'linear' or 'log'
aspect                'auto', 'equal' or float
grid                  GRID (see below)
legend                LEGEND (see below)
===================== =====================

Grid
^^^^

Every axes can also have a grid with the following optional
properties:

===================== =====================
Property              Type
===================== =====================
                      bool
color                 mpl color (see below)
linestyle             matplotlib line style (e.g. '-', '--', '.-', etc)
linewidth             float
which                 'major', 'minor', 'both'
axis                  'both', 'x', 'y'
===================== =====================

Legend
^^^^^^

Every axes can also have a legend defined with the following
optional properties:

===================== =====================
Property              Type
===================== =====================
                      bool
loc                   mpl legend location (e.g. 'best', 'upper left')
ncol                  int
fontsize              e.g. 'x-small', 'medium', 'x-large', etc
markerfirst           bool
frameon               bool
title                 unicode
===================== =====================


Example
^^^^^^^

The example defines two axes, one (id=xy) with the y axis
on the left ('y1') and the other (id=foo) with the y axis
on the right ('y2') while sharing the bottom x axis ('x1').
Since the xaxis is shared between the two axes, it is defined
on the global level. For the *xy*, a legend will be shown in
the upper left corner, while the *foo* axes will have a green
grid.

    =================== ===================
    Parameters          Values
    =================== ===================
    axes.xaxis          x1
    axes.xy.yaxis       y1
    axes.xy.xlabel      The xy xlabel
    axes.xy.ylabel      The xy ylabel
    axes.xy.legend      True
    axes.xy.legend.loc  upper left
    axes.foo.yaxis      y2
    axes.foo.ylabel     The y2 ylabel
    axes.foo.grid       True
    axes.foo.grid.c     green
    =================== ===================

MPL colors
^^^^^^^^^^

All properties with *mpl colors* values expect a string with
either a hex color (with or without extra alpha channel), 3 or 4
comma separated integers for the RGBA values (range [0, 255]),
3 or 4 comma separated floats for the RGBA values (range [0., 1.])
or a matplotlib color_ name (e.g. 'r', 'red', 'blue', etc.).

.. _color: http://matplotlib.org/examples/color/named_colors.html
"""
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import os
import itertools
import functools

import six

import numpy as np

from sympathy.api import qt as qt_compat
from sympathy.api import node as synode
from sympathy.api import exporters
from sympathy.api import datasource as dsrc
from sympathy.api import ParameterView
from sympathy import api
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags

QtCore = qt_compat.QtCore
QtGui = qt_compat.QtGui
qt_compat.backend.use_matplotlib_qt()

from sylib.figure import util
import sympathy.platform.widget_library as sywidgets


class SuperNodeFigureWithTable(synode.Node):
    author = 'Benedikt Ziegler <benedikt.ziegler@combine.se>'
    copyright = '(c) 2016 Combine AB'
    version = '0.1'
    icon = 'figure.svg'
    tags = Tags(Tag.Visual.Figure)

    parameters = synode.parameters()
    parameters.set_list(
        'parameters', label='Parameters:', value=[0],
        description='The column which identifies the column '
                    'containing the parameter names.',
        editor=synode.Util.combo_editor().value())
    parameters.set_list(
        'values', label='Values:', value=[1],
        description='The column which identifies the column '
                    'containing the parameter values.',
        editor=synode.Util.combo_editor().value())

    def verify_parameters(self, node_context):
        parameters = node_context.parameters
        param_list = [] != parameters['parameters'].list
        value_list = [] != parameters['values'].list
        return param_list and value_list

    def adjust_parameters(self, node_context):
        config_input = node_context.input['config']
        parameters = node_context.parameters
        if config_input.is_valid():
            column_names = config_input.column_names()
            for i, p_name in enumerate(['parameters', 'values']):
                parameters[p_name].list = column_names
        return node_context

    def execute(self, node_context):
        config_table = node_context.input['config']

        parameters = node_context.parameters

        column_names = config_table.column_names()
        param_col = parameters['parameters'].value[0]
        value_col = parameters['values'].value[0]
        param_col_name = column_names[param_col]
        value_col_name = column_names[value_col]
        param_names = config_table.get_column_to_array(param_col_name)
        param_values = config_table.get_column_to_array(value_col_name)
        configuration = zip(param_names, param_values)

        figure_param = util.parse_configuration(configuration)

        self._create_figure(node_context, figure_param)


class FigureFromTableWithTable(SuperNodeFigureWithTable):
    """
    Create a Figure from a Table using a table for configuration.

    :Inputs:
        **input** : Table
            Table with data.
        **config** : Table
            Table with at least a parameter and value column which
            will be auto selected by the node or which the user
            can specify in the GUI.
    :Outputs:
        **figure** : Figure
            A Figure with the configured axes, lines, labels, etc.
    :Configuration:
        **Parameters**
            The column specifying the parameters.
        **Values**
            The column specifying the corresponding values.
    """

    name = 'Figure from Table with Table'
    description = ('Create a Figure from a Table using a '
                   'configuration Table')
    nodeid = 'org.sysess.sympathy.visualize.figurefromtablewithtable'

    inputs = Ports([Port.Table('Input data', name='input'),
                    Port.Table('Configuration', name='config')])
    outputs = Ports([Port.Figure('Output figure', name='figure')])

    def _create_figure(self, node_context, figure_param):
        data_table = node_context.input['input']
        figure = node_context.output['figure']

        figure_creator = util.CreateFigure(data_table, figure, figure_param)
        figure_creator.create_figure()


class FiguresFromTablesWithTable(SuperNodeFigureWithTable):
    """
    Create Figures from List of Tables using a table for configuration.

    :Inputs:
        **input** : [Table]
            Table with data.
        **config** : Table
            Table with at least a parameter and value column which
            will be auto selected by the node or which the user
            can specify in the GUI.
    :Outputs:
        **figure** : [Figure]
            A Figure with the configured axes, lines, labels, etc.
    :Configuration:
        **Parameters**
            The column specifying the parameters.
        **Values**
            The column specifying the corresponding values.
    """

    name = 'Figures from Tables with Table'
    description = ('Create Figures from List of Tables using a '
                   'configuration Table')
    nodeid = 'org.sysess.sympathy.visualize.figuresfromtableswithtable'

    inputs = Ports([Port.Tables('Input data', name='input'),
                    Port.Table('Configuration', name='config')])
    outputs = Ports([Port.Figures('Output figure', name='figure')])

    def _create_figure(self, node_context, figure_param):
        data_tables = node_context.input['input']
        figures = node_context.output['figure']

        for i, data_table in enumerate(data_tables):
            figure = api.figure.File()
            figure_creator = util.CreateFigure(
                data_table, figure, figure_param)
            figure_creator.create_figure()

            figures.append(figure)

            self.set_progress(100 * (i + 1) / len(data_tables))


class FigureCompressor(synode.Node):
    """
    Compress a list of Figures into one Figure.

    :Inputs:
        **input** : [Figure]
            List of Figures.
    :Outputs:
        **figure** : Figure
            A Figure with the configured axes, lines, labels, etc.
    :Configuration:
        **Parent Figure**
            Specify with figure from the input list will be used
            to take axes properties from.
        **Join legends**
            Set True, if legends of different overlaying twin axes
            should be shown in the same legend.
        **Legend position**
            The position of the join legend. Default 'best'.
    :Ref. nodes: :ref:`Figure from Table with Table`
    """
    author = 'Benedikt Ziegler <benedikt.ziegler@combine.se>'
    copyright = '(c) 2016 Combine AB'
    version = '0.1'
    icon = 'figurecompressor.svg'
    name = 'Figure Compressor'
    description = 'Compress a list of Figures to a single figure'
    nodeid = 'org.sysess.sympathy.visualize.figurecompressorgui'
    tags = Tags(Tag.Visual.Figure)

    parameters = synode.parameters()
    parameters.set_list(
        'parent_figure', value=[0], label='Parent figure:',
        description='Specify the figure from which axes parameters '
                    'and legend position are copied.',
        editor=synode.Util.combo_editor().value())
    parameters.set_boolean(
        'join_legends', value=True, label='Join legends',
        description='Set if legends from different axes should be '
                    'joined into one legend.')
    parameters.set_list(
        'legend_location', value=[0], label='Legend position:',
        plist=sorted(util.LEGEND_LOC.keys()),
        description='Defines the position of the joined legend.',
        editor=synode.Util.combo_editor().value())
    parameters.set_boolean(
        'auto_recolor', value=False, label='Auto recolor lines',
        description='Automatically recolor all lines to avoid using a color '
                    'multiple times, if possible.')
    parameters.set_boolean(
        'auto_rescale', value=True, label='Auto rescale axes',
        description='Automatically rescale all axes to fit the visible data.')

    controllers = (
        synode.controller(
            when=synode.field('join_legends', 'checked'),
            action=synode.field('legend_location', 'enabled')))

    inputs = Ports([Port.Figures('Input data', name='input')])
    outputs = Ports([Port.Figure('Output figure', name='figure')])

    def adjust_parameters(self, node_context):
        input_figure = node_context.input['input']
        if not input_figure.is_valid():
            input_figure = []
        parameters = node_context.parameters
        parameters['parent_figure'].list = [str(i) for i in
                                            range(len(input_figure))]
        return node_context

    def execute(self, node_context):
        input_figures = node_context.input['input']
        output_figure = node_context.output['figure']
        parameters = node_context.parameters

        parent_figure_number = parameters['parent_figure'].value[0]

        input_axes = [figure.get_mpl_figure().axes for figure in input_figures]
        default_output_axes = output_figure.first_subplot().get_mpl_axes()

        util.compress_axes(input_axes, default_output_axes,
                           parameters['join_legends'].value,
                           parameters['legend_location'].selected,
                           int(parent_figure_number),
                           auto_recolor=parameters['auto_recolor'].value,
                           auto_rescale=parameters['auto_rescale'].value)


class ExportFigures(synode.Node):
    """
    Export Figures to a selected data format.

    :Inputs:
        **Figures** : [Figure]
            List of figures to export.
    :Outputs:
        **Datasources** : [Datasource]
            Datasources with path to the created file.
    :Configuration:
        **Output directory**
            Specify/select directory where the created files will be stored.
        **Filename**
            Specify the common base for the filenames. If there are several
            incoming Figures the node will add "_${index number of
            corresponding Figure in the incoming list}" after the base for
            each file. Do not specify extension.
        **Filename extension**
            Specify the extension used to export the figures.
        **Filename(s) preview** : button
            When pressed a preview of all filenames will be presented under the
            considered button.
    :Ref. nodes: :ref:`Figure from Table with Table`
    """

    author = 'Benedikt Ziegler <benedikt.ziegler@combine.se>'
    copyright = '(c) 2016 Combine AB'
    version = '0.1'
    icon = 'export_figure.svg'
    name = 'Export Figures'
    description = 'Export Figures to image files.'
    nodeid = 'org.sysess.sympathy.export.exportfigures'
    tags = Tags(Tag.Output.Export)

    inputs = Ports([Port.Figures('Input figures', name='figures')])
    outputs = Ports([Port.Datasources(
        'Datasources', name='port0', scheme='text')])

    parameters = synode.parameters()
    parameters.set_string(
        'directory', value='.', label='Output directory',
        description='Select the directory where to export the files.',
        editor=synode.Util.directory_editor().value())
    parameters.set_string(
        'filename', label='Filename',
        description='Filename without extension.')
    parameters.set_list(
        'extension',
        label='Filename extension:',
        description='The extension to be used for exporting the figures.',
        value=[1],
        plist=['eps', 'pdf', 'svg', 'png'],
        editor=synode.Util.combo_editor().value())
    parameters.set_integer(
        'width',
        label='Image width (px):',
        description='The image width in pixels.',
        value=800,
        editor=synode.Util.bounded_spinbox_editor(100, 1000000000, 1).value())
    parameters.set_integer(
        'height',
        label='Image height (px):',
        description='The image height in pixels.',
        value=600,
        editor=synode.Util.bounded_spinbox_editor(100, 1000000000, 1).value())

    def execute(self, node_context):
        parameters = node_context.parameters
        input_list = node_context.input['figures']
        number_of_objects = len(input_list)
        datasource_list = node_context.output['port0']

        width = parameters['width'].value
        height = parameters['height'].value

        directory = parameters['directory'].value
        if not os.path.isdir(directory):
            os.makedirs(directory)
        filename = parameters['filename'].value
        extension = parameters['extension'].selected
        fq_filenames = exporters.base.create_fq_filenames(
            directory, self._create_filenames(node_context.input,
                                              filename,
                                              extension))

        for object_no, (figure, fq_filename) in enumerate(
                itertools.izip(input_list, fq_filenames)):
            figure.save_figure(fq_filename, size=(width, height))

            datasource_file = dsrc.File()
            datasource_file.encode_path(fq_filename)
            datasource_list.append(datasource_file)

            self.set_progress(
                    100.0 * (1 + object_no) / number_of_objects)

    def _create_filenames(self, node_context_input, filename, ext):
        figurelist = node_context_input['figures']
        filenames = ('{}_{}.{}'.format(filename, i, ext)
                     for i in range(len(figurelist)))
        return filenames


class SubplotFigures(synode.Node):
    """
    Layout the Figures in a list of Figures into subplots.

    The number of rows and columns is automatically adjusted to a
    square pattern, but removing empty rows. Empty axes in a
    non-empty row will be not shown.

    :Inputs:
        **input** : [Figure]
            List of Figures.
    :Outputs:
        **figure** : Figure
            A Figure with several subplot axes.
    :Configuration:
        **Number of rows**
            Specify how many rows of subplots the figure should have.
            If set to 0, the number of rows will be set to show all
            input figures, depending on the number or columns. If rows
            and columns are 0, the axes layout will be square.
        **Number of columns**
            Specify how many columns of subplots the figure should have.
            If set to 0, the number of columns will be set to show all
            input figures, depending on the number of rows. If rows and
            columns are 0, the axes layout will be square.
    :Ref. nodes: :ref:`Figure from Table with Table`
    """
    author = 'Benedikt Ziegler <benedikt.ziegler@combine.se>'
    copyright = '(c) 2016 Combine AB'
    version = '0.1'
    icon = 'figuresubplots.svg'
    name = 'Layout Figures in Subplots'
    description = 'Layout a list of Figures in a Subplot'
    nodeid = 'org.sysess.sympathy.visualize.figuresubplot'
    tags = Tags(Tag.Visual.Figure)

    inputs = Ports([Port.Figures('Input data', name='input')])
    outputs = Ports([Port.Figure('Output figure', name='figure')])

    parameters = synode.parameters()
    parameters.set_integer(
        'rows', value=0, label='Number of rows (0 = best):',
        description='Specify the number of rows. 0 optimizes to fit all '
                    'figures. If rows and columns are 0, the axes layout '
                    'will be square.',
        editor=synode.Util.bounded_spinbox_editor(0, 100, 1).value())
    parameters.set_integer(
        'columns', value=0, label='Number of columns (0 = best):',
        description='Specify the number of columns. 0 optimizes to fit all '
                    'figures. If rows and columns are 0, the axes layout '
                    'will be square.',
        editor=synode.Util.bounded_spinbox_editor(0, 100, 1).value())
    parameters.set_boolean(
        'recolor', value=True, label='Recolor lines automatically',
        description='Specify if lines should be assigned new colors '
                    'automatically to prevent double colors')

    def execute(self, node_context):
        input_figures = node_context.input['input']
        output_figure = node_context.output['figure']
        parameters = node_context.parameters
        rows = parameters['rows'].value
        cols = parameters['columns'].value
        auto_recolor = parameters['recolor'].value

        # calculate the number of rows and columns if any is =0
        nb_input_figures = len(input_figures)
        if rows == 0 and cols == 0:
            rows = int(np.ceil(np.sqrt(nb_input_figures)))
            cols = int(np.ceil(np.sqrt(nb_input_figures)))
            if rows * cols - cols >= nb_input_figures > 0:
                rows -= 1
        elif rows == 0 and cols > 0:
            rows = int(np.ceil(nb_input_figures / float(cols)))
        elif rows > 0 and cols == 0:
            cols = int(np.ceil(nb_input_figures / float(rows)))

        subplots = np.array(output_figure.subplots(rows, cols)).ravel()

        for subplot, input_figure in itertools.izip(subplots, input_figures):
            default_axes = subplot.get_mpl_axes()
            input_axes = [axes.get_mpl_axes() for axes in input_figure.axes]

            util.compress_axes([input_axes], default_axes,
                               legends_join=True,
                               legend_location='best',
                               copy_properties_from=0,
                               auto_recolor=auto_recolor)

        # don't show empty axes
        if len(subplots) > len(input_figures):
            for ax_to_blank in subplots[len(input_figures):]:
                ax_to_blank.set_axis(False)


UserType = QtGui.QStandardItem.UserType

PARAMETER_TYPES = {
    'AXES': UserType,
    'GRID': UserType + 1,
    'LEGEND': UserType + 2,
    'LINE': UserType + 10,
    'SCATTER': UserType + 11,
}

# Define for every parameter a type_id. The inverse lookup needs to be
# implemented in ``get_type_parameters()`` below.

# add AXES parameters
PARAMETER_TYPES.update({key: UserType + 100 + i
                        for i, key in enumerate(util.AXES.keys())})
# add LINE parameters
PARAMETER_TYPES.update({key: UserType + 200 + i
                        for i, key in enumerate(util.LINE.keys())})

# add other plot types here

# add GRID parameters
PARAMETER_TYPES.update({key: UserType + 1000 + i
                        for i, key in enumerate(util.GRID.keys())})

# add LEGEND parameters
PARAMETER_TYPES.update({key: UserType + 1100 + i
                        for i, key in enumerate(util.LEGEND.keys())})

# inverted lookup dict
PARAMETER_TYPES_INV = {v: k for k, v in six.iteritems(PARAMETER_TYPES)}


def get_type_parameters(index):
    item = index.model().itemFromIndex(index)
    type_id = item.type()

    type_name = PARAMETER_TYPES_INV.get(type_id)
    if UserType + 100 <= type_id < UserType + 200:
        type_param = util.AXES[type_name]
    elif UserType + 200 <= type_id < UserType + 300:
        type_param = util.LINE[type_name]
    # ADD OTHER PLOT TYPES HERE
    elif UserType + 1000 <= type_id < UserType + 1100:
        type_param = util.GRID[type_name]
    elif UserType + 1100 <= type_id < UserType + 1200:
        type_param = util.LEGEND[type_name]
    else:
        type_name, type_param = None, None

    return type_name, type_param


def create_widget_for(parent, index):
    """
    Create an editor widget for the given type.
    """
    type_name, type_param = get_type_parameters(index)
    if type_param is None:
        return None
    type_, default, options, required, widget = type_param
    if widget is not None:
        return widget(parent)
    return None


def add_default_parameter(parent, type_name, prop=None):
    if prop is None:
        prop = {}
    model = parent.model()
    params = util.PARAMETER_OPTIONS.get(type_name, {}).get('parameter', None)
    type_params = util.PARAMETER_OPTIONS.get(type_name, {})
    default_params = type_params.get('default_parameter', None)
    if params is not None:
        for name, param in six.iteritems(params):
            if isinstance(param, tuple) and param[3] or name in default_params:
                value = prop.get(name, param[1])
                model.add_parameter_to_item(parent, name, value)


class SyTableTreeModel(QtGui.QStandardItemModel):
    def __init__(self, table, parent=None):
        super(SyTableTreeModel, self).__init__(parent)
        self.root_item = self.invisibleRootItem()

        self._table = table
        self.create_tree()

    def create_tree(self):
        # TODO: (Bene) add [Table] support with the following syntax
        # "table[1].name"
        # only in cases where input "table" is of type [Table] ?!
        parent = self.add_child(self.root_item, 'table')
        self.add_child(parent, 'name')
        for attr in self._table.get_table_attributes().keys() + ['']:
            self.add_child(parent, "attr('{}')".format(attr))

        column_names = self._table.column_names()
        for name in column_names + ['']:
            child = self.add_child(parent, "col('{}')".format(name))

            for prop in ['name', 'data', 'attr']:
                if prop == 'attr':
                    try:
                        col_attr = self._table.get_column_attributes(
                            name).keys() + ['']
                    except KeyError:
                        col_attr = ['']
                    for attr in col_attr:
                        self.add_child(child, "attr('{}')".format(attr))
                else:
                    self.add_child(child, prop)

    @staticmethod
    def add_child(parent, child_name):
        child_item = QtGui.QStandardItem(six.text_type(child_name))
        parent.appendRow(child_item)
        return child_item


class TreeModelCompleter(QtGui.QCompleter):
    insert_text = QtCore.Signal(unicode)

    def __init__(self, *args, **kwargs):
        super(TreeModelCompleter, self).__init__(*args, **kwargs)
        self._separator = None
        self.activated[unicode].connect(self.change_completion)

    def change_completion(self, completion):
        self.insert_text.emit(completion)

    @property
    def separator(self):
        return self._separator

    @separator.setter
    def separator(self, s):
        self._separator = s

    def splitPath(self, path):
        if self.separator is None:
            return super(TreeModelCompleter, self).splitPath(path)

        splitted_path = path.split(self.separator)
        return splitted_path

    def pathFromIndex(self, index):
        def get_tree_data(idx, data_list):
            if idx.isValid():
                data = self.model().data(idx, self.completionRole())
                data_list.append(data)
                get_tree_data(idx.parent(), data_list)

        if self.separator is None:
            return super(TreeModelCompleter, self).pathFromIndex(index)

        # navigate up and accumulate data
        data_list = []
        get_tree_data(index, data_list)
        return '{}'.format(self.separator).join(reversed(data_list))


class FigureConfigItem(QtGui.QStandardItem):
    def __init__(self, icon=None, text=None, other=None,
                 rows=None, columns=1, type_=None):
        if other is not None:
            super(FigureConfigItem, self).__init__(other)
        elif text is not None and icon is not None:
            super(FigureConfigItem, self).__init__(icon, text)
        elif text is not None and icon is None:
            super(FigureConfigItem, self).__init__(text)
        elif rows is not None:
            super(FigureConfigItem, self).__init__(rows, columns)
        else:
            super(FigureConfigItem, self).__init__()

        if type_ is None:
            type_ = 0
        self._type = type_

    def type(self):
        return self._type


class ParameterTreeDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, completer_model, parent=None):
        super(ParameterTreeDelegate, self).__init__(parent)

        self.completer_model = completer_model

    def createEditor(self, parent, option, index):
        if index.isValid():
            widget = create_widget_for(parent, index)
            if widget is None:
                return super(ParameterTreeDelegate, self).createEditor(parent,
                                                                       option,
                                                                       index)
            else:
                return widget

    def setEditorData(self, editor, index):
        type_name, type_param = get_type_parameters(index)
        if type_param is not None:
            type_, default, options, required, widget = type_param
            if options is not None and hasattr(editor, 'set_options'):
                editor.set_options(options)
            if hasattr(editor, 'set_completer'):
                completer = TreeModelCompleter(self)
                completer.separator = '.'
                completer.setModel(self.completer_model)
                completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
                completer.setWrapAround(False)
                editor.set_completer(completer)

        value = index.model().data(index)
        if hasattr(editor, 'set_value'):
            editor.set_value(value)
        else:
            super(ParameterTreeDelegate, self).setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if hasattr(editor, 'get_value'):
            value = editor.get_value()
            model.setData(index, value)
        else:
            super(ParameterTreeDelegate, self).setModelData(editor, model,
                                                            index)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class FigureConfigModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        super(FigureConfigModel, self).__init__(parent)
        self.root_item = self.invisibleRootItem()

    def add_item(self, name, type_, parent=None, add_default=True, prop=None):
        """Add an item ot a parent."""
        type_id = PARAMETER_TYPES.get(type_, None)
        if type_id is None:
            raise ValueError('The given type "{}" is not '
                             'supported.'.format(type_))

        args = {'text': name,
                'type_': type_id}

        icon_name = util.PARAMETER_OPTIONS.get(type_, {}).get('icon', None)
        if icon_name is not None:
            icon_name = util.get_full_icon_name(icon_name)
            icon = QtGui.QIcon(icon_name)
            args['icon'] = icon

        item = FigureConfigItem(**args)
        if parent is None:
            parent = self.root_item
        # add a disabled item to block entering garbage into the value column
        disabled_value_item = QtGui.QStandardItem()
        disabled_value_item.setEnabled(False)
        disabled_value_item.setEditable(False)
        parent.appendRow([item, disabled_value_item])

        # add default parameter
        if add_default:
            add_default_parameter(item, type_, prop)
        return item

    @staticmethod
    def add_parameter_to_item(parent, name, value=None):
        """Add a parameter to parent."""
        # TODO: add attribute icon
        name_item = FigureConfigItem(text=name)
        name_item.setEditable(False)

        parent_type = PARAMETER_TYPES_INV.get(parent.type())

        type_id = PARAMETER_TYPES.get(name)
        # get default value
        type_dict = util.PARAMETER_OPTIONS.get(parent_type, {})
        parent_dict = type_dict.get('parameter', {})
        type_param = parent_dict.get(name)

        if isinstance(type_param, tuple):
            if value is None:
                value = type_param[1]
            value_item = FigureConfigItem(text=six.text_type(value),
                                          type_=type_id)
            parent.appendRow([name_item, value_item])
            return name_item, value_item

    def get_items(self, type_=None):
        rows = self.rowCount()

        items = []
        type_id = PARAMETER_TYPES.get(type_, None)
        for row in range(rows):
            item = self.item(row)
            if (type_ is not None and item is not None and
                        item.type() == type_id):
                items.append(item)
            elif type_ is None:
                items.append(item)
        return items

    def remove_item(self, index):
        if index.parent() == QtCore.QModelIndex():
            # workaround to delete first generation items
            item = self.takeItem(index.row())
            self.beginRemoveRows(self.root_item.index(),
                                 item.row(),
                                 item.row() + 1)
            self.removeRow(index.row())
            del index
            del item
            self.endRemoveRows()
            return
        self.removeRows(index.row(), 1, index.parent())

    def init_config(self, parameters):
        def populate_children(value_dict, parent):
            for param, value in six.iteritems(value_dict):
                if isinstance(value, dict):
                    child = self.add_item(param, param.upper(), parent,
                                          add_default=False)
                    populate_children(value, child)
                else:
                    self.add_parameter_to_item(parent, param, value)

        parsed_params = util.parse_configuration(parameters)
        for key, value in six.iteritems(parsed_params):
            for id_, id_value in six.iteritems(value):
                child = self.add_item(id_, key.upper(), add_default=False)
                populate_children(id_value, child)

    def export_config(self):
        def populate_config(parent, path, output):
            if parent:
                rows = parent.rowCount()
                for row in range(rows):
                    cols = parent.columnCount()
                    name_item = parent.child(row, 0)
                    name = six.text_type(name_item.text())
                    full_name = '.'.join((path, name))
                    value = 'True'
                    value_item = parent.child(row, 1)
                    if cols > 1 and value_item.isEnabled():
                        value = six.text_type(value_item.text())
                    output.append((full_name, value))
                    if name_item.hasChildren():
                        populate_config(name_item, full_name, output)

        config = []
        for row in range(self.root_item.rowCount()):
            child = self.root_item.child(row)
            type = PARAMETER_TYPES_INV.get(child.type())
            path = '.'.join((type.lower(), child.text()))
            populate_config(child, path, config)
        return config


class ParameterTreeView(QtGui.QTreeView):
    def __init__(self, input_table, parent=None):
        super(ParameterTreeView, self).__init__(parent)

        self._input_table = input_table
        self.completer_model = SyTableTreeModel(self._input_table, self)

        delegate = ParameterTreeDelegate(self.completer_model, self)
        self.setItemDelegate(delegate)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_custom_context_menu)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.remove_current_selection()
            event.ignore()

    def on_custom_context_menu(self, pos):
        index = self.indexAt(pos)
        if index.isValid():
            # add general context menu items
            menu = self.create_item_type_menu(index)

            menu.addSeparator()
            icon_name = util.get_full_icon_name('edit-trash-symbolic.svg')
            icon = QtGui.QIcon(icon_name)
            action_delete = menu.addAction(icon, 'Delete')
            icon_name = util.get_full_icon_name('increase-size-option.svg')
            icon = QtGui.QIcon(icon_name)
            # action_expand = menu.addAction(icon, 'Expand')
            # if self.isExpanded(index):
            #     action_expand.setVisible(False)
            action_expand_all = menu.addAction(icon, 'Expand All')
            icon_name = util.get_full_icon_name('decrease-size-option.svg')
            icon = QtGui.QIcon(icon_name)
            # action_collapse = menu.addAction(icon, 'Collapse')
            # if not self.isExpanded(index):
            #     action_collapse.setVisible(False)
            action_collapse_all = menu.addAction(icon, 'Collapse All')
            action = menu.exec_(self.viewport().mapToGlobal(pos))

            if action == action_delete:
                self.remove_current_selection()
            # elif action == action_expand:
            #     self.expand(index)
            elif action == action_expand_all:
                self.expandAll()
            # elif action == action_collapse:
            #     self.collapse(index)
            elif action == action_collapse_all:
                self.collapseAll()

    def create_item_type_menu(self, index):
        menu = QtGui.QMenu(self)
        if index.isValid():
            model = index.model()
            item = model.itemFromIndex(index)
            # add type specific context menu items
            item_type = PARAMETER_TYPES_INV.get(item.type(), None)
            if item_type in util.PARAMETER_OPTIONS.keys():
                parent_params = util.PARAMETER_OPTIONS.get(item_type, {})
                available_params = parent_params.get('parameter', {})

                current_children = [item.child(row)
                                    for row in range(item.rowCount())]
                current_params = [child.text() for child in current_children]

                for key, param in six.iteritems(available_params):
                    if key not in current_params and isinstance(param, tuple):
                        # lambda does not work, since it would take the
                        # last 'key' value
                        func = functools.partial(model.add_parameter_to_item,
                                                 item, key)
                        menu.addAction('Add {}'.format(key), func)
                    elif key not in current_params and isinstance(param, dict):
                        func = functools.partial(model.add_item, key,
                                                 key.upper(), item)
                        menu.addAction('Add {}'.format(key.upper()), func)
        return menu

    def remove_current_selection(self):
        index = self.currentIndex()
        if index.isValid():
            self.model().remove_item(index)


class FigureFromTableWidget(ParameterView):
    def __init__(self, input_table, parameters, parent=None):
        super(FigureFromTableWidget, self).__init__(parent=parent)

        self.input_table = input_table
        self.parameters = parameters

        self._model = FigureConfigModel(self)
        self._model.setHorizontalHeaderLabels(['Item', 'Value'])
        self._init_gui()
        self._init_from_parameters()

    def _init_gui(self):
        self.toolbar = sywidgets.SyToolBar(self)

        self.param_tree = ParameterTreeView(self.input_table, self)
        self.param_tree.setMinimumWidth(200)
        self.param_tree.setMinimumHeight(200)
        self.param_tree.setSelectionBehavior(
            QtGui.QAbstractItemView.SelectRows)
        self.param_tree.setUniformRowHeights(True)
        self.param_tree.header().stretchLastSection()
        self.param_tree.setModel(self._model)

        main_layout = QtGui.QHBoxLayout()
        settings_layout = QtGui.QVBoxLayout()
        settings_layout.addWidget(self.toolbar)
        settings_layout.addWidget(self.param_tree)
        main_layout.addLayout(settings_layout)

        self.setLayout(main_layout)
        self._init_toolbar()

        selection_model = self.param_tree.selectionModel()
        selection_model.selectionChanged.connect(
            self.update_selected_item_menu)

    def _init_toolbar(self):
        # add data menu
        data_menu_items = ['AXES', 'LINE']
        self.create_menu_in_toolbar(data_menu_items,
            menu_icon_name='plus-sign-in-a-black-circle.svg')
        # context menu item (depends on currently selected item)
        self.selected_item_toolbutton = self.create_menu_in_toolbar([],
            menu_icon_name='cross-mark-on-a-black-circle-background.svg')
        self.selected_item_toolbutton.setEnabled(False)
        icon_name = util.get_full_icon_name('edit-trash-symbolic.svg')
        icon = QtGui.QIcon(icon_name)
        self.delete_action = self.toolbar.addAction(icon, 'Delete')
        self.toolbar.addStretch()

        self.delete_action.triggered.connect(self._delete_selected_item)

        # timer is needed to delay the menu updated call
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(5)
        self._timer.setSingleShot(True)
        self.selected_item_toolbutton.triggered.connect(self._timer.start)
        self._timer.timeout.connect(self._reinit_selected_item_menu)

    def create_menu_in_toolbar(self, items, menu_icon_name=None):
        menu = QtGui.QMenu()
        actions = []
        for item in items:
            # get icon
            icon_name = util.PARAMETER_OPTIONS.get(
                            item, {}).get('icon', None)
            if icon_name is None:
                action = menu.addAction(
                    'Add {}'.format(item.lower().title()),
                    functools.partial(self.add_item, item))
            else:
                icon_name = util.get_full_icon_name(icon_name)
                icon = QtGui.QIcon(icon_name)
                action = menu.addAction(
                    icon,
                    'Add {}'.format(item.lower().title()),
                    functools.partial(self.add_item, item))
            actions.append(action)

        tool_button = QtGui.QToolButton()
        if len(actions) and menu_icon_name is None:
            menu.setDefaultAction(actions[0])
            menu_icon = actions[0].icon()
            tool_button.setIcon(menu_icon)
        elif menu_icon_name is not None:
            full_icon_name = util.get_full_icon_name(menu_icon_name)
            menu_icon = QtGui.QIcon(full_icon_name)
            tool_button.setIcon(menu_icon)
        tool_button.setMenu(menu)
        tool_button.setPopupMode(QtGui.QToolButton.InstantPopup)

        toolbuttonaction = QtGui.QWidgetAction(self)
        toolbuttonaction.setDefaultWidget(tool_button)
        self.toolbar.addAction(toolbuttonaction)
        return tool_button

    def update_selected_item_menu(self):
        current_index = self.param_tree.selectionModel().currentIndex()
        self.selected_item_toolbutton.setEnabled(False)
        if current_index != QtCore.QModelIndex():
            menu = self.param_tree.create_item_type_menu(current_index)

            # update icon
            item = current_index.model().itemFromIndex(current_index)
            # add type specific context menu items
            item_type = PARAMETER_TYPES_INV.get(item.type(), None)
            if item_type is not None:
                parent_params = util.PARAMETER_OPTIONS.get(item_type, {})
                icon_name = parent_params.get('icon', None)
                if icon_name is not None:
                    icon_name = util.get_full_icon_name(icon_name)
                    icon = QtGui.QIcon(icon_name)
                    self.selected_item_toolbutton.setIcon(icon)

            self.selected_item_toolbutton.setMenu(menu)
            if not menu.isEmpty():
                self.selected_item_toolbutton.setEnabled(True)

    def _reinit_selected_item_menu(self):
        self.update_selected_item_menu()

    def add_item(self, type_):
        model = self._model
        existing_items = model.get_items(type_=type_)
        existing_names = [item.text() for item in existing_items]

        all_items = [model.item(r) for r in range(model.rowCount())]
        all_existing_types = [item.type() for item in all_items]

        prop = {}

        if type_ != 'AXES':
            # auto create an axes if non exists
            axes_id = PARAMETER_TYPES.get('AXES', None)
            if axes_id not in set(all_existing_types):
                self.add_item('AXES')

            # auto set color
            # color = len(all_existing_types) - all_existing_types.count(axes_id)
            prop['color'] = ''

        valid_name = False
        i = 0
        while not valid_name:
            name_for_new_item = '{:s}_{:d}'.format(type_.lower(),
                                                   len(existing_items) + i)
            if name_for_new_item not in existing_names:
                valid_name = True
            else:
                i += 1

        new_item = model.add_item(name_for_new_item, type_=type_, prop=prop)
        return new_item

    def _delete_selected_item(self):
        selected_indices = self.param_tree.selectedIndexes()
        if len(selected_indices):
            selected_index = selected_indices[0]
            self.param_tree.model().remove_item(selected_index)

    def _init_from_parameters(self):
        model = self.param_tree.model()
        model.init_config(self.parameters['parameters'].list)

    def save_parameters(self):
        model = self.param_tree.model()
        self.parameters['parameters'].list = model.export_config()


class FigureFromTableWithTreeView(synode.Node):
    """
    Create a Figure from a Table.

    :Inputs:
        **input** : Table
            Table containing the data to be plotted.
    :Outputs:
        **plot** : Figure
            A Figure.
        **config** : Table
            A table containing the figure configuration as
            parameter and value pairs.
    """

    author = 'Benedikt Ziegler <benedikt.ziegler@combine.se'
    copyright = '(c) 2016 Combine AB'
    version = '0.1'
    icon = 'figure.svg'
    name = 'Figure from Table'
    description = 'Create a Figure from a Table using a GUI.'
    nodeid = 'org.sysess.sympathy.visualize.figuretabletreegui'
    tags = Tags(Tag.Visual.Figure)

    parameters = synode.parameters()
    parameters.set_list('parameters')

    inputs = Ports([Port.Table('Input data', name='input')])
    outputs = Ports([Port.Figure('Output figure', name='figure'),
                     Port.Table('Configuration', name='config')])

    def exec_parameter_view(self, node_context):
        input_data = node_context.input['input']
        if not input_data.is_valid():
            input_data = api.table.File()
        return FigureFromTableWidget(input_data, node_context.parameters)

    def execute(self, node_context):
        data_table = node_context.input['input']
        figure = node_context.output['figure']

        config_table = node_context.output['config']
        fig_parameters = node_context.parameters['parameters'].list
        parsed_param = util.parse_configuration(fig_parameters)

        figure_creator = util.CreateFigure(data_table, figure, parsed_param)
        figure_creator.create_figure()

        fig_parameters = np.atleast_2d(np.array(fig_parameters))
        if len(fig_parameters) and fig_parameters.shape >= (1, 2):
            parameters = fig_parameters[:, 0]
            values = fig_parameters[:, 1]
        else:
            parameters = np.array([])
            values = np.array([])
        config_table.set_column_from_array('Parameters', parameters)
        config_table.set_column_from_array('Values', values)


class FiguresFromTablesWithTreeView(FigureFromTableWithTreeView):
    """
    Create a List of Figures from a List of Tables.

    :Inputs:
        **input** : [Table]
            Tables containing the data to be plotted.
    :Outputs:
        **plot** : [Figure]
            A List of Figures.
        **config** : Table
            A table containing the figure configuration as
            parameter and value pairs.
    """

    version = '0.1'
    name = 'Figures from Tables'
    description = 'Create a Figures from a Tables using a GUI.'
    nodeid = 'org.sysess.sympathy.visualize.figurestablestreegui'
    tags = Tags(Tag.Visual.Figure)

    inputs = Ports([Port.Tables('Input data', name='inputs')])
    outputs = Ports([Port.Figures('Output figure', name='figures'),
                     Port.Table('Configuration', name='config')])

    def exec_parameter_view(self, node_context):
        input_data = node_context.input['inputs']
        if not input_data.is_valid() or not len(input_data):
            first_input = api.table.File()
        else:
            first_input = input_data[0]
        return FigureFromTableWidget(first_input, node_context.parameters)

    def execute(self, node_context):
        data_tables = node_context.input['inputs']
        figures = node_context.output['figures']

        config_table = node_context.output['config']
        fig_parameters = node_context.parameters['parameters'].list
        parsed_param = util.parse_configuration(fig_parameters)

        number_of_tables = len(data_tables) + 1  # +1 for writing config table

        i = 0
        for i, data_table in enumerate(data_tables):
            figure = api.figure.File()
            figure_creator = util.CreateFigure(data_table, figure,
                                               parsed_param.copy())
            figure_creator.create_figure()
            figures.append(figure)
            self.set_progress(100 * (i + 1) / number_of_tables)

        fig_parameters = np.atleast_2d(np.array(fig_parameters))
        if len(fig_parameters) and fig_parameters.shape >= (1, 2):
            parameters = fig_parameters[:, 0]
            values = fig_parameters[:, 1]
        else:
            parameters = np.array([])
            values = np.array([])
        config_table.set_column_from_array('Parameters', parameters)
        config_table.set_column_from_array('Values', values)
        self.set_progress(100 * (i + 1) / number_of_tables)


if __name__ == '__main__':
    import sys
    from sympathy.api import table

    test_table = table.File()
    test_table.set_column_from_array('test',
                                     np.arange(100),
                                     {'unit': 'm',
                                      'description': 'My description',
                                      'other attr': 'The other attribute'})

    treemodel = SyTableTreeModel(test_table)

    completer = TreeModelCompleter()
    completer.setModel(treemodel)
    completer.separator = '.'
    completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
    completer.setWrapAround(False)

    application = QtGui.QApplication(sys.argv)

    window = util.widgets.SyMPLTextEdit()

    window.set_completer(completer)

    window.show()
    window.activateWindow()
    window.raise_()

    sys.exit(application.exec_())
