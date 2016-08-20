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
import unittest

from sylib.figure.util import parse_configuration
from sylib.figure.colors import COLORS, parse_color_to_mpl_color


class ParseStringToMPLColorTestCase(unittest.TestCase):
    def test_mpl_colors(self):
        for c in COLORS:
            self.assertEqual(c, parse_color_to_mpl_color(c))

    def test_hex_color(self):
        text = '#ffffff'
        result = [1., 1., 1.]
        self.assertEqual(result, parse_color_to_mpl_color(text))

    def test_hexa_color(self):
        text = '#ffffffff'
        result = [1., 1., 1., 1.]
        self.assertEqual(result, parse_color_to_mpl_color(text))

    def test_rgb_int_color(self):
        test_cases = ['255, 255, 255',
                      '1, 1, 1']
        results = [[1., 1., 1.],
                   [1/255., 1/255., 1/255.]]
        for case, result in zip(test_cases, results):
            self.assertEqual(result, parse_color_to_mpl_color(case))

    def test_rgba_int_color(self):
        test_cases = ['255, 255, 255, 255',
                      '(255, 255, 255, 255)']
        result = [1., 1., 1., 1.]
        for case in test_cases:
            self.assertEqual(result, parse_color_to_mpl_color(case))

    def test_rgb_float_color(self):
        test_cases = ['1., 1., 1.',
                      '(1., 1., 1.)',
                      '1., 1. 1.',
                      '1 1 1.']
        result = [1., 1., 1.]
        for case in test_cases:
            self.assertEqual(result, parse_color_to_mpl_color(case))

    def test_rgba_float_color(self):
        text = '1., 1., 1., 1.'
        result = [1., 1., 1., 1.]
        self.assertEqual(result, parse_color_to_mpl_color(text))

    def test_wrong_imput(self):
        test_cases = ['255, 255',
                      '#ffes',
                      '#ffeegg',
                      '256, 1, 1']
        for text in test_cases:
            self.assertEqual(None, parse_color_to_mpl_color(text))


class ParseConfigurationTestCase(unittest.TestCase):
    def test_prase_configuration(self):
        test_case = [
            ('figure.title', 'figure title'),
            ('axes.id.xaxis', 'x1'),
            ('axes.id.yaxis', 'y1'),
            ('axes.id.grid.color', 'g'),
            ('axes.id.legend.loc', 'upper left'),
            ('line.l1.xdata', 'index'),
            ('line.l1.ydata', 'signal'),
            ('line.l1.axes', 'id')
        ]
        result = {'axes': {'id': {'xaxis': 'x1',
                                  'yaxis': 'y1',
                                  'grid': {'show': True,
                                           'color': 'g'},
                                  'legend': {'show': True,
                                             'loc': 'upper left'}}},
                  'line': {'l1': {'xdata': 'index',
                                  'ydata': 'signal',
                                  'axes': 'id',
                                  'valid': True}},
                  'figure': {'title': 'figure title'}}
        self.assertEqual(result, parse_configuration(test_case))


def runModelTest(): # noqa
    test_loader = unittest.TestLoader()
    test_loader.loadTestsFromTestCase(ParseStringToMPLColorTestCase)
    unittest.TextTestRunner(verbosity=2)
