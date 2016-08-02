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
This script will modify the way that IPython prints sympathy data types.

Any object which is an instance of the sympathy.utils.filebase.PPrintUnicode
class will be printed by calling its __unicode__ method instead of the default
__repr__ method.
"""
# Importing this monkeypathes distutils (do not remove).
import setuptools as _setuptools  # NOQA
import os as _os


def CCompiler_spawn_quote_monkey(self, cmd, display=None):
    """
    Quoting patch to avoid problems compiling on Windows when the
    installation folder contains space.

    Spaces in the path has been known to cause problems for scipy.weave.inline.
    """
    if _ccompiler.is_sequence(cmd):
        cmd = ['"' + cm + '"' if ' ' in cm and '"' not in cm else cm
               for cm in cmd]
    return _ccompiler.CCompiler_spawn(self, cmd, display)


if _os.name == 'nt':
    # Apply compiler patch on Windows.
    from numpy.distutils import ccompiler as _ccompiler
    _ccompiler.replace_method(
        _ccompiler.CCompiler, 'spawn', CCompiler_spawn_quote_monkey)

try:
    ipython = get_ipython()
except NameError:
    pass
else:
    from sympathy.utils import filebase as _filebase

    formatter = ipython.display_formatter.formatters['text/plain']
    formatter.for_type(
        _filebase.PPrintUnicode, lambda arg, p, cycle: p.text(unicode(arg)))
