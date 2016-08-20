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
The nodes :ref:`Filter Tables with Table input` and
:ref:`Filter ADAFs with Table input` are very
similiar. They both take a table on the upper port and use it to filter the
list on the lower port. The table must contain a single column and should be at
least as long as the list on the lower port. Lets call it the filter-column.
Now for each Table or ADAF in the incoming list the corresponding index of
the filter-column is inspected. If it is True (or is considered True in Python,
e.g. any non-zero integer or a non-empty string) the Table or ADAF is included
in the filtered list. And vice versa, if the value in the filter-column is
False (or is considered False in Python, e.g. 0 or an empty string) the
corresponding Table or ADAF is not included in the filtered list.
"""
import numpy as np
from itertools import izip

from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sylib import util
from sympathy.platform.exceptions import sywarn


class FilterADAFsTable(synode.Node):
    """
    Filter a list of ADAFs using an incoming table.

    :Inputs:
        **Filter** : Table
            Table with a single column that will be used filter column.
        **List of adafs** : ADAFs
            Incoming list of ADAFs.
    :Outputs:
        **Filtered list** : ADAFs
            The filtered list with ADAFs.
    """

    name = "Filter ADAFs with Table input"
    nodeid = "org.sysess.sympathy.list.filteradafstable"
    description = "Filter a list of ADAFs using an incoming table."
    icon = "filter_list.svg"
    author = "Magnus Sanden <magnus.sanden@combine.se>"
    copyright = "(c) 2013 Combine AB"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.Table('Filter', name="filter"),
                    Port.ADAFs('List of ADAFs', name="in")])
    outputs = Ports([Port.ADAFs('Filtered ADAFs', name="out")])

    def execute(self, node_context):
        infiles = node_context.input['in']
        outfiles = node_context.output['out']
        try:
            filterfile = node_context.input['filter']
            filter_values = filterfile.get_column_to_array('filter')

            for filter_value, infile in izip(filter_values, infiles):
                if filter_value:
                    outfiles.append(infile)
        except KeyError:
            sywarn("The filter table has no column 'filter', "
                   "passing through data.")
            outfiles.source(infiles)


class FilterTablesTable(synode.Node):
    """Filter a list of tables using an incoming table.

    :Inputs:
        **Filter** : Table
            Table with a column used as the filter column.
        **List of tables** : Tables
            Incoming list of Tables.
    :Outputs:
        **Filtered list** : Tables
            The filtered list with Tables.
    """

    name = "Filter Tables with Table input"
    nodeid = "org.sysess.sympathy.list.filtertablestable"
    description = "Filter a list of tables using an incoming table."
    icon = "filter_list.svg"
    author = "Magnus Sanden <magnus.sanden@combine.se>"
    copyright = "(c) 2013 Combine AB"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.Table('Filter', name="filter"),
                    Port.Tables('List of Tables', name="in")])
    outputs = Ports([Port.Tables('Filtered Tables', name="out")])

    def execute(self, node_context):
        filterfile = node_context.input['filter']
        if filterfile.number_of_rows() == 0:
            node_context.output['out'].source(node_context.input['in'])
            return
        filter_values = filterfile.get_column_to_array('filter')
        infiles = node_context.input['in']
        outfiles = node_context.output['out']

        for filter_value, infile in izip(filter_values, infiles):
            if filter_value:
                outfiles.append(infile)


class FilterListTable(synode.Node):
    """Filter a list using an incoming table."""

    name = "Filter List with Table input"
    nodeid = "org.sysess.sympathy.list.filterlisttable"
    description = "Filter a list using an incoming table."
    icon = "filter_list.svg"
    author = "Magnus Sanden <magnus.sanden@combine.se>"
    copyright = "(c) 2016 Combine AB"
    version = '1.0'
    tags = Tags(Tag.DataProcessing.List)

    inputs = Ports([Port.Table('Filter', name="filter"),
                    Port.Custom('[<a>]', 'List of items', name='in')])
    outputs = Ports(
        [Port.Custom('[<a>]', 'Filtered list of items', name='out')])

    def execute(self, node_context):
        filterfile = node_context.input['filter']
        if filterfile.number_of_rows() == 0:
            node_context.output['out'].source(node_context.input['in'])
            return
        filter_values = filterfile.get_column_to_array('filter')
        infiles = node_context.input['in']
        outfiles = node_context.output['out']

        for filter_value, infile in izip(filter_values, infiles):
            if filter_value:
                outfiles.append(infile)


def predicate_function(node_context):
    predicate_str = node_context.parameters['predicate'].value
    return util.base_eval(predicate_str)


def filter_with_predicate(node_context):
    infiles = node_context.input['in']
    outfiles = node_context.output['out']
    index = node_context.output['index']
    predicate_fn = predicate_function(node_context)

    index_data = []
    for infile in infiles:
        if predicate_fn(infile):
            outfiles.append(infile)
            index_data.append(True)
        else:
            index_data.append(False)

    index.set_column_from_array('filter', np.array(index_data))


class FilterTablesPredicate(synode.Node):
    """
    Filter a list of Tables using a predicate.

    :Inputs:
        **Input data Tables** : Tables
            Incoming list of Tables.
    :Outputs:
        **Output data Tables** : Tables
            Outgoing, filtered, list of Tables.
        **Output index Table** : Table
            Outgoing Table, containing 'filter' - a boolean index column.
    """

    name = "Filter Tables Predicate"
    nodeid = "org.sysess.sympathy.list.filtertablespredicate"
    description = "Filter a list using configured item based predicate."
    icon = "filter_list.svg"
    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.Tables('Input data Tables', name="in")])
    outputs = Ports([Port.Table('Output index Table', name="index"),
                     Port.Tables('Output data Tables (Filtered)', name="out")])

    parameters = synode.parameters()
    parameters.set_string(
        'predicate',
        label='Predicate filter function',
        value='lambda x: True  # Identity filter',
        description='Filter function')

    def verify_parameters(self, node_context):
        try:
            predicate_function(node_context)
        except:
            return False
        return True

    def execute(self, node_context):
        filter_with_predicate(node_context)


class FilterADAFsPredicate(synode.Node):
    """Filter a list of ADAFs using a predicate.

    :Inputs:
        **Input data ADAFs** : ADAFs
            Incoming list of ADAFs.
    :Outputs:
        **Output data ADAFs** : ADAFs
            Outgoing, filtered, list of ADAFs.
        **Output index Table** : Table
            Outgoing Table, containing 'filter' - a boolean index column.
    """

    name = "Filter ADAFs Predicate"
    nodeid = "org.sysess.sympathy.list.filteradafspredicate"
    description = "Filter a list using configured item based predicate."
    icon = "filter_list.svg"
    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.ADAFs('Input data ADAFs', name="in")])
    outputs = Ports([Port.Table('Output index Table', name="index"),
                     Port.ADAFs('Output data ADAFs (Filtered)', name="out")])

    parameters = synode.parameters()
    parameters.set_string(
        'predicate',
        label='Predicate filter function',
        value='lambda x: True  # Identity filter',
        description='Filter function')

    def verify_parameters(self, node_context):
        try:
            predicate_function(node_context)
        except:
            return False
        return True

    def execute(self, node_context):
        filter_with_predicate(node_context)


def partition_with_predicate(node_context):
    infiles = node_context.input['in']
    truefiles = node_context.output['true']
    falsefiles = node_context.output['false']
    predicate_fn = predicate_function(node_context)

    for infile in infiles:
        if predicate_fn(infile):
            truefiles.append(infile)
        else:
            falsefiles.append(infile)


class PartitionTablesPredicate(synode.Node):
    """Partition a list of Tables using a predicate."""

    name = "Partition Tables Predicate"
    nodeid = "org.sysess.sympathy.list.partitiontablespredicate"
    description = "Partition a list using configured item based predicate."
    icon = "partition_list.svg"
    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.Tables('Input data Tables', name="in")])
    outputs = Ports(
        [Port.Tables(
            'Output data Tables where predicate returns True', name='true'),
         Port.Tables(
             'Output data Tables where predicate returns False',
             name='false')])

    parameters = synode.parameters()

    parameters.set_string(
        'predicate',
        label='Predicate partition function',
        value='lambda x: True  # Identity partition',
        description='Partition function')

    def verify_parameters(self, node_context):
        try:
            predicate_function(node_context)
        except:
            return False
        return True

    def execute(self, node_context):
        partition_with_predicate(node_context)


class PartitionADAFsPredicate(synode.Node):
    """Partition a list of ADAFs using a predicate."""

    name = "Partition ADAFs Predicate"
    nodeid = "org.sysess.sympathy.list.partitionadafspredicate"
    description = "Partition a list using configured item based predicate."
    icon = "partition_list.svg"
    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.ADAFs('Input data ADAFs', name="in")])
    outputs = Ports(
        [Port.ADAFs(
            'Output data ADAFs where predicate returns True', name="true"),
         Port.ADAFs(
             'Output data ADAFs where predicate returns True', name="false")])

    parameters = synode.parameters()

    parameters.set_string(
        'predicate',
        label='Predicate partition function',
        value='lambda x: True  # Identity partition',
        description='Partition function')

    def verify_parameters(self, node_context):
        try:
            predicate_function(node_context)
        except:
            return False
        return True

    def execute(self, node_context):
        partition_with_predicate(node_context)


class FilterListPredicate(synode.Node):
    """Filter a list of ADAFs using a predicate."""

    name = 'Filter List Predicate'
    nodeid = 'org.sysess.sympathy.list.filterlistpredicate'
    description = 'Filter a list using configured item based predicate.'
    icon = 'filter_list.svg'
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2015 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.List)

    inputs = Ports([
        Port.Custom('[<a>]', 'List', name='list')])

    outputs = Ports([
        Port.Table('Index', name='index'),
        Port.Custom('[<a>]', 'List', name='list')])

    parameters = synode.parameters()
    parameters.set_string(
        'predicate',
        label='Predicate filter function',
        value='lambda x: True  # Identity filter',
        description='Filter function')

    def verify_parameters(self, node_context):
        try:
            predicate_function(node_context)
        except:
            return False
        return True

    def execute(self, node_context):
        infiles = node_context.input['list']
        outfiles = node_context.output['list']
        index = node_context.output['index']
        predicate_fn = predicate_function(node_context)

        index_data = []
        for infile in infiles:
            if predicate_fn(infile):
                outfiles.append(infile)
                index_data.append(True)
            else:
                index_data.append(False)

        index.set_column_from_array('filter', np.array(index_data))


class PartitionListPredicate(synode.Node):
    """Partition a list using a predicate."""

    name = 'Partition List Predicate'
    nodeid = 'org.sysess.sympathy.list.partitionlistpredicate'
    description = 'Partition a list using configured item based predicate.'
    icon = 'partition_list.svg'
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2015 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.List)

    inputs = Ports([
        Port.Custom('[<a>]', 'List', name='list')])

    outputs = Ports([
        Port.Custom('[<a>]', 'List of items where predicate returned true',
                    name='list_true'),
        Port.Custom('[<a>]', 'List of items where predicate returned false',
                    name='list_false')])

    parameters = synode.parameters()

    parameters.set_string(
        'predicate',
        label='Predicate partition function',
        value='lambda x: True  # Identity partition',
        description='Partition function')

    def verify_parameters(self, node_context):
        try:
            predicate_function(node_context)
        except:
            return False
        return True

    def execute(self, node_context):
        infiles = node_context.input['list']
        truefiles = node_context.output['list_true']
        falsefiles = node_context.output['list_false']
        predicate_fn = predicate_function(node_context)

        for infile in infiles:
            if predicate_fn(infile):
                truefiles.append(infile)
            else:
                falsefiles.append(infile)


class EitherWithDataPredicate(synode.Node):
    """Either using data and a predicate."""

    name = 'Either with Data Predicate'
    nodeid = 'org.sysess.sympathy.list.eitherwithdatapredicate'
    description = 'Either of inputs using predicate and data to compare.'
    icon = 'partition_list.svg'
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2015 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.Select)
    icon = 'either.svg'

    inputs = Ports([
        Port.Custom('<a>', 'First, returned if predicate held true',
                    name='true'),
        Port.Custom('<a>', 'Second, returned if predicate did not hold true',
                    name='false'),
        Port.Custom('<b>', 'Data for the predicate comparison',
                    name='data')])

    outputs = Ports([Port.Custom(
        '<a>',
        'Output, First if the predicate holds true otherwise Second',
        name='output')])
    parameters = synode.parameters()

    parameters.set_string(
        'predicate',
        label='Either predicate function',
        value='lambda x: True  # Identity partition',
        description='Either predicate function')

    def verify_parameters(self, node_context):
        try:
            predicate_function(node_context)
        except:
            return False
        return True

    def execute(self, node_context):
        truefile = node_context.input['true']
        falsefile = node_context.input['false']
        datafile = node_context.input['data']
        outputfile = node_context.output['output']
        predicate_fn = predicate_function(node_context)

        if predicate_fn(datafile):
            outputfile.source(truefile)
        else:
            outputfile.source(falsefile)
