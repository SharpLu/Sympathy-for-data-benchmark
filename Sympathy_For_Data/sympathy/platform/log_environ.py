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
"Package for logging environment information."
import os
import sys
import site
import json

from datetime import datetime
from collections import OrderedDict
 

separator = '\n\n'


site_table = OrderedDict((
    ('ENABLE_USER_SITE', site.ENABLE_USER_SITE),
    ('USER_SITE', site.USER_SITE),
    ('USER_BASE', site.USER_BASE),
    ('PREFIXES', site.PREFIXES)))

sys_table = OrderedDict((
    ('version', sys.version),
    ('prefix', sys.prefix),
    ('exec_prefix', sys.exec_prefix),
    ('path_hooks', str(sys.path_hooks)),
    ('path', sys.path)))

log_entries = OrderedDict((
    ('Sympathy startup log', ''),
    ('Log date', str(datetime.now())),
    ('Site setup', site_table),
    ('Sys setup', sys_table),
    ('Environment setup', dict(os.environ))))


def write(filename):
    "Write new entry to log file name."
    with open(filename, 'a') as logfile:
        logfile.write(separator)
        logfile.write((json.dumps(log_entries, indent=4)))


def read(filename):
    "List of log entries from filename."
    with open(filename) as logfile:
        return [json.loads(entry)
                for entry in logfile.read().split(separator) if entry != '']


def usage():
    "Print usage information."
    print('usage: python log_environ.py filename')


if __name__ == '__main__':
    try:
        logfilename = sys.argv[1]
    except IndexError:
        usage()
    try:
        write(logfilename)
    except:
        print('Error writing log')
