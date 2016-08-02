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
import ast
import re
from collections import defaultdict

import numpy as np

from matplotlib import lines as mpl_lines
from matplotlib import markers as mpl_markers
from matplotlib import colors as mpl_colors
from matplotlib.transforms import IdentityTransform

from sympathy.platform.exceptions import sywarn
from sympathy.api import figure

MARKERS = mpl_markers.MarkerStyle.markers
LINESTYLES = mpl_lines.lineStyles

LEGEND_LOC = {
    'best': 0,  # (only implemented for axes legends)
    'upper right': 1,
    'upper left': 2,
    'lower left': 3,
    'lower right': 4,
    'right': 5,
    'center left': 6,
    'center right': 7,
    'lower center': 8,
    'upper center': 9,
    'center': 10
}

FONTSIZE = ['xx-small', 'x-small', 'small', 'medium',
            'large', 'x-large', 'xx-large']


def get_known_mpl_colors():
    colors = list(mpl_colors.cnames.iteritems())
    # Add the single letter colors.
    for name, rgb in mpl_colors.ColorConverter.colors.iteritems():
        hex_ = mpl_colors.rgb2hex(rgb)
        colors.append((name, hex_))
    # sort by name
    colors.sort()
    return dict(colors)


COLORS = get_known_mpl_colors()


def parse_color_to_mpl_color(text):
    """
    Parse a color string to a valid matplotlib color tuple.

    `text` can be any valid mpl color string can be used
    (e.g. 'r', 'red', 'b', 'blue', etc.), a valid hex color,
     hex color with additional alpha channel or a string
     of 3-4 integers/floats which can be parsed by
     ast.literal_eval to a tuple of numbers.

    Parameters
    ----------
    text : str
        A string for the color.
        Examples:
            (0, 0, 0)
            (255, 255, 255, 255)
            (0.5, 0.5, 0.5)
            (1., 1., 1., 1.)
            #ffffff
            #fefefefe
            'r'
            'red'

    Returns
    -------
    color : list
        A list of four floats in the interval [0., 1.].
    """
    # named color
    if text in COLORS.keys():
        return text
    # hex color
    hex_match = re.search(r'#[0-9a-fA-F]{6,8}', text)
    if hex_match:
        hex = hex_match.group()
        rgba = list(mpl_colors.hex2color(hex[:7]))
        if len(hex) == 9:
            rgba.append(int(hex[-2:], 16) / 255.)
        return rgba
    # rgb colors
    try:
        rgba = ast.literal_eval(text)
    except SyntaxError:
        return None
    if len(rgba) in [3, 4]:
        rgba = np.array(rgba, dtype=float)
        if np.any(rgba > 1.) and not any(rgba > 255):
            color = [item / 255. for item in rgba]
        elif np.any(rgba > 255):
            return None
        else:
            color = rgba
        return list(color)
    return None


# the allowed parameters are listed in dictionaries where the value
# contains: (type, default_value, choices or None, required)

LINE = {
    'xdata': (unicode, '', None, True),
    'ydata': (unicode, '', None, True),
    'axes': ('axestype', '_default_', None, False),
    'label': (unicode, '', None, False),
    'marker': (str, 'o', MARKERS, False),
    'markersize': (float, 5, None, False),
    # 'ms': (float, 5, None, False),
    'markeredgecolor': ('colortype', 'gray', COLORS, False),
    # 'mec': ('colortype', 'gray', COLORS, False),
    'markeredgewidth': (float, 0.1, None, False),
    # 'mew': (float, 0.1, None, False),
    'markerfacecolor': ('colortype', 'b', COLORS, False),
    # 'mfc': ('colortype', 'b', COLORS, False),
    'linestyle': ('linestyletype', '-', LINESTYLES, False),
    # 'ls': ('linestyletype', '-', LINESTYLES, False),
    'linewidth': (float, 1., None, False),
    # 'lw': (float, 1., None, False),
    'color': ('colortype', 'g', COLORS, False),
    # 'c': ('colortype', 'g', COLORS, False),
    'alpha': (float, 1., [0., 1.], False),
    'zorder': (float, 1, None, False),
    'drawstyle': ('drawstyletype', 'default', ['default', 'steps',
                                               'steps-pre', 'steps-mid',
                                               'steps-post'], False),
    # 'xdate': (bool, False, None, False),
    # 'ydate': (bool, False, None, False),
}

GRID = {
    'color': ('colortype', 'g', COLORS, False),
    # 'c': ('colortype', 'g', COLORS, False),
    'linestyle': ('linestyletype', '-', LINESTYLES, False),
    # 'ls': ('linestyletype', '-', LINESTYLES, False),
    'linewidth': (float, 1., None, False),
    # 'lw': (float, 1., None, False),
    'which': (str, 'major', ['major', 'minor', 'both'], False),
    'axis': (str, 'both', ['x', 'y', 'both'], False)
}

LEGEND = {
    'loc': ('locationtype', 'upper right', LEGEND_LOC, False),
    'ncol': (int, 1, None, False),
    'fontsize': ('fontsizetype', None, FONTSIZE, False),
    'frameon': (bool, True, None, False),
    'title': (unicode, '', None, False),
    # 'markerfirst': (bool, True, None, False),
    # 'numpoints': (int, None, None, False),
    # 'scatterpoints': (int, None, None, False),
    # 'fancybox': (bool, False, None, False),
    # 'shadow': (bool, False, None, False),
    # 'framealpha': (float, 1., None, False),
    # 'borderpad': (float, None, None, False),
    # 'labelspacing': (float, None, None, False),
    # 'handlelength': (float, None, None, False),
    # 'handletextpad': (float, None, None, False),
    # 'borderaxespad': (float, None, None, False),
    # 'columnspacing': (float, None, None, False),
}

AXES = {
    'xaxis': ('axestype', 'x1', ['x', 'x1', 'x2'], True),  # possibly add multi x-axis support later
    'yaxis': ('axestype', 'y1', ['y', 'y1', 'y2'], True),
    'title': (unicode, '', None, False),
    'xlabel': (unicode, '', None, False),
    'ylabel': (unicode, '', None, False),
    'xlim': (ast.literal_eval, (None, None), None, False),
    'ylim': (ast.literal_eval, (None, None), None, False),
    'xscale': (str, 'linear', ['linear', 'log'], False),
    'yscale': (str, 'linear', ['linear', 'log'], False),
    'aspect': (str, 'auto', ['auto', 'equal', '1.'], False),
    'legend': LEGEND,
    'grid': GRID,
}

FIGURE = {
    'title': (unicode, '', None, False),  # seems not to be supported by mpl
}


def verify_options(value, options):
    """Check if value is within the options."""
    if value in options:
        return value
    return None


def gen_config_by_prefix(config, prefix):
    """
    Return a generator returning (key, value) where the key
    start with the given prefix.
    """
    return ((k.lower(), v) for k, v in config
            if k.lower().startswith(prefix.lower()))


def parse_type(value, type_):
    t, default, options, required = type_
    if t == 'colortype':
        return parse_color_to_mpl_color(str(value))
    elif t in ['linestyletype', 'locationtype',
               'drawstyletype', 'fontsizetype']:
        return verify_options(str(value), options)
    elif t == 'axestype':
        if value in ['x', 'y']:
            return '{}1'.format(value)
        elif value in ['x1', 'x2', 'y1', 'y2']:
            return value
        return None
    else:
        return t(value)


def fill_in_global_parameters(global_params, local_params):
    """
    Update the local parameters with existing global parameters
    without overriding existing ones.
    """
    for key, value in global_params.iteritems():
        for local in local_params.itervalues():
            if key not in local:
                local[key] = value


def parse_config_lines(config, axes=None):
    """Parse the line parameters."""
    if axes is None:
        axes = {}
    global_line_params = {}
    lines = defaultdict(dict)
    for key, value in config:
        key_splitted = key.lower().split('.')
        if len(key_splitted) == 3:
            identifier, param = key_splitted[1:]
        elif len(key_splitted) == 2:
            identifier, param = None, key_splitted[1]
        type_ = LINE.get(param, None)
        # continue if type is unknown
        if type_ is None:
            continue
        if param == 'axes':
            if value in axes.keys():
                parsed_value = value
            else:
                # default case
                continue
        else:
            parsed_value = parse_type(value, type_)
        # jump parameter if it's value is unknown
        if parsed_value is None:
            continue
        if identifier is None:
            global_line_params[param] = parsed_value
        else:
            lines[identifier][param] = parsed_value

    # get required parameters
    required_parameters = [k for k, v in LINE.iteritems() if v[3]]
    # update line parameters from global parameters if missing and
    # defined in global line parameter
    for line_id, params in lines.iteritems():
        is_valid = True
        for required_param in required_parameters:
            if required_param in params.keys():
                continue
            if (required_param not in params.keys() and
                    required_param in global_line_params.keys()):
                value = global_line_params[required_param]
            else:
                value = LINE[required_param][1]
                if required_param in ['xdata', 'ydata']:
                    is_valid = False
            lines[line_id][required_param] = value
        lines[line_id]['valid'] = is_valid

    fill_in_global_parameters(global_line_params, lines)
    return lines, global_line_params


def parse_sub_config(param, value, config_dict):
    type_ = config_dict.get(param, None)
    if type_ is None:
        return None, None
    parsed_value = parse_type(value, type_)
    return param, parsed_value


def parse_config_axes(config):
    """Parse the axes parameters."""
    global_axes = {}
    axes = defaultdict(dict)
    for key, value in config:
        key_splitted = key.lower().split('.')
        sub_param = []
        if len(key_splitted) == 3 and key_splitted[1] not in AXES.keys():
            identifier, param = key_splitted[1:]
        elif len(key_splitted) == 3 and key_splitted[1] in AXES.keys():
            identifier = None
            param = key_splitted[1]
            sub_param = key_splitted[2:]
        elif len(key_splitted) == 2:
            identifier, param = None, key_splitted[1]
        else:
            identifier = key_splitted[1]
            param = key_splitted[2]
            sub_param = key_splitted[3:]
        type_ = AXES.get(param, None)
        if type_ is None:
            continue
        if param in ['grid', 'legend']:
            if (identifier is None and
                    param not in global_axes.keys()):
                    global_axes[param] = {'show': True}
            elif (identifier is not None and
                    param not in axes[identifier].keys()):
                    axes[identifier][param] = {'show': True}
            if len(sub_param):
                sconfig = GRID if param == 'grid' else LEGEND
                p, v = parse_sub_config(sub_param[0], value, sconfig)
                if p is not None and v is not None:
                    if identifier is None:
                        global_axes[param][p] = v
                    else:
                        axes[identifier][param][p] = v
        else:
            parsed_value = parse_type(value, type_)
            if identifier is None:
                global_axes[param] = parsed_value
            else:
                axes[identifier][param] = parsed_value

    # get all defined x and y axes
    defined_yaxis = set(
        [a['yaxis'] for a in axes.itervalues() if 'yaxis' in a])

    # get required parameters
    required_parameters = [k for k, v in AXES.iteritems() if
                           not isinstance(v, dict) and v[3]]
    # update line parameters from global parameters if missing and
    # defined in global line parameter
    for axis_id, params in axes.iteritems():
        for required_param in required_parameters:
            if required_param in params.keys():
                continue
            if required_param in global_axes.keys():
                value = global_axes[required_param]
            else:
                value = AXES[required_param][1]
                if required_param == 'yaxis':
                    if value in defined_yaxis:
                        value = 'y2'
            axes[axis_id][required_param] = value
    fill_in_global_parameters(global_axes, axes)
    return axes


def parse_config_figure(config):
    """Parse the figure parameters."""
    figure = {}
    for key, value in config:
        try:
            param = key.lower().lstrip('figure.')
            type_ = FIGURE.get(param, None)
            if type_ is None:
                continue
            parsed_value = parse_type(value, type_)
            figure[param] = parsed_value
        except:
            pass
    return figure


def parse_configuration(config):
    """
    Parse a configuration table containing with
    a parameter and value column.
    """
    axes = parse_config_axes(
        gen_config_by_prefix(config, 'axes.'))
    lines, global_line_params = parse_config_lines(
        gen_config_by_prefix(config, 'line.'), axes)
    figure = parse_config_figure(
        gen_config_by_prefix(config, 'figure.'))

    return {'figure': figure,
            'axes': axes,
            'lines': lines}


def reconstruct_twin_axes(start_axes, axes):
    """Reconstruct the relationship between overlaying twin axes."""
    sibling_axes = {start_axes: (1, 1)}
    shared_ax = {ax: (ax._sharex, ax._sharey) for ax in axes}

    for ax in axes:
        if ax in sibling_axes.keys():
            continue
        has_shared = shared_ax.get(ax)
        if has_shared is not None and has_shared != (None, None):
            sharex, sharey = has_shared
            if sharex is not None and sharey is None:
                x_parent_pos = sibling_axes.get(sharex)
                pos = x_parent_pos[0], x_parent_pos[1] + 1
            elif sharex is None and sharey is not None:
                y_parent_pos = sibling_axes.get(sharey)
                pos = y_parent_pos[0] + 1, y_parent_pos[1]
            else:
                raise ValueError('Unknown axes configuration')
            sibling_axes[ax] = pos
    return sibling_axes


def get_twin_axes(axes_dict, xaxis, yaxis):
    """
    Return the twin axes given by `xaxis`, `yaxis`.

    Parameters
    ----------
    axes_dict : dict
        A dictionary containing at least the default axes
        with xaxis='x1' and yaxis='y1'.
    xaxis : str
        The name of the xaxis. Supported values are 'x1' and 'x2'.
    yaxis : str
        The name of the yaxis. Supported values are 'y1' and 'y2'.

    Returns
    -------
    ax : matplotlib.axes._subplots.AxesSubplot
    """
    ax = axes_dict.get((xaxis, yaxis), None)
    default_axes = axes_dict[('x1', 'y1')]
    if isinstance(default_axes, figure.SyAxes):
        default_axes = default_axes.get_mpl_axes()
    if ax is None:
        if xaxis == 'x1' and yaxis == 'y2':
            ax = default_axes.twinx()
        elif xaxis == 'x2' and yaxis == 'y1':
            ax = default_axes.twiny()
        elif xaxis == 'x2' and yaxis == 'y2':
            x1y2axes = get_twin_axes(axes_dict, 'x1', 'y2')
            ax = x1y2axes.twiny()
        else:
            raise ValueError('The axes type "{}, {}" is not '
                             'supported.'.format(xaxis, yaxis))
        axes_dict[(xaxis, yaxis)] = ax
    return ax


def classify_axes(axes):
    """
    Classify the axes in the scheme ('x1', 'y1').

    The axes get stored with a (x,y) key in a dictionary
    depending on their shared x or y axes. The first axes
    will always be set as ('x1', 'y1').
    """
    if len(axes):
        classed_axes = reconstruct_twin_axes(axes[0], axes)
        return {('x{}'.format(v[0]), 'y{}'.format(v[1])): k
                for k, v in classed_axes.iteritems()}
    return {}


def move_lines_to(source, target):
    """
    Move a line artist from a source to a target axes.

    Remove the line artist from the source mpl.axes and
    add it to the target axes.
    """
    if isinstance(target, figure.SyAxes):
        target = target.get_mpl_axes()
    if isinstance(source, figure.SyAxes):
        source = source.get_mpl_axes()
    lines = source.lines
    for line in lines:
        # this is a bit of a hack to move a line artist
        # from one axes to another
        line.remove()
        line.set_transform(IdentityTransform())
        line._transformed_path = None
        line._transformSet = False
        line._xy = None
        line._x = None
        line._y = None
        label = line.get_label()
        if label in (l.get_label() for l in target.lines):
            line.set_label('{}_2'.format(label))
        target.add_line(line)


parameter_list_to_copy = [
    # 'title',  # doesn't work for whichever reason
    'xscale',
    'yscale',
    'xlabel',
    'ylabel',
    'xlim',
    'ylim'
]


def copy_axes_parameter(source, target):
    """
    Copy axes parameters from a source to a target axes.

    Copy the parameters defined in the ``parameter_list_to_copy``
    from the ``source`` mpl axes to the ``target`` mpl axes.
    """
    if isinstance(target, figure.SyAxes):
        target = target.get_mpl_axes()
    if isinstance(source, figure.SyAxes):
        source = source.get_mpl_axes()
    for attr in parameter_list_to_copy:
        value = getattr(source, 'get_{}'.format(attr))()
        setter = getattr(target, 'set_{}'.format(attr))
        setter(value)

    # has to be done manually
    target.set_title(source.get_title())

    for saxis, taxis in zip([source.xaxis, source.yaxis],
                            [target.xaxis, target.yaxis]):
        grid_params = {}
        major_grid_on = saxis._major_tick_kw.get('gridOn', False)
        minor_grid_on = saxis._minor_tick_kw.get('gridOn', False)

        if major_grid_on and minor_grid_on:
            grid_params['which'] = 'both'
        elif major_grid_on:
            grid_params['which'] = 'major'
        elif minor_grid_on:
            grid_params['which'] = 'minor'

        line_properties = saxis.get_gridlines()[0].properties()
        for prop in ['color', 'linewidth', 'linestyle']:
            value = line_properties.get(prop, None)
            grid_params[prop] = value

        grid_params['zorder'] = 1

        taxis.grid(**grid_params)


def compress_axes(axes_of_figures, default_output_axes,
                  legends_join=False, legend_location='best',
                  copy_properties_from=0):
    """
    Compress the lines and parameters from different axes into one.

    Parameters
    ----------
    axes_of_figures : list
        List of mpl axes
    default_output_axes : axes
        Mpl axes
    legends_join : bool
        Set true if legends for different twin axes should be joined
        into one. Default False.
    legend_location : str or int
        Location of the joined legend in mpl strings or int.
        Default 'best'.
    copy_properties_from : int
        The set of twinaxes from which the axes properties should be
        copied to the resulting axes. Default 0.
    """
    default_axes = default_output_axes

    output_axes_dict = {('x1', 'y1'): default_axes}
    if copy_properties_from >= len(axes_of_figures):
        copy_properties_from = 0
        sywarn('The figure specified as source for the new axes '
               'parameter does not exist. The first figure will '
               'be used!')

    legend_in_subaxes = {}

    for idx, axes in enumerate(axes_of_figures):
        axes_dict = classify_axes(axes)
        for ax_id, source_ax in axes_dict.iteritems():
            target_ax = get_twin_axes(output_axes_dict,
                                      ax_id[0], ax_id[1])
            move_lines_to(source_ax, target_ax)

            if idx == copy_properties_from:
                copy_axes_parameter(source_ax, target_ax)

            # save if source_ax had legend
            legend = source_ax.get_legend()
            if (legend is not None and
                    (ax_id not in legend_in_subaxes or
                        idx == copy_properties_from)):
                # collect legends parameters
                legend_props = {}
                for prop in LEGEND.keys():
                    value = None
                    if hasattr(legend, prop):
                        value = getattr(legend, prop)
                    elif hasattr(legend, '_{}'.format(prop)):
                        value = getattr(legend, '_{}'.format(prop))
                    elif hasattr(legend, 'get_{}'.format(prop)):
                        value = getattr(legend, 'get_{}'.format(prop))()
                    if value is not None:
                        legend_props[prop] = value
                legend_in_subaxes[ax_id] = legend_props

    # draw legend for each axes
    legend_handles = []
    legend_lables = []
    for ax_id, props in legend_in_subaxes.iteritems():
        ax = output_axes_dict[ax_id]
        if not legends_join:
            title = props.pop('title', None)
            if title is not None and title.get_text() != u'None':
                props['title'] = title.get_text()
            ax.legend(**props)
        else:
            if isinstance(ax, figure.SyAxes):
                ax = ax.get_mpl_axes()
            handles, labels = ax.get_legend_handles_labels()
            legend_handles.extend(handles)
            labels = [u'{} {}'.format(l, str(ax_id)) for l in labels]
            legend_lables.extend(labels)
    if legends_join:
        # copy legend properties from the default axes
        parent_legend_props = legend_in_subaxes.get(('x1', 'y1'), {})
        if parent_legend_props != {}:
            parent_legend_props.pop('loc', None)
            parent_legend_props.pop('title', None)
        parent_legend_props['loc'] = legend_location
        if len(legend_lables) or len(legend_handles):
            default_axes.set_zorder(1)
            default_axes.legend(legend_handles, legend_lables,
                                **parent_legend_props)


if __name__ == '__main__':
    test_config = [['line.1.name', 'testline'],
                   # ['line.color', 'blue'],
                   ['line.xdata', 'col 1'],
                   ['line.ydata', 'y data col'],
                   ['line.1.ydata', 'col 2'],
                   ['line.1.axes', 'xy'],
                   ['line.2.ydata', 'col 3y'],
                   ['line.2.color', '123, 2'],
                   ['line.xdata', 'col 3x'],
                   ['line.3.ydata', 'col 5x'],
                   ['figure.title', 'test title'],
                   ['axes.legend.loc', 'best'],
                   ['axes.legend.markerfirst', False],
                   ['axes.xy.grid.color', '12, 12']

                   # ['axes.xy.xaxis', 'x'],
                   # ['axes.xy.yaxis', 'y'],
                   # ['axes.xy.xlim', '0, 12'],
                   # ['axes.xy.grid', True],
                   # ['axes.xy.grid.color', '(1., 1., 1.)'],
                   # ['axes.xy.legend.fancybox', True],
                   # ['axes.xy.legend.title', 'legend title'],
                   # ['axes.xy.legend.loc', 'upper left'],
                   # ['axes.x1y2.xlim', '0, 12'],
                   # ['axes.grid.color', 'red'],
                   # ['axes.legend.peter', '']  # shouldn't show up
                   ]

    # output = gen_config_by_prefix(test_config, 'line.')
    output = parse_configuration(test_config)

    for k, o in output.iteritems():
        print(k + ':')
        for id_, line in o.iteritems():
            print '\t', id_, line
