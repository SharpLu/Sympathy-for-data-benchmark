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
import collections

import numpy as np

from sylib.report import layers
from sylib.report import icons


class Layer(layers.Layer):
    """Bar layer."""

    meta = {
        'icon': icons.SvgIcon.bar,
        'label': 'Bar Plot',
        'default-data': {
            'type': 'bar',
            'data': [
                {
                    'source': '',
                    'axis': ''
                },
                {
                    'source': '',
                    'axis': ''
                }
            ]
        }
    }
    property_definitions = collections.OrderedDict((
        ('name', {'type': 'string',
                  'label': 'Name',
                  'icon': icons.SvgIcon.blank,
                  'default': 'Bar Plot'}),

        ('bar-width', {'type': 'float',
                       'label': 'Bar Width',
                       'icon': icons.SvgIcon.blank,
                       'range': {'min': 0, 'max': np.inf, 'step': 0.5},
                       'default': 0.5}),

        ('x-offset', {'type': 'float',
                      'label': 'Horizontal Offset',
                      'icon': icons.SvgIcon.blank,
                      'range': {'min': -np.inf, 'max': np.inf, 'step': 0.5},
                      'default': 0.0}),

        ('face-color', {'type': 'color',
                        'label': 'Face Color',
                        'icon': icons.SvgIcon.blank,
                        'default': '#809dd5'}),

        ('edge-color', {'type': 'color',
                        'label': 'Edge Color',
                        'icon': icons.SvgIcon.blank,
                        'default': '#000000'}),

        ('alpha', {'type': 'float',
                   'label': 'Alpha',
                   'range': {'min': 0.0, 'max': 1.0, 'step': 0.1},
                   'icon': icons.SvgIcon.blank,
                   'default': 1.0})
    ))
