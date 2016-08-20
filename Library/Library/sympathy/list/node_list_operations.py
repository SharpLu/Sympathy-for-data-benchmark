# -*- coding: utf-8 -*-
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
The considered category of nodes includes a number of common list operations,
    - Append
    - Extend
    - Get item

These list operations exist for list of ADAFs, Tables, and Text.
"""
from sympathy.api import node as synode
from sympathy.api import adaf, table
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import NoDataError, SyDataError
import itertools
from sympathy.api.exceptions import sywarn
from sylib import sort as sort_util


def deprecationwarn():
    sywarn(
        "This node is being deprecated in an upcoming release of Sympathy. "
        "Use Pad Table/Tables/ADAF/ADAFs instead.")


def index_adjust_parameters(node_context):
    input_list = node_context.input['port1']
    if input_list.is_valid():
        node_context.parameters['combo'].list = (
            [unicode(item) for item in range(len(input_list))])
    else:
        node_context.parameters['combo'].list = (
            node_context.parameters['combo'].value_names)
    return node_context


def index_execute(node_context):
    index = node_context.parameters['combo'].value[0]
    input_list = node_context.input['port1']
    output_element = node_context.output['port3']
    try:
        output_element.source(input_list[index])
    except IndexError:
        raise SyDataError(
            "Input list too short. Item {} doesn't exist.".format(index))


def append_execute(node_context):
    input_element = node_context.input['port1']
    input_list = node_context.input['port2']
    output_list = node_context.output['port3']
    output_list.extend(input_list)
    output_list.append(input_element)


def extend_execute(node_context):
    input_list1 = node_context.input['port1']
    input_list2 = node_context.input['port2']
    output_list = node_context.output['port3']
    output_list.extend(input_list1)
    output_list.extend(input_list2)


def extend(list1, list2):
    for elem in list2:
        list1.append(elem)


def match_length(node_context, fill_data):
    input_list1 = node_context.input['guide']
    input_list2 = node_context.input['input']
    output_list = node_context.output['output']
    parameter_root = synode.parameters(node_context.parameters)

    len1 = len(input_list1)
    len2 = len(input_list2)

    fill = parameter_root['fill'].selected

    if fill == 'Last value' and len2:
        fill_data = input_list2[len2 - 1]

    if len1 >= len2:
        extend(output_list, input_list2)
        extend(output_list, itertools.repeat(fill_data, len1 - len2))
    else:
        extend(output_list, itertools.islice(input_list2, len1))


class SuperNode(object):
    author = "Alexander Busck <alexander.busck@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)


class Index(SuperNode):
    description = 'Get an item from a list'
    parameters = synode.parameters()
    parameters.set_list(
        'combo', ['0'], label="Index", value=[0],
        description='List indexes.',
        editor=synode.Util.combo_editor().value())


class ADAFNode(SuperNode):
    outputs = Ports([Port.ADAFs('Output ADAFs', name='port3')])


class TableNode(SuperNode):
    outputs = Ports([Port.Tables('Output Tables', name='port3')])


class TextNode(SuperNode):
    outputs = Ports([Port.Texts('Output Texts', name='port3')])


class AppendADAF(ADAFNode, synode.Node):
    """
    Append ADAF to a list of ADAFs.

    :Inputs:
        **First** : ADAF
            ADAF to be appended to the list on the lower port.
        **Second** : ADAFs
            List of ADAFs that the ADAF on the upper port to be appended to.
    :Outputs:
        **Output** : ADAFs
            List of ADAFs that includes all incoming ADAFs. The ADAF
            on the upper port is located as the last element of the list.
    :Opposite node:
    :Ref. nodes: :ref:`Extend ADAF`
    """

    name = 'Append ADAF'
    description = 'Append to a list'
    icon = 'list_append.svg'
    nodeid = 'org.sysess.sympathy.list.appendadaf'
    inputs = Ports([
        Port.ADAF('ADAF to be appended', name='port1'),
        Port.ADAFs('Appended ADAFs', name='port2')])

    def execute(self, node_context):
        append_execute(node_context)


class ExtendADAF(ADAFNode, synode.Node):
    """
    Extend a list of ADAFs with another list of ADAFs.

    :Inputs:
        **First** : ADAFs
            List of ADAFs that the list on the lower port to be extended to.
        **Second** : ADAFs
            List of ADAFs to be extended to the list on the upper port.
    :Outputs:
        **Output** : ADAFs
            List of ADAFs that includes all incoming ADAFs. The ADAFs in
            the list on the lower port will be located after the ADAFs coming
            in through the upper port.
    :Opposite node:
    :Ref. nodes: :ref:`Append ADAF`
    """

    name = 'Extend ADAF'
    description = 'Extend a list'
    nodeid = 'org.sysess.sympathy.list.extendadaf'
    icon = 'list_extend.svg'
    inputs = Ports([
        Port.ADAFs('The ADAFs that will be added to', name='port1'),
        Port.ADAFs('The ADAFs that will be added', name='port2')])

    def execute(self, node_context):
        extend_execute(node_context)


class GetItemADAF(Index, synode.Node):
    """
    Get one ADAF in list of ADAFs. The ADAF is selected by index in the list.

    :Inputs:
        **List** : ADAFs
            Incoming list of ADAFs.
    :Outputs:
        **Item** : ADAF
            The ADAF at the selected index of the incoming list.
    :Configuration:
        **Index**
            Select index in the incoming list to extract the outgoing ADAF
            from.
    :Opposite node: :ref:`ADAF to ADAFs`
    :Ref. nodes:
    """

    name = 'Get Item ADAF'
    nodeid = "org.sysess.sympathy.list.getitemadaf"
    icon = 'list_get_item.svg'
    inputs = Ports([Port.ADAFs('Input ADAFs', name='port1')])
    outputs = Ports([Port.ADAF('Output selected ADAF', name='port3')])

    def adjust_parameters(self, node_context):
        return index_adjust_parameters(node_context)

    def execute(self, node_context):
        index_execute(node_context)


class PadADAF(ADAFNode, synode.Node):
    """
    Pad a list of ADAFs to match another list.

    :Inputs:
        **Template** : ADAF
            Template list.
        **Input** : ADAFs
            List to be padded.
    :Outputs:
        **Output** : ADAFs
            List of ADAFs that includes all incoming ADAFs. The ADAF
            on the upper port is located as the last element of the list.
    :Opposite node:
    :Ref. nodes: :ref:`Extend ADAF`
    """

    name = 'Pad ADAF'
    description = 'Pad a list of ADAFs to match the length of another'
    nodeid = 'org.sysess.sympathy.list.padadaf'
    inputs = Ports([
        Port.ADAFs('ADAFs with deciding length', name='port1'),
        Port.ADAFs('ADAFs which will be padded', name='port2')])

    parameters = synode.parameters()
    parameters.set_list(
        'strategy', label="Pad values", value=[0],
        description='Specify strategy to use when padding.',
        plist=['Empty ADAF', 'Repeat last ADAF'],
        editor=synode.Util.combo_editor().value())

    def execute(self, node_context):
        template = node_context.input['port1']
        inputs = node_context.input['port2']
        outputs = node_context.output['port3']

        if node_context.parameters['strategy'].value[0] == 1:
            fv = inputs[-1]
        else:
            fv = adaf.File()

        for idx, (inp, templ) in enumerate(itertools.izip_longest(
                inputs, template, fillvalue=fv)):
            outputs.append(inp)


class PadADAFUsingTable(ADAFNode, synode.Node):
    """
    Pad a list of ADAFs to match another list.

    :Inputs:
        **Template** : ADAF
            Template list.
        **Input** : ADAFs
            List to be padded.
    :Outputs:
        **Output** : ADAFs
            List of ADAFs that includes all incoming ADAFs. The ADAF
            on the upper port is located as the last element of the list.
    :Opposite node:
    :Ref. nodes: :ref:`Extend ADAF`
    """

    name = 'Pad ADAF using Tables'
    description = 'Pad one list of ADAFs to match the length of another'
    nodeid = 'org.sysess.sympathy.list.padadafusingtable'
    inputs = Ports([
        Port.Tables('Tables with deciding length', name='port1'),
        Port.ADAFs('ADAFs which will be padded', name='port2')])

    parameters = synode.parameters()
    parameters.set_list(
        'strategy', label="Pad values", value=[0],
        description='Specify strategy to use when padding.',
        plist=['Empty ADAF', 'Repeat last ADAF'],
        editor=synode.Util.combo_editor().value())

    def execute(self, node_context):
        template = node_context.input['port1']
        inputs = node_context.input['port2']
        outputs = node_context.output['port3']

        if node_context.parameters['strategy'].value[0] == 1:
            fv = inputs[-1]
        else:
            fv = adaf.File()

        for idx, (inp, templ) in enumerate(itertools.izip_longest(
                inputs, template, fillvalue=fv)):
            outputs.append(inp)


class PadTable(TableNode, synode.Node):
    """
    Pad a list of Tables to match another list.

    :Inputs:
        **Template** : ADAF
            Template list.
        **Input** : ADAFs
            List to be padded.
    :Outputs:
        **Output** : ADAFs
            List of ADAFs that includes all incoming ADAFs. The ADAF
            on the upper port is located as the last element of the list.
    :Opposite node:
    :Ref. nodes: :ref:`Extend Table`
    """

    name = 'Pad Table'
    description = 'Pad a list of Tables to match the length of another'
    nodeid = 'org.sysess.sympathy.list.padtable'
    inputs = Ports([
        Port.Tables('Tables with deciding length', name='port1'),
        Port.Tables('Tables which will be padded', name='port2')])

    parameters = synode.parameters()
    parameters.set_list(
        'strategy', label="Pad values", value=[0],
        description='Specify strategy to use when padding.',
        plist=['Empty Table', 'Repeat last Table'],
        editor=synode.Util.combo_editor().value())

    def execute(self, node_context):
        template = node_context.input['port1']
        inputs = node_context.input['port2']
        outputs = node_context.output['port3']

        if node_context.parameters['strategy'].value[0] == 1:
            fv = inputs[-1]
        else:
            fv = table.File()

        for idx, (inp, templ) in enumerate(itertools.izip_longest(
                inputs, template, fillvalue=fv)):
            outputs.append(inp)


class PadTableUsingADAF(TableNode, synode.Node):
    """
    Pad a list of Tables to match another list.

    :Inputs:
        **Template** : ADAF
            Template list.
        **Input** : ADAFs
            List to be padded.
    :Outputs:
        **Output** : ADAFs
            List of ADAFs that includes all incoming Tables. The Table
            on the upper port is located as the last element of the list.
    :Opposite node:
    :Ref. nodes: :ref:`Extend Table`
    """

    name = 'Pad Table Using ADAFs'
    description = 'Pad a list of Tables to match the length of another'
    nodeid = 'org.sysess.sympathy.list.padtableusingadaf'
    inputs = Ports([
        Port.ADAFs('ADAFs with deciding length', name='port1'),
        Port.Tables('Tables which will be padded', name='port2')])

    parameters = synode.parameters()
    parameters.set_list(
        'strategy', label="Pad values", value=[0],
        description='Specify strategy to use when padding.',
        plist=['Empty Table', 'Repeat last Table'],
        editor=synode.Util.combo_editor().value())

    def execute(self, node_context):
        template = node_context.input['port1']
        inputs = node_context.input['port2']
        outputs = node_context.output['port3']

        if node_context.parameters['strategy'].value[0] == 1:
            fv = inputs[-1]
        else:
            fv = table.File()

        for idx, (inp, templ) in enumerate(itertools.izip_longest(
                inputs, template, fillvalue=fv)):
            outputs.append(inp)


class AppendTable(TableNode, synode.Node):
    """
    Append Table to a list of Tables.

    :Inputs:
        **First** : Table
            Table to be appended to the list on the lower port.
        **Second** : Tables
            List of Tables that the Table on the upper port to be appended to.
    :Outputs:
        **Output** : Tables
            List of Tables that includes all incoming Tables. The Table
            on the upper port is located as the last element of the list.
    :Opposite node:
    :Ref. nodes: :ref:`Extend Table`
    """

    name = 'Append Table'
    description = 'Append to a list'
    icon = 'list_append.svg'
    nodeid = 'org.sysess.sympathy.list.appendtable'
    inputs = Ports([
        Port.Table('Table to be appended', name='port1'),
        Port.Tables('Appended Tables', name='port2')])

    def execute(self, node_context):
        append_execute(node_context)


class ExtendTable(TableNode, synode.Node):
    """
    Extend a list of Tables with another list of Tables.

    :Inputs:
        **First** : Tables
            List of Tables that the list on the lower port to be extended to.
        **Second** : Tables
            List of ADAFs to be extended to the list on the upper port.
    :Outputs:
        **Output** : Tables
            List of Tables that includes all incoming Tables. The Tables in
            the list on the lower port will be located after the Tables coming
            in through the upper port.
    :Opposite node:
    :Ref. nodes: :ref:`Append Table`
    """

    name = 'Extend Table'
    description = 'Extend a list'
    nodeid = 'org.sysess.sympathy.list.extendtable'
    icon = 'list_extend.svg'
    inputs = Ports([
        Port.Tables('The Tables that will be added to', name='port1'),
        Port.Tables('The Tables that will be added', name='port2')])

    def execute(self, node_context):
        extend_execute(node_context)


class GetItemTable(Index, synode.Node):
    """
    Get one Table in list of Tables. The Table is selected by index in the
    list.

    :Inputs:
        **List** : Tables
            Incoming list of Tables.
    :Outputs:
        **Item** : Table
            The Table at the selected index of the incoming list.
    :Configuration:
        **Index**
            Select index in the incoming list to extract the outgoing Table
            from.
    :Opposite node: :ref:`Table to Tables`
    :Ref. nodes:
    """

    name = 'Get Item Table'
    nodeid = "org.sysess.sympathy.list.getitemtable"
    icon = 'list_get_item.svg'
    inputs = Ports([Port.Tables('Input Tables', name='port1')])
    outputs = Ports([Port.Table('Output selected Table', name='port3')])

    def adjust_parameters(self, node_context):
        input_list = node_context.input['port1']
        if input_list.is_valid():
            node_context.parameters['combo'].list = (
                [u'{index}\t{name}'.format(
                    index=i, name=(item.get_name() or ''))
                 for i, item in enumerate(input_list)])
        else:
            node_context.parameters['combo'].list = (
                node_context.parameters['combo'].value_names)
        return node_context

    def execute(self, node_context):
        index_execute(node_context)


class AppendText(TextNode, synode.Node):
    """
    Append Text to a list of Texts.

    :Inputs:
        **First** : Text
            Text to be appended to the list on the lower port.
        **Second** : Texts
            List of Texts that the Text on the upper port to be appended to.
    :Outputs:
        **Output** : Texts
            List of Texts that includes all incoming Texts. The Text
            on the upper port is located as the last element of the list.
    :Opposite node:
    :Ref. nodes: :ref:`Extend Text`
    """

    name = 'Append Text'
    description = 'Append to a list'
    icon = 'list_append.svg'
    nodeid = 'org.sysess.sympathy.list.appendtext'
    inputs = Ports([
        Port.Text('Text to be appended', name='port1'),
        Port.Texts('Appended Texts', name='port2')])

    def execute(self, node_context):
        append_execute(node_context)


class ExtendText(TextNode, synode.Node):
    """
    Extend a list of Texts with another list of Texts.

    :Inputs:
        **First** : Texts
            List of Texts that the list on the lower port to be extended to.
        **Second** : Texts
            List of ADAFs to be extended to the list on the upper port.
    :Outputs:
        **Output** : Texts
            List of Texts that includes all incoming Texts. The Texts in
            the list on the lower port will be located after the Texts coming
            in through the upper port.
    :Opposite node:
    :Ref. nodes: :ref:`Append Text`
    """

    name = 'Extend Text'
    description = 'Extend a list'
    nodeid = 'org.sysess.sympathy.list.extendtext'
    icon = 'list_extend.svg'
    inputs = Ports([
        Port.Texts('The Texts that will be added to', name='port1'),
        Port.Texts('The Texts that will be added', name='port2')])

    def execute(self, node_context):
        extend_execute(node_context)


class GetItemText(Index, synode.Node):
    """
    Get one Text in list of Texts. The Text is selected by index in the
    list.

    :Inputs:
        **List** : Texts
            Incoming list of Texts.
    :Outputs:
        **Item** : Text
            The Text at the selected index of the incoming list.
    :Configuration:
        **Index**
            Select index in the incoming list to extract the outgoing Text
            from.
    :Opposite node: :ref:`Text to Texts`
    :Ref. nodes:
    """

    name = 'Get Item Text'
    nodeid = "org.sysess.sympathy.list.getitemtext"
    icon = 'list_get_item.svg'
    inputs = Ports([Port.Texts('Input Texts', name='port1')])
    outputs = Ports([Port.Text('Output selected Text', name='port3')])

    def adjust_parameters(self, node_context):
        input_list = node_context.input['port1']
        if input_list.is_valid():
            node_context.parameters['combo'].list = (
                [u'{index}'.format(index=i)
                 for i, item in enumerate(input_list)])
        else:
            node_context.parameters['combo'].list = (
                node_context.parameters['combo'].value_names)
        return node_context

    def execute(self, node_context):
        index_execute(node_context)


class SuperNodeGeneric(synode.Node):
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2015 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.DataProcessing.List)


class AppendList(SuperNodeGeneric):
    """Create a list with the items from list (input) followed by item."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Append List'
    nodeid = 'org.sysess.sympathy.list.appendlist'
    icon = 'append_list.svg'

    inputs = Ports([
        Port.Custom('<a>', 'The Item to be appended', name='item'),
        Port.Custom('[<a>]', 'Appended List', name='list')])
    outputs = Ports([
        Port.Custom('[<a>]', 'Appended List', name='list')])

    def execute(self, node_context):
        result = node_context.output['list']
        result.extend(node_context.input['list'])
        result.append(node_context.input['item'])


class ItemToList(SuperNodeGeneric):
    """Create a single item list containing item."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Item to List'
    nodeid = 'org.sysess.sympathy.list.itemtolist'
    icon = 'item_to_list.svg'

    inputs = Ports([
        Port.Custom('<a>', 'Input Item', name='item')])
    outputs = Ports([
        Port.Custom('[<a>]', 'Item as List', name='list')])

    def execute(self, node_context):
        result = node_context.output['list']
        result.append(node_context.input['item'])


class GetItemList(SuperNodeGeneric):
    """Get one item in list by index."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Get Item List'
    nodeid = "org.sysess.sympathy.list.getitemlist"
    inputs = Ports(
        [Port.Custom('[<a>]', 'Input List', name='list')])
    outputs = Ports(
        [Port.Custom('<a>', 'Output selcted Item from List', name='item')])
    icon = 'get_item_list.svg'

    parameters = synode.parameters()
    parameters.set_list(
        'index', ['0'], label='Index', value=[0],
        description='Choose item index in list.',
        editor=synode.Util.combo_editor().value())

    def adjust_parameters(self, node_context):
        input_list = node_context.input['list']

        try:
            indices = [unicode(item) for item in range(len(input_list))]
        except NoDataError:
            indices = node_context.parameters['index'].value_names

        node_context.parameters['index'].list = indices
        return node_context

    def execute(self, node_context):
        index = node_context.parameters['index'].value[0]
        node_context.output['item'].source(node_context.input['list'][index])


class PadList(SuperNodeGeneric):
    """Pad a list to match another list."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Pad List'
    description = 'Pad a list to match the length of template'
    nodeid = 'org.sysess.sympathy.list.padlist'
    inputs = Ports(
        [Port.Custom('[<a>]', 'List with deciding length', name='template'),
         Port.Custom('[<a>]', 'List that will be padded', name='list')])
    outputs = Ports(
        [Port.Custom('[<a>]', 'Padded List', name='list')])
    icon = 'pad_list.svg'

    parameters = synode.parameters()
    parameters.set_list(
        'strategy', label='Pad values', value=[0],
        description='Specify strategy to use when padding.',
        plist=['Repeat last item', 'Empty item'],
        editor=synode.Util.combo_editor().value())

    def execute(self, node_context):
        template = node_context.input['template']
        input_ = node_context.input['list']
        output = node_context.output['list']

        if node_context.parameters['strategy'].value[0] == 0:
            fv = input_[-1]
        else:
            fv = output.create()

        for idx, (inp, templ) in enumerate(itertools.izip_longest(
                input_, template, fillvalue=fv)):
            output.append(inp)


class PadListItem(SuperNodeGeneric):
    """Pad a list with item to match another list."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Pad List with Item'
    description = 'Pad a list with item match the length of template'
    nodeid = 'org.sysess.sympathy.list.padlistitem'
    inputs = Ports(
        [Port.Custom('[<a>]', 'List with deciding length', name='template'),
         Port.Custom('<b>', 'Item to be used as padding', name='item'),
         Port.Custom('[<b>]', 'List that will be padded', name='list')])
    outputs = Ports(
        [Port.Custom('[<b>]', 'The padded List', name='list')])
    icon = 'pad_list.svg'

    def execute(self, node_context):
        template = node_context.input['template']
        item = node_context.input['item']
        input_ = node_context.input['list']
        output = node_context.output['list']

        for idx, (inp, templ) in enumerate(itertools.izip_longest(
                input_, template, fillvalue=item)):
            output.append(inp)


class Propagate(SuperNodeGeneric):
    """
    Propagate input to output.

    This node is mostly useful for testing purposes.
    """

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Propagate Input'
    description = 'Propagate input to output'
    nodeid = 'org.sysess.sympathy.generic.propagate'
    icon = 'propagate.svg'
    inputs = Ports([
        Port.Custom('<a>', 'Input Item', name='item')])

    outputs = Ports(
        [Port.Custom('<a>', 'The input Item', name='item')])

    def execute(self, node_context):
        node_context.output['item'].source(node_context.input['item'])


class PropagateFirst(SuperNodeGeneric):
    """
    Propagate first input to output.

    This node is mostly useful for testing purposes.
    It can also be used to force a specific execution
    order.
    """

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Propagate First Input'
    description = 'Propagate first input to output'
    nodeid = 'org.sysess.sympathy.generic.propagatefirst'
    icon = 'propagate_first.svg'
    inputs = Ports([
        Port.Custom('<a>', 'The Item to be propagated', name='item1'),
        Port.Custom('<b>', 'Item that will not be propagated', name='item2')])

    outputs = Ports(
        [Port.Custom('<a>', 'Propagated Item', name='item')])

    def execute(self, node_context):
        node_context.output['item'].source(node_context.input['item1'])


class PropagateFirstSame(SuperNodeGeneric):
    """
    Propagate first input to output.

    This node is mostly useful for testing purposes.
    It can also be used to force a specific execution
    order and to enforce a specific type.
    """

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Propagate First Input (Same Type)'
    description = 'Propagate first input to output'
    nodeid = 'org.sysess.sympathy.generic.propagatefirstsame'
    icon = 'propagate_first.svg'
    inputs = Ports([
        Port.Custom('<a>', 'The Item to be propagated', name='item1'),
        Port.Custom('<a>', 'Item that will not be propagated', name='item2')])

    outputs = Ports(
        [Port.Custom('<a>', 'Propagated Item', name='item')])

    def execute(self, node_context):
        node_context.output['item'].source(node_context.input['item1'])


class ExtendList(SuperNodeGeneric):
    """Extend a list with another list."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Extend List'
    description = 'Extend a list'
    nodeid = 'org.sysess.sympathy.list.extendlist'
    icon = 'extend_list.svg'
    inputs = Ports([
        Port.Custom('[<a>]', 'The List that will be added to', name='list1'),
        Port.Custom('[<a>]', 'The List that will be added', name='list2')])

    outputs = Ports(
        [Port.Custom('[<a>]', 'The extended List', name='list')])

    def execute(self, node_context):
        input_list1 = node_context.input['list1']
        input_list2 = node_context.input['list2']
        output_list = node_context.output['list']
        output_list.extend(input_list1)
        output_list.extend(input_list2)


class FlattenList(SuperNodeGeneric):
    """Flatten a nested list."""

    author = 'Magnus Sandén <magnus.sanden@combine.se>'
    name = 'Flatten List'
    description = 'Flatten a nested list'
    nodeid = 'org.sysess.sympathy.list.flattenlist'
    icon = 'flatten_list.svg'
    inputs = Ports([
        Port.Custom('[[<a>]]', 'Nested List', name='in')])

    outputs = Ports(
        [Port.Custom('[<a>]', 'Flattened List', name='out')])

    def execute(self, node_context):
        input_list = node_context.input['in']
        output_list = node_context.output['out']
        for inner_list in input_list:
            output_list.extend(inner_list)


class Repeat(SuperNodeGeneric):
    """Repeat item creating list of item."""

    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    name = 'Repeat Item to List'
    description = 'Repeat item n times creating list of items'
    nodeid = 'org.sysess.sympathy.list.repeatlistitem'
    icon = 'repeat_item_to_list.svg'

    parameters = synode.parameters()
    parameters.set_integer(
        'n', label='Number of times', value=0,
        description='Choose number of times to repeat item.')

    inputs = Ports([
        Port.Custom('<a>', 'Input Item', name='item')])

    outputs = Ports(
        [Port.Custom('[<a>]', 'List containing repeated Items', name='list')])

    def execute(self, node_context):
        item = node_context.input['item']
        output_list = node_context.output['list']

        for _ in range(node_context.parameters['n'].value):
            output_list.append(item)


class MatchTablesList(synode.Node):
    """Match a list of Tables lengths."""

    name = "Match Tables list lengths (deprecated)"
    nodeid = "org.sysess.sympathy.list.matchtableslist"
    description = "Match a list length using guide list."
    icon = "match_list.svg"
    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.Tables('Guide list', name='guide'),
                    Port.Tables('Input list', name='input')])
    outputs = Ports([Port.Tables('Output list', name='output')])

    parameters = synode.parameters()

    parameters.set_list(
        'fill', value=[0], label='Extend values',
        desciption=(
            'Specify the values to use if the input has to be extended.'),
        plist=['Empty element', 'Last value'],
        editor=synode.Util.combo_editor().value())

    def execute(self, node_context):
        deprecationwarn()
        match_length(node_context, table.File())


class MatchADAFsList(synode.Node):
    """Match a list of ADAFs lengths."""

    name = "Match ADAFs list lengths (deprecated)"
    nodeid = "org.sysess.sympathy.list.matchadafslist"
    description = "Match a list length using guide list."
    icon = "match_list.svg"
    author = "Erik der Hagopian <erik.hagopian@sysess.org>"
    copyright = "(C) 2013 System Engineering Software Society"
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)

    inputs = Ports([Port.ADAFs('Guide list', name='guide'),
                    Port.ADAFs('Input list', name='input')])
    outputs = Ports([Port.ADAFs('Output list', name='output')])

    parameters = synode.parameters()

    parameters.set_list(
        'fill', value=[0], label='Extend values',
        desciption=(
            'Specify the values to use if the input has to be extended.'),
        plist=['Empty element', 'Last value'],
        editor=synode.Util.combo_editor().value())

    def execute(self, node_context):
        deprecationwarn()
        match_length(node_context, adaf.File())


class SortList(synode.Node):
    """
    Sort List of items using a Python key function that determines order.
    For details about how to write the key function see: `Key functions
    <https://docs.python.org/2/howto/sorting.html#key-functions>`_.
    """

    name = 'Sort List'
    description = 'Sort List using a key function.'
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2015 System Engineering Software Society'
    nodeid = 'org.sysess.sympathy.list.sortlist'
    icon = 'sort_list.svg'
    version = '1.0'
    parameters = synode.parameters()
    parameters.set_string(
        'sort_function',
        description='Python key function that determines order.',
        value='lambda item: item  # Arbitrary key example.')

    parameters.set_boolean(
        'reverse',
        label='Reverse order',
        description='Use descending (reverse) order.',
        value=False)

    tags = Tags(Tag.DataProcessing.List)

    inputs = Ports([
        Port.Custom('[<a>]', 'List to be sorted', name='list')])
    outputs = Ports([
        Port.Custom('[<a>]', 'Sorted List', name='list')])

    tags = Tags(Tag.DataProcessing.List)

    def exec_parameter_view(self, node_context):
        return sort_util.SortWidget(node_context.input['list'],
                                    node_context)

    def execute(self, node_context):
        output_list = node_context.output['list']
        for item in sort_util.sorted_list(
                node_context.parameters['sort_function'].value,
                node_context.input['list'],
                reverse=node_context.parameters['reverse'].value):
            output_list.append(item)
