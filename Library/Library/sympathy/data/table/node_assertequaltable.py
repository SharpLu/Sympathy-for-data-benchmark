# -*- coding: utf-8 -*-
import numpy as np

from sympathy.api import node
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyDataError


class AssertEqualTable(node.Node):
    """Compare two incoming tables and raise an error if they differ."""

    name = 'Assert Equal Table'
    author = u'Magnus Sandén <magnus.sanden@combine.se>'
    copyright = 'Copyright (c) 2016 System Engineering Software Society'
    version = '1.0'
    icon = ''
    description = ''
    nodeid = 'org.sysess.sympathy.data.table.assertequaltable'
    tags = Tags(Tag.Development.Test)

    inputs = Ports([
        Port.Table('Table A', name='table1'),
        Port.Table('Table B', name='table2')])
    outputs = Ports([
        Port.Table('Output Table', name='out')])

    parameters = node.parameters()
    parameters.set_boolean(
        'col_order', value=True, label='Compare column order')
    parameters.set_boolean(
        'col_attrs', value=True, label='Compare column attributes')
    parameters.set_boolean(
        'tbl_names', value=True, label='Compare table names')
    parameters.set_boolean(
        'tbl_attrs', value=True, label='Compare table attributes')

    def execute(self, node_context):
        parameters = node_context.parameters
        table1 = node_context.input['table1']
        table2 = node_context.input['table2']
        out_table = node_context.output['out']

        # Column names/order
        t1_cols = set(table1.column_names())
        t2_cols = set(table2.column_names())
        if t1_cols != t2_cols:
            only_in_a = t1_cols - t2_cols
            if only_in_a:
                raise SyDataError(
                    "Tables are not equal. Some columns only exists in "
                    "table A: {}".format(list(only_in_a)))
            only_in_b = t2_cols - t1_cols
            if only_in_b:
                raise SyDataError(
                    "Tables are not equal. Some columns only exists in "
                    "table B: {}".format(list(only_in_b)))

            # Should never happen.
            raise SyDataError(
                'Tables are not equal. Different column names.')
        if parameters['col_order'].value:
            if table1.column_names() != table2.column_names():
                raise SyDataError(
                    'Tables are not equal. Different column order.')

        # Column data/attributes
        if table1.number_of_rows() != table2.number_of_rows():
            raise SyDataError(
                "Tables are not equal. Different number of rows.")
        for col_name in table1.column_names():
            diff = (table1.get_column_to_array(col_name) !=
                    table2.get_column_to_array(col_name))
            if diff.any():
                raise SyDataError(
                    "Tables are not equal. "
                    "Different values in column '{}' "
                    "(first difference at row {}).".format(
                        col_name, np.flatnonzero(diff)))
            if parameters['col_attrs'].value:
                if (table1.get_column_attributes(col_name) !=
                        table2.get_column_attributes(col_name)):
                    raise SyDataError(
                        "Tables are not equal. Different "
                        "attributes for column '{}'.".format(col_name))

        # Table name/attributes
        if parameters['tbl_names'].value:
            if table1.name != table2.name:
                raise SyDataError(
                    'Tables are not equal. Different table names.')
        if parameters['tbl_attrs'].value:
            if (dict(table1.get_table_attributes()) !=
                    dict(table2.get_table_attributes())):
                raise SyDataError(
                    'Tables are not equal. Different table attributes.')

        # Could use either one. They are equal after all.
        out_table.source(table1)
