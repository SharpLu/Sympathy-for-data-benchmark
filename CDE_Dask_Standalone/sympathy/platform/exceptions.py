# Copyright (c) 2014, System Engineering Software Society
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
"""Exceptions for use in Sympathy nodes."""
from __future__ import print_function
# import warnings
import sys
# import linecache


# def _show_warning(message, category, filename, lineno, file=None, line=None):
#     """Function hook to show warning with better unicode support."""
#     if file is None:
#         file = sys.stderr
#     try:
#         print(_formatwarning(message, category, filename, lineno, line),
#               file=file)
#     except IOError:
#         pass

# warnings.showwarning = _show_warning


# def _formatwarning(message, category, filename, lineno, line=None):
#     """Function to format a warning with better unicode support."""
#     s = u'{}:{}: {}: {}'.format(filename, lineno, category.__name__,
#                                 message)
#     line = linecache.getline(filename, lineno) if line is None else line
#     if line:
#         line = line.strip()
#         s += u'\n  {}'.format(line)
#     return s


# def sywarn(message, stack=True, stacklevel=2):
#     """Notify the user of a node error."""
#     if stack:
#         with warnings.catch_warnings():
#             warnings.simplefilter('always')
#             warnings.warn(message, stacklevel=stacklevel)
#     else:
#         print(message, file=sys.stderr)

def sywarn(message, stack=True, stacklevel=2):
    """Notify the user of a node error."""
    print(message, file=sys.stderr)


class NoDataError(Exception):
    """Raised when trying to access data on an input port which has no data."""
    pass


class SyNodeError(Exception):
    """
    An error occurred in the node. See the specific error message for details.
    For further information, please refer to the node's documentation.
    """

    @property
    def help_text(self):
        """Detailed help text.

        Default implementation returns class docstring. Override to implement
        custom behaviour.
        """
        return self.__doc__


class SyDataError(SyNodeError):
    """
    There is something wrong with the data that this node received. See the
    specific error message for details. For help with the requirements
    on the input data for this node, please refer to the node's documentation.
    """
    # Raise this when the user should be notified of an error in the input
    # data for a node.
    pass


class SyConfigurationError(SyNodeError):
    """
    There is an error in the node's configuration. See the specific error
    message for details. For further information about the requirements of the
    configuration for this node, please refer to the node's documentation.
    """
    # Raise this when the user should be notified of an error in the input
    # configuration for a node.
    pass
