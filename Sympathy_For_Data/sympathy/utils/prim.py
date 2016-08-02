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
"""
Module for primitive, but useful, operations on files, lists and dictionaries.
"""
from collections import OrderedDict
from itertools import islice
from contextlib import contextmanager
import re
import os
import urllib
import urlparse


def containing_dirs(paths):
    """
    Filter contained paths leaving only the ones that are not contained in a
    subdirectory of any other path.
    Returns filtered paths.

    >>> paths = ['/usr/bin', '/usr', '/usr/local', '/opt', '/opt/local']
    >>> get_containing_dirs(paths)
    ['/usr', '/opt']
    """
    normal = [os.path.normcase(os.path.realpath(path)).rstrip(os.path.sep)
              for path in paths]
    unique = OrderedDict.fromkeys(normal).keys()
    return [path for path in unique
            if not any(path.startswith(other)
                       for other in unique if other != path)]


@contextmanager
def open_url(url):
    open_file = None
    parsed = urlparse.urlparse(url)
    if parsed.scheme == 'file' or parsed.scheme == '':
        url = uri_to_path(parsed.path)
        opener = open
    else:
        opener = urllib.urlopen
    try:
        open_file = opener(url)
        yield open_file
    finally:
        if open_file is not None:
            open_file.close()


def dottedpath(path):
    return path.replace(os.path.sep, '.').replace(':.', '.')


def uri_to_path(url):
    """Create a local file path from a URI."""
    if isinstance(url, unicode):
        url = url.encode('ascii')
    path = urlparse.urlparse(url).path
    local_path = urllib.url2pathname(path).decode('utf8')
    return local_path


def localuri(path):
    """Create absolute uri from absolute local path."""
    encoded_path = urllib.pathname2url(path.encode('utf8'))
    return urlparse.urljoin('file:', encoded_path)


def unipath(path):
    """
    Returns universal path for usage in URL, changing all native file
    separators to forward slashes (``'/'``).
    >>> unipath('/usr/bin')
    '/usr/bin'

    However:
    unipath('C:\\Users') should evaluate to C:/Users, on windows and other
    systems where \\ is a separator.
    """
    return os.path.normpath(path)
    # normpath = os.path.normpath(path)
    # seppath = normpath.split(os.sep)
    # return '/'.join(seppath)


def nativepath(path):
    """
    Returns a native path from an URL, changing all forward slashes to native
    file separators.
    """
    normpath = os.path.normpath(path)
    seppath = normpath.split('/')
    return os.sep.join(seppath)


def concat(nestedlist):
    """
    Concatenate one level of list nesting.
    Returns a new list with one level less of nesting.
    """
    return [item for sublist in nestedlist for item in sublist]


def flip(nested):
    """
    Flips a double nested dict so that the inner dict becomes the outer one.
    Returns a new flipped dictionary.
    """
    result = {}
    for key1, value1 in nested.items():
        for key2, value2 in value1.items() if value1 else {}:
            result[key2] = result.get(key2, {})
            result[key2][key1] = value2
    return result


def group_pairs(pair_list):
    """Return new list of key-value pairs grouped by key."""
    result = OrderedDict()
    for key, value in pair_list:
        acc = result.setdefault(key, [])
        acc.append(value)
    return result.items()


def ungroup_pairs(pair_list):
    """Return new ungrouped list of key-value pairs."""
    return [(key, value) for key, values in pair_list for value in values]


def fuzzy_filter(pattern, items):
    """Filter items whose keys do not match pattern."""
    def fix(char):
        special = """'"*^-.?${},+[]()"""
        if char in special:
            return '\\' + char
        else:
            return char

    escaped = [fix(char) for char in pattern]
    pattern = re.compile('.*'.join([''] + escaped + ['']), re.IGNORECASE)
    return [(key, value) for key, value in items
            if pattern.match(key)]


def nth(iterable, n, default=None):
    "Returns the nth item or a default value."
    return next(islice(iterable, n, None), default)


def encode_basic(basic, encoding='utf-8'):
    """
    Encode basic structure consisting of basic python types, such as the
    result of using json.load so that all unicode strings are encoded.
    Dictionary keys included.
    Return new encoded structure.
    """
    if isinstance(basic, dict):
        return {encode_basic(key, encoding): encode_basic(value, encoding)
                for key, value in basic.iteritems()}
    elif isinstance(basic, list):
        return [encode_basic(value, encoding) for value in basic]
    elif isinstance(basic, unicode):
        return basic.encode(encoding)
    else:
        return basic


def memoize(function):
    """Memoization of function with non-keyword arguments."""
    memoized = {}

    def wrapper(*args):
        if args not in memoized:
            result = function(*args)
            memoized[args] = result
            return result
        return memoized[args]
    wrapped_function = wrapper
    wrapped_function.__name__ = wrapper.__name__
    wrapped_function.__doc__ = wrapper.__doc__
    return wrapped_function


def combined_key(string):
    """
    Alphanumeric key function.
    It computes the sorting key from string using the string and integer parts
    separately.
    """
    def to_int(string):
        try:
            return int(string)
        except ValueError:
            return string
    return [to_int(part) for part in re.split('([0-9]+)', string)]


def absolute_paths(root, paths):
    return [path if os.path.isabs(path)
            else os.path.normpath(os.path.join(root, path))
            for path in paths]


def import_statements(filenames):
    """Return a list of all import statements in filenames."""
    regex = re.compile(
        '^((?:import .*|from [^\.][^\n]* import (?:\([^\)]+\)|.*)?))',
        re.MULTILINE)
    result = []

    for filename in filenames:
        try:
            with open(filename) as f:
                result.extend(re.findall(regex, f.read()))
        except:
            pass

    return sorted(set(
        re.sub('[ ]+', ' ',
               re.sub('[\n\r()]', ' ', i)).rstrip()
        for i in set(result)))


def limit_traceback(full_traceback, filename=None):
    """Take a full traceback in the format returned by traceback.format_exception
    and return a string produced by joining the lines.

    If filename is specified then traceback rows that are found before the
    first line containing filename will be dropped.
    """
    if filename is None:
        return ''.join(full_traceback)

    filename = os.path.basename(filename)
    start = 1

    for i, row in enumerate(full_traceback):
        if filename in row:
            start = i
            break

    return ''.join([full_traceback[0]] + full_traceback[start:])


def resources_path():
    """Return the path to the Resource folder."""
    path = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(path, '..', '..', '..',
                                        'Gui', 'Resources'))


def icons_path():
    """Return the path to the icons folder."""
    return os.path.join(resources_path(), 'icons')


def get_icon_path(name):
    """Return the absolute path for the icon with name `name`."""
    return os.path.join(icons_path(), name)
