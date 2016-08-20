# Copyright (c) 2015, System Engineering Software Society
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
If you're only interested in some of the data in an ADAF (maybe for performance
reasons) you can use e.g. :ref:`Select columns in ADAF with Table`.

The Table/Tables argument shall have four columns, which must be named Type,
System, Raster, and Parameter. These columns hold the names of the
corresponding fields in the ADAF/ADAFs.
"""

from collections import OrderedDict
from sympathy.api import node, table, adaf
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags

from sympathy.api.exceptions import SyDataError


def apply_selection(in_adaf, out_adaf, meta, res, ts, compliment):
    out_adaf.set_source_id(in_adaf.source_id())

    for in_data, out_data, group in [(in_adaf.meta, out_adaf.meta, meta),
                                     (in_adaf.res, out_adaf.res, res)]:

        keys = in_data.keys()
        if compliment:
            keys = [key for key in keys if key not in group]
        else:
            keys = [key for key in keys if key in group]

        in_table = in_data.to_table()
        out_table = table.File()

        for key in keys:
            out_table.update_column(key, in_table)

        out_data.from_table(out_table)

    systems = {}

    for sysname, in_sys in in_adaf.sys.items():
        if not compliment and sysname not in ts:
            continue
        ts_sys = ts.get(sysname, {})

        for rastername, in_raster in in_sys.items():
            if not compliment and rastername not in ts_sys:
                continue
            ts_names = ts_sys.get(rastername, [])
            in_ts_names = in_raster.keys()

            if compliment:
                keys = [key for key in in_ts_names if key not in ts_names]
            else:
                keys = [key for key in in_ts_names if key in ts_names]

            if keys:
                if sysname in systems:
                    out_sys = systems[sysname]
                else:
                    out_sys = out_adaf.sys.create(sysname)
                    systems[sysname] = out_sys

                out_raster = out_sys.create(rastername)

                basis_name = '__amazing_probably_not_used_basis_name__'
                in_table = in_raster.to_table(basis_name)
                out_table = table.File()
                out_table.set_table_attributes(
                    in_table.get_table_attributes())
                out_table.set_name(in_table.get_name())

                out_table.update_column(
                    basis_name, in_table)

                for key in keys:
                    out_table.update_column(key, in_table)

                out_raster.from_table(out_table, basis_name)


def build_selection(selection):
    selection_columns = ['Type', 'System', 'Raster', 'Parameter']
    columns = selection.column_names()

    if not all([column_name in columns
                for column_name in selection_columns]):
        raise SyDataError(
            'Selection Table must have the following columns: {}\n'
            'Using ADAF structure to Table ensures it.'.format(
                ', '.join(selection_columns)))

    narrow_selection = table.File()

    for column in selection_columns:
        narrow_selection.update_column(column, selection)

    meta = []
    res = []
    syss = {}

    for typec, systemc, rasterc, parameterc in narrow_selection.to_rows():
        if typec == 'Metadata':
            meta.append(parameterc)
        elif typec == 'Result':
            res.append(parameterc)
        elif typec == 'Timeseries':
            sys = syss.setdefault(systemc, {})
            raster = sys.setdefault(rasterc, [])
            raster.append(parameterc)

    return meta, res, syss


def _set_complement_parameter(parameter_root):
    parameter_root.set_boolean(
        'complement', value=False,
        label='Remove selected columns',
        description=(
            'When enabled, the selected columns will be removed. '
            'When disabled, the non-selected columns will be '
            'removed.'))


class SelectColumnsADAFWithTable(node.Node):
    name = 'Select columns in ADAF with Table'
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(c) 2015 System Engineering Software Society'
    version = '1.0'
    icon = ''
    description = (
        'Select the columns to keep in ADAF using selection table created by '
        'ADAF structure to table')
    nodeid = 'org.sysess.sympathy.data.adaf.selectcolumnsadafwithtable'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([
        Port.Table('ADAF structure selection', name='selection'),
        Port.ADAF('ADAF data matched with selection', name='data')])
    outputs = Ports([
        Port.ADAF('ADAF data after selection', name='data')])

    parameters = OrderedDict()
    parameter_root = node.parameters(parameters)

    _set_complement_parameter(parameter_root)

    def execute(self, node_context):
        selection = node_context.input['selection']
        in_data = node_context.input['data']
        out_data = node_context.output['data']
        if in_data.is_empty() or selection.is_empty():
            return

        parameters = node.parameters(node_context.parameters)
        complement = parameters['complement'].value

        meta, res, syss = build_selection(selection)
        apply_selection(in_data, out_data, meta, res, syss, complement)


class SelectColumnsADAFsWithTable(node.Node):
    name = 'Select columns in ADAFs with Table'
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(c) 2015 System Engineering Software Society'
    version = '1.0'
    icon = ''
    description = (
        'Select the columns in ADAFs to keep using selection table created by '
        'ADAF structure to table')
    nodeid = 'org.sysess.sympathy.data.adaf.selectcolumnsadafswithtable'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([
        Port.Table('ADAF structure selection', name='selection'),
        Port.ADAFs('ADAFs data matched with selection', name='data')])
    outputs = Ports([
        Port.ADAFs('ADAFs data after selection', name='data')])

    parameters = OrderedDict()
    parameter_root = node.parameters(parameters)

    _set_complement_parameter(parameter_root)

    def execute(self, node_context):
        selection = node_context.input['selection']
        in_data = node_context.input['data']
        out_data = node_context.output['data']
        if len(in_data) == 0 or selection.is_empty():
            return

        parameters = node.parameters(node_context.parameters)
        complement = parameters['complement'].value

        meta, res, syss = build_selection(selection)
        for in_adaf in in_data:
            out_adaf = adaf.File()
            apply_selection(in_adaf, out_adaf, meta, res, syss, complement)
            out_data.append(out_adaf)


class SelectColumnsADAFsWithTables(node.Node):
    name = 'Select columns in ADAFs with Tables'
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(c) 2015 System Engineering Software Society'
    version = '1.0'
    icon = ''
    description = (
        'Select the columns in ADAFs to keep using selection table created by '
        'ADAF structure to table')
    nodeid = 'org.sysess.sympathy.data.adaf.selectcolumnsadafswithtables'
    tags = Tags(Tag.DataProcessing.Select)

    inputs = Ports([
        Port.Tables('ADAF structure selection', name='selection'),
        Port.ADAFs('ADAFs data matched with selection', name='data')])
    outputs = Ports([
        Port.ADAFs('ADAFs data after selection', name='data')])

    parameters = OrderedDict()
    parameter_root = node.parameters(parameters)

    _set_complement_parameter(parameter_root)

    def execute(self, node_context):
        selection = node_context.input['selection']
        in_data = node_context.input['data']
        out_data = node_context.output['data']

        parameters = node.parameters(node_context.parameters)
        complement = parameters['complement'].value

        assert(len(selection) == len(in_data))

        for in_adaf, in_table in zip(in_data, selection):
            out_adaf = adaf.File()
            meta, res, syss = build_selection(in_table)
            apply_selection(in_adaf, out_adaf, meta, res, syss, complement)
            out_data.append(out_adaf)
