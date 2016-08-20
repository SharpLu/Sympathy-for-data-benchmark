from sympathy.api import node
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
import numpy as np


def hold_column(array):
    it = iter(np.where(np.isnan(array))[0])

    try:
        i = it.next()
    except StopIteration:
        return array

    # Local copy for in-place edit.
    array = np.array(array)

    if i != 0:
        array[i] = array[i - 1]

    for i in it:
        array[i] = array[i - 1]
    return array


def hold_table(in_table, out_table):
    for cname in in_table.column_names():
        out_table.set_column_from_array(
            cname, hold_column(in_table.get_column_to_array(cname)))
    out_table.set_attributes(in_table.get_attributes())


class HoldValueBase(node.Node):
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2015 System Engineering Software Society'
    version = '1.0'
    icon = ''
    tags = Tags(Tag.DataProcessing.TransformData)
    description = (
        'Replace occurences of nan in cells by the last non-nan value from '
        'the same column.')


class HoldValueTable(HoldValueBase):
    """
    Replace occurences of nan in cells by the last non-nan value from the same
    column.
    """

    name = 'Hold value Table'
    nodeid = 'org.sysess.sympathy.data.table.holdvaluetable'

    inputs = Ports([
        Port.Table('Input Table')])
    outputs = Ports([
        Port.Table('Output Table with NaN replaced')])

    def execute(self, node_context):
        hold_table(node_context.input[0], node_context.output[0])


class HoldValueTables(HoldValueBase):
    """
    Replace occurences of nan in cells by the last non-nan value from the same
    column.
    """

    name = 'Hold value Tables'
    nodeid = 'org.sysess.sympathy.data.table.holdvaluetables'

    inputs = Ports([
        Port.Tables('Input Tables')])
    outputs = Ports([
        Port.Tables('Outputs Table with NaN replaced')])

    def execute(self, node_context):
        out_tables = node_context.output[0]

        for in_table in node_context.input[0]:
            out_table = out_tables.create()
            hold_table(in_table, out_table)
            out_tables.append(out_table)
