# -*- coding: utf-8 -*-
# Copyright (c) 2016, System Engineering Software Society
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
The considered category of nodes includes a number of common tuple operations.
    - Zip
    - Unzip
    - First
    - Second
    - Tuple
    - Untuple
    - Carthesian product
"""
from itertools import izip, product
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags


class SuperNodeGeneric(synode.Node):
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2016 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.Tuple)


class Tuple2(SuperNodeGeneric):
    """Create a two element tuple (pair) from two items."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Tuple2'
    nodeid = 'org.sysess.sympathy.tuple.tuple2'

    inputs = Ports([
        Port.Custom('<a>', 'First'),
        Port.Custom('<b>', 'Second')])
    outputs = Ports([
        Port.Custom('(<a>, <b>)', 'Tuple')])

    def execute(self, node_context):
        out = node_context.output[0]
        for i, item in enumerate(node_context.input):
            out[i] = node_context.input[i]


class FirstTuple2(SuperNodeGeneric):
    """Get the first element out of a two element tuple (pair)."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'First Tuple2'
    nodeid = 'org.sysess.sympathy.tuple.firsttuple2'

    inputs = Ports([
        Port.Custom('(<a>, <b>)', 'Tuple')])

    outputs = Ports([
        Port.Custom('<a>', 'First')])

    def execute(self, node_context):
        node_context.output[0].source(node_context.input[0][0])


class SecondTuple2(SuperNodeGeneric):
    """Get the second element out of a two element tuple (pair)."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Second Tuple2'
    nodeid = 'org.sysess.sympathy.tuple.secondtuple2'

    inputs = Ports([
        Port.Custom('(<a>, <b>)', 'Tuple2')])

    outputs = Ports([
        Port.Custom('<b>', 'Second')])

    def execute(self, node_context):
        node_context.output[0].source(node_context.input[0][1])


class Untuple2(SuperNodeGeneric):
    """Get two output elements out of a two element tuple (pair)."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Untuple2'
    nodeid = 'org.sysess.sympathy.tuple.untuple2'

    inputs = Ports([
        Port.Custom('(<a>, <b>)', 'Tuple2')])

    outputs = Ports([
        Port.Custom('<a>', 'First'),
        Port.Custom('<b>', 'Second')])

    def execute(self, node_context):
        for in_, out in izip(node_context.input[0], node_context.output):
            out.source(in_)


class CarthesianProductTuple2(synode.Node):
    """Create a list of two element tuples (pairs) from two lists."""

    copyright = '(C) 2016 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.Tuple)
    author = 'Magnus Sandén <magnus.sanden@sysess.org>'
    name = 'Carthesian Product Tuple2'
    nodeid = 'org.sysess.sympathy.tuple.carthesianproduct2'

    inputs = Ports([
        Port.Custom('[<a>]', 'First List'),
        Port.Custom('[<b>]', 'Second List')])

    outputs = Ports([
        Port.Custom('[(<a>, <b>)]', 'List with all combinations')])

    def execute(self, node_context):
        inputs = list(node_context.input)
        outlist = node_context.output[0]

        for pytuple in product(*inputs):
            sytuple = outlist.create()

            for i, item in enumerate(pytuple):
                sytuple[i] = item
            outlist.append(sytuple)


class ZipTuple2(SuperNodeGeneric):
    """Create a list of two element tuples (pairs) from two lists."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Zip Tuple2'
    nodeid = 'org.sysess.sympathy.tuple.ziptuple2'

    inputs = Ports([
        Port.Custom('[<a>]', 'First List'),
        Port.Custom('[<b>]', 'Second List')])

    outputs = Ports([
        Port.Custom('[(<a>, <b>)]', 'Tuple2 List')])

    def execute(self, node_context):
        inputs = list(node_context.input)
        outlist = node_context.output[0]

        for pytuple in izip(*inputs):
            sytuple = outlist.create()

            for i, item in enumerate(pytuple):
                sytuple[i] = item
            outlist.append(sytuple)


class UnzipTuple2(SuperNodeGeneric):
    """Create two list outputs from list of two element tuples (pairs)."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Unzip Tuple2'
    nodeid = 'org.sysess.sympathy.tuple.unziptuple2'

    inputs = Ports([
        Port.Custom('[(<a>, <b>)]', 'Tuple2 List')])

    outputs = Ports([
        Port.Custom('[<a>]', 'First List'),
        Port.Custom('[<b>]', 'Second List')])

    def execute(self, node_context):
        in_list = node_context.input[0]
        outs = list(node_context.output)

        for tuple2 in in_list:
            for i, item in enumerate(tuple2):
                outs[i].append(item)
