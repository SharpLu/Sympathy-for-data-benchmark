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
from functools import wraps
import sys
import contextlib
import exceptions

import inspect

from ..platform.exceptions import NoDataError


def inherit_doc(cls):
    """
    Classes decorated will inherit missing __doc__ on methods from the first
    parent along the mro that provides it.
    """

    def method_doc(fname, f, mro):

        for cls_ in mro:
            f_ = getattr(cls_, fname, None)

            if f_ is not None and f_.__doc__ is not None:
                f.__func__.__doc__ = f_.__doc__
                break
        return f

    for fname, f in inspect.getmembers(cls, predicate=inspect.ismethod):
        method_doc(fname, f, cls.mro())

    return cls


def pending_deprecation(repl_fname=None):
    def decorator(f):
        def wrapper(*args, **kwargs):
            msg = "WARNING: The method '{}' will soon be removed.".format(
                f.__name__)
            if repl_fname:
                msg += " Please use {} instead.".format(repl_fname)
            print(msg)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def deprecated(message=''):
    raise exceptions.DeprecationWarning(message)


def deprecated_function(func):
    def wrapper(*args, **kwargs):
        deprecated('* Deprecated method: {}\n'.format(func.__name__))
        return func(*args, **kwargs)
    wrapper.__doc__ = func.__doc__
    return wrapper


def nested(*args):
    return contextlib.nested(*args)


class PortDummy(object):
    """
    PortDummy is returned instead of a real data type if there is no data on
    the port.

    To test if you got a real data type or only got a :class:`PortDummy` object
    use the :meth:`is_valid` method::

        input_table = node_context.input['input']
        if input_table.is_valid():
            # Data available
        else:
            # No data available, trying to use input_table will raise a
            # NoDataError.

    Accessing any other member of a :class:`PortDummy` object will raise a
    NoDataError which tells the user what to do.
    """
    def __init__(self, exc_info):
        self._exc_info = exc_info

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __getattr__(self, key):
        self.raise_error()

    def __getitem__(self, key):
        self.raise_error()

    def __iter__(self):
        self.raise_error()

    def __len__(self):
        self.raise_error()

    def raise_error(self):
        raise NoDataError(
            'No data on input port. Try connecting the input '
            'and running all previous nodes first.')

    @staticmethod
    def is_valid():
        return False


class ErrorPortDummy(PortDummy):

    def raise_error(self):
        raise self._exc_info[0], self._exc_info[1], self._exc_info[2]


class PortWrapper(object):
    """
    Wraps a contextmanager which gets called, if any error occurs during
    __enter__ it is assumed that a port file could not be opened. Such ports
    are wrapped in PortDummy so that the error can be deferred until they are
    used.
    """
    def __init__(self, port):
        self._port = port

    def __enter__(self):
        try:
            return self._port.__enter__()
        except (IOError, OSError):
            self._port = PortDummy(sys.exc_info())
        except:
            # Arbitrary errors cannot be considered NoDataError.
            self._port = ErrorPortDummy(sys.exc_info())

        return self._port

    def __exit__(self, *args):
        self._port.__exit__(*args)


def with_managers(function, managers):
    """
    Call the function with the managers opened.
    Managers are received as a list opened in the order they occur in the
    input.
    """
    failing_port = None

    try:
        with nested(*[PortWrapper(manager) for manager in managers]) as opened:
            for item in opened:
                if isinstance(item, ErrorPortDummy):
                    failing_port = item
                    return

            return function(opened)
    finally:
        if failing_port:
            failing_port.raise_error()


class RepeatContext(object):
    """Helper class for repeatcontext decorator."""

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.__gen = func(*args, **kwargs)

    @property
    def gen(self):
        with self as once:
            yield once

    def __enter__(self):
        try:
            return self.__gen.next()
        except StopIteration:
            self.__gen = self.func(*self.args, **self.kwargs)
            try:
                return self.__gen.next()
            except StopIteration:
                raise RuntimeError('Invalid generator')

    def __exit__(self, *args):
        try:
            self.__gen.next()
        except StopIteration:
            return
        else:
            raise RuntimeError('Invalid generator')


def repeatcontext(func):
    """
    Decorator which allows a generator to be called again after StopIteration.

    >>> @repeatcontext
    ... def test():
    ...     print("'enter'")
    ...     yield
    ...     print("'exit'")

    >>> gen = test()

    >>> with gen:
    ...     pass
    'enter'
    'exit'

    >>> with gen:
    ...     pass
    'enter'
    'exit'

    """

    @wraps(func)
    def helper(*args, **kwargs):
        return RepeatContext(func, *args, **kwargs)
    return helper
