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
import fnmatch
import inspect
import os
from collections import defaultdict
from collections import OrderedDict

from . prim import containing_dirs
from .. platform import state


COMPONENTS = defaultdict(lambda: defaultdict(list))


class IComponent(object):
    """
    Base class for discoverable components.
    Specific interface for a particular kind of components should be determined
    by creating a subclass of IComponent.
    """
    pass


def get_support_dirs(dirs=None):
    """
    Return list of support directories to scan for components.
    The method relies on state.node_state().attributes having following fields:
        'support_dirs'
        'library_dirs'
    These are normally setup by worker_subprocess.worker.
    """
    if not dirs:
        support = state.node_state().attributes['support_dirs'] or []
        library = [
            path
            for path in state.node_state().attributes['library_dirs'] or []]
        dirs = library + support
    return containing_dirs(dirs)


def get_file_env(filename):
    """
    Return the environment resulting from executing the file in an empty
    environment.
    """
    env = OrderedDict()
    try:
        with open(filename) as f:
            safe_filename = filename.encode('ascii', 'replace')
            compiled = compile(f.read(), safe_filename, 'exec')
            eval(compiled, env, env)
    except Exception as exc:
        import traceback
        print(u'Error compiling {}'.format(filename))
        print(exc)
        traceback.print_exc()
    return env


def get_classes_env(env):
    """Return the class instances in env."""
    return OrderedDict((key, value) for key, value in env.iteritems()
                       if inspect.isclass(value))


def get_subclasses_env(env, baseclass):
    """Return the class instances in env that are subclasses of baseclass."""
    return OrderedDict((key, value) for key, value in env.iteritems()
                       if inspect.isclass(value)
                       and issubclass(value, baseclass)
                       and value is not baseclass)


def scan_components(pattern, kind, dirs=None):
    """
    Scan python path for available components matching pattern and kind.
    Pattern is a glob pattern matched against the filename and kind is the base
    class for a group of components.
    """
    matches = []
    for path in get_support_dirs(dirs):
        for root, dirs, files in os.walk(path):
            matches.extend([os.path.abspath(os.path.join(root, f))
                            for f in fnmatch.filter(files, pattern)])
    return [value
            for match in matches
            for value in get_subclasses_env(
                get_file_env(match), kind).itervalues()]


def get_components(pattern, kind, dirs=None):
    """
    Get list of components for the given kind.
    If no components are found, a scan is performed.
    """
    result = COMPONENTS[str(kind)]
    if result:
        return result
    else:
        result = scan_components(pattern, kind, dirs)
        COMPONENTS[str(kind)] = result
    return result
