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
from __future__ import (print_function, division, unicode_literals,
                        absolute_import)
import sys
import os.path
from collections import OrderedDict

from sympathy.utils.components import get_file_env, get_subclasses_env
from sympathy.types import types
from sympathy.platform import qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module('QtGui')


def match_cls(cls, arg_type, multi):
    if multi and not cls.list_wrapper:
        try:
            arg_type = arg_type[0]
        except:
            return False
    return any([types.match(types.from_string(arg_type_), arg_type)
                for arg_type_ in cls.arg_types])


class PyfileWrapper(object):
    """Extract classes that extend a given base class (functions) from a
    python file. Used to extract function names for node_function_selector.
    """

    def __init__(self, fq_source_filename, base_class, arg_type, multi):

        arg_type = types.from_string(arg_type)
        if types.generics(arg_type):
            self._classes = {}
        elif fq_source_filename:
            sys_path = sys.path[:]
            if fq_source_filename.endswith('None'):
                raise IOError(fq_source_filename)
            sys.path.append(
                os.path.dirname(os.path.abspath(fq_source_filename)))

            self._classes = get_subclasses_env(
                get_file_env(fq_source_filename), base_class)
            self._classes = OrderedDict(
                [(k, v) for k, v in self._classes.items()
                 if match_cls(v, arg_type, multi)])
            # Restore sys.path.
            sys.path[:] = sys_path
        else:
            self._classes = {}

    def get_class(self, class_name):
        """Retrieve a single class from the supplied python file.
        Raises NameError if the class doesn't exist.
        """
        try:
            return self._classes[class_name]
        except KeyError:
            raise NameError

    def function_names(self):
        """Extract the names of classes that extend the base class in the
        supplied python file.
        """
        # Only select classes that extend the base class
        return self._classes.keys()
