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


def get_known_mpl_colors(add_single_letter_colors=True):
    colors = list(mpl_colors.cnames.iteritems())
    # Add the single letter colors.
    if add_single_letter_colors:
        for name, rgb in mpl_colors.ColorConverter.colors.iteritems():
            hex_ = mpl_colors.rgb2hex(rgb)
            colors.append((name, hex_.lower()))
    # sort by name
    colors.sort()
    return dict(colors)


COLORS = get_known_mpl_colors()
COLORS_INV = {v.lower(): k for k, v in get_known_mpl_colors(add_single_letter_colors=False).iteritems()}


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
    text = unicode(text)
    # hex color
    is_hex = re.search(r'#[0-9a-fA-F]{6,8}', text)
    is_float, is_int = parse_number_colors(text)

    if text in COLORS.keys():
        # named color
        return text
    elif is_hex:
        hex_c = is_hex.group() if is_hex is not None else None
        rgba = list(mpl_colors.hex2color(hex_c[:7]))
        if len(hex_c) == 9:
            rgba.append(int(hex_c[-2:], 16) / 255.)
        return rgba
    elif is_int is not None:
        return list(is_int / 255.)
    elif is_float is not None:
        return list(is_float)
    return None


def get_color_dev(text):
    """
    Returns the type used to define the color ('name', 'rgb', etc).

    Parameters
    ----------
    text : unicode
        The color defined as unicode.

    Returns
    -------
    str
        One of ['name', 'hex', 'rgb', 'rgba', 'rgbF', 'rgbaF', None].
    """
    text = unicode(text)
    is_float, is_int = parse_number_colors(text)

    if text in COLORS.keys():
        # named color
        return 'name'
    elif re.search(r'#[0-9a-fA-F]{6,8}', text):
        return 'hex'
    elif is_float is not None and len(is_float) == 3:
        return 'rgbF'
    elif is_float is not None and len(is_float) == 4:
        return 'rgbaF'
    elif is_int is not None and len(is_int) == 3:
        return 'rgb'
    elif is_int is not None and len(is_int) == 4:
        return 'rgba'
    return None


def parse_number_colors(text):
    text = unicode(text)
    # rgb colors
    ex = r"(?: (?: \d* \. \d+ ) | (?: \d+ \.? ) )"
    rx = re.compile(ex, re.VERBOSE)
    numbers = rx.findall(text)
    is_float = np.float_(numbers)
    if is_float is None or np.any(is_float > 1.) or len(is_float) not in [3, 4]:
        is_float = None
    try:
        is_int = np.int_(numbers)
        if is_int is None or np.any(is_int > 255) or len(is_int) not in [3, 4] or '.' in text:
            is_int = None
    except ValueError:
        is_int = None
    return is_float, is_int


def get_color_as_rgba_f(color):
    color_dev = get_color_dev(color)
    a = 1.
    if color_dev == 'name':
        hex_color = COLORS[color]
        rgbf = mpl_colors.hex2color(hex_color)
    elif color_dev == 'hex':
        rgbf = mpl_colors.hex2color(color[:7])
        if len(color) > 7:
            a = int(color[-2:], 16) / 255.
    elif color_dev == 'rgb':
        rgbf = parse_color_to_mpl_color(color)
    elif color_dev == 'rgba':
        rgbaf = parse_color_to_mpl_color(color)
        a = rgbaf[-1]
        rgbf = rgbaf[:3]
    elif color_dev == 'rgbF':
        rgbf = parse_color_to_mpl_color(color)
    elif color_dev == 'rgbaF':
        rgbaf = parse_color_to_mpl_color(color)
        rgbf = rgbaf[:3]
        a = rgbaf[-1]
    else:
        return None

    rgbaf = tuple(list(rgbf) + [a])
    return rgbaf