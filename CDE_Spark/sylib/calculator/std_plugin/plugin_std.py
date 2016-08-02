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
import collections

from sylib.calculator import plugins
from sylib.calculator.std_plugin import basics, logics, event_detection, plugin_matlab


class PluginWrapper(object):
    """Merge two or more module-like objects into one.

    getattr calls on PluginWrapper objects are passed on to the module-like
    objects and the first one which doesn't raise AttributeError gets to return
    its result.
    """
    def __init__(self, *namespaces):
        self._namespaces = list(namespaces)

    def __getattr__(self, attr):
        for ns in self._namespaces:
            try:
                return getattr(ns, attr)
            except AttributeError:
                pass

        raise AttributeError(attr)


class StdPlugin(plugins.ICalcPlugin):
    """Standard plugin for calculator node."""

    # This plugin should be listed first:
    WEIGHT = -1

    @staticmethod
    def gui_dict():
        gui_dict = collections.OrderedDict()
        gui_dict.update(basics.GUI_DICT)
        gui_dict.update(logics.GUI_DICT)
        gui_dict.update(event_detection.GUI_DICT)
        return gui_dict

    @staticmethod
    def globals_dict():
        return {'ca': PluginWrapper(basics.LogicOperator,
                                    logics.Logics,
                                    event_detection.EventDetection)}

class MatlabPlugin(plugins.MatlabCalcPlugin):
    """Standard plugin for calculator node."""

    # This plugin should be listed first:
    WEIGHT = -1

    @staticmethod
    def gui_dict():
        gui_dict = collections.OrderedDict()
        gui_dict.update(plugin_matlab.GUI_DICT)

        return gui_dict

    @staticmethod
    def globals_dict():
        return {'ca': PluginWrapper(plugin_matlab.GUI_DICT)}
