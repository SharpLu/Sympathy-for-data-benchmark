# coding=utf-8
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
A collection of examples that illustrates a number of details that are
important in order to create nodes for Sympathy of Data. The usage of content
in this file should be combined with the Node Writing Tutorial.
"""

import time

import numpy as np

from sympathy.api import table
from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api.exceptions import SyNodeError, sywarn


class HelloWorld(synode.Node):
    """
    This example prints a customizable greeting. Default greeting is "Hello
    world!".

    :Ref. nodes: :ref:`Output Example`, :ref:`Error Example`
    """

    name = 'Hello world Example'
    description = 'Node demonstrating the basics of node creation.'
    icon = 'example.svg'
    nodeid = 'org.sysess.sympathy.examples.helloworld'
    author = 'Magnus Sandén <magnus.sanden@combine.se>'
    copyright = '(c) 2014 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.Development.Example)

    parameters = synode.parameters()
    parameters.set_string(
        'greeting', value='Hello world!', label='Greeting:',
        description='Your preferred greeting.')

    def execute(self, node_context):
        print node_context.parameters['greeting'].value


class OutputExample(synode.Node):
    """
    This example demonstrates how to write data to an outgoing Table.

    :Ref. nodes: :ref:`Hello world Example`, :ref:`Error Example`
    """

    name = 'Output example'
    description = 'Node demonstrating how to write a table.'
    icon = 'example.svg'
    nodeid = 'org.sysess.sympathy.examples.outputexample'
    author = 'Magnus Sandén <magnus.sanden@combine.se>'
    copyright = '(c) 2014 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.Development.Example)

    outputs = Ports([
        Port.Table("Table with a column named 'Enumeration' with values 1-99",
                   name='output')])

    def execute(self, node_context):
        """Execute node"""
        tablefile = node_context.output['output']
        data = np.arange(1, 101, dtype=int)
        tablefile.set_name('Output Example')
        tablefile.set_column_from_array('Enumeration', data)


class ErrorExample(synode.Node):
    """
    Demonstrates how to give the user error messages or warnings and how that
    is shown in the platform.

    :Ref. nodes: :ref:`Hello World Example`, :ref:`Output Example`
    """

    name = 'Error example'
    description = 'Node demonstrating the error handling system.'
    icon = 'example_error.svg'
    nodeid = 'org.sysess.sympathy.examples.errorexample'
    author = 'Stefan Larsson <stefan.larsson@sysess.org>'
    copyright = '(C)2011-2012,2015 System Engineering Software Society'
    version = '2.0'
    tags = Tags(Tag.Development.Example)

    parameters = synode.parameters()
    parameters.set_list(
        'severity', label='Severity:',
        description='Choose how severe the error is.',
        plist=['Output', 'Warning', 'Error', 'Exception'], value=[2],
        editor=synode.Util.combo_editor().value())
    parameters.set_string(
        'error_msg', label='Error message:',
        description='This error message will be shown when executing the node',
        value='This is an expected error.')

    def execute(self, node_context):
        parameters = node_context.parameters
        severity = parameters['severity'].selected
        error_msg = parameters['error_msg'].value
        if severity == 'Output':
            print error_msg
        elif severity == 'Warning':
            sywarn(error_msg)
        elif severity == 'Error':
            raise SyNodeError(error_msg)
        elif severity == 'Exception':
            raise Exception(error_msg)


class AllParametersExample(synode.Node):
    """
    This node includes all available configuration options for initialising
    parameters. The configuration GUI is automatically generated by the
    platform.

    :Configuration: All types of configuration options
    :Ref. nodes: :ref:`Hello World Example`, :ref:`Output Example`
    """

    name = 'All parameters example'
    description = 'Node showing all different parameter types.'
    icon = 'example.svg'
    nodeid = 'org.sysess.sympathy.examples.allparameters'
    author = 'Alexander Busck <alexander.busck@sysess.org>'
    copyright = '(C)2011-2012,2015 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.Development.Example)

    parameters = synode.parameters()
    scalars_page = parameters.create_page('scalars', label='Scalars')
    float_group = scalars_page.create_group('float', label='Floats')
    float_group.set_float('stringfloat',
                          label='Float in a line edit',
                          description='A float',
                          value=0.1234)
    float_group.set_float('spinfloat',
                          label='Float in a spinbox',
                          description='A float',
                          value=0.1234,
                          editor=synode.Util.bounded_decimal_spinbox_editor(
                              0.0, 4.0, 0.1, 4).value())
    integer_group = scalars_page.create_group('integer', label='Integers')
    integer_group.set_integer('stringinteger',
                              label='Integer in a line edit',
                              description='An integer',
                              value=1234,
                              editor=synode.Util.bounded_lineedit_editor(
                                  0, 2000, placeholder='Number between 0 '
                                                       'and 2000').value())
    integer_group.set_integer('spininteger',
                              label='Integer in a spinbox',
                              description='An integer',
                              value=1234,
                              editor=synode.Util.bounded_spinbox_editor(
                                  0, 2000, 10).value())

    string_page = parameters.create_page('strings', label='Strings')
    string_page.set_string('lineedit',
                           label='String in a line edit',
                           value='Hello',
                           description='Text on a single line',
                           editor=synode.Util.lineedit_editor(
                               'Hello World!').value())
    string_page.set_string('filename',
                           label='Filename',
                           description='A filename including path if needed',
                           value='test.txt',
                           editor=synode.Util.filename_editor(
                               ['Image files (*.png *.xpm *.jpg)',
                                'Text files (*.txt)',
                                'Any files (*)']).value())
    string_page.set_string('save_filename',
                           label='Save filename',
                           description='A filename including path if needed',
                           value='test.txt',
                           editor=synode.Util.savename_editor(
                               ['Image files (*.png *.xpm *.jpg)',
                                'Text files (*.txt)',
                                'Any files (*)']).value())
    string_page.set_string('directory',
                           label='Directory',
                           description='A directory including path if needed',
                           value='MyDirectory',
                           editor=synode.Util.directory_editor().value())

    logics_page = parameters.create_page('logics', label='Logics')
    logics_page.set_boolean('boolflag',
                            label='Boolean',
                            description=('A boolean flag indicating true or '
                                         'false'),
                            value=True)

    lists_page = parameters.create_page('lists', label='Lists')
    lists_page.set_list('combo',
                        label='Combo box',
                        description='A combo box',
                        value=[1],
                        plist=['First option',
                               'Second option',
                               'Third option'],
                        editor=synode.Util.combo_editor().value())
    lists_page.set_list('alist',
                        label='List view',
                        description='A list',
                        value=[2],
                        plist=['First option',
                               'Second option',
                               'Third option'],
                        editor=synode.Util.list_editor().value())
    multilist_editor = synode.Util.selectionlist_editor('multi')
    multilist_editor.set_attribute('alternatingrowcolors', False)
    lists_page.set_list('multilist',
                        label='List view with multiselect',
                        description='A list with multiselect',
                        value=[0, 2],
                        plist=['Element1', 'Element2', 'Element3'],
                        editor=multilist_editor.value())

    def adjust_parameters(self, node_context):
        """
        This method is called before configure and execute. In this example it
        fills one of the lists with alternatives and overrides the value of one
        of the integer parameters, totally disregarding whatever the user has
        set it to.
        """
        node_context.parameters['lists']['alist'].list = (
            ['My', 'Programmatically', 'Generated', 'List'])
        node_context.parameters['scalars']['integer']['spininteger'].value = 42
        return node_context

    def execute(self, node_context):
        """
        You always have to implement the execute method to be able to execute
        the node. In this node we don't want the execute method to actually do
        anything though.
        """
        pass


class ProgressExample(synode.Node):
    """
    This node runs with a delay and updates its progress during execution to
    let the user know how far it has gotten.

    :Ref. nodes: :ref:`Error Example`
    """

    name = 'Progress example'
    description = 'Node demonstrating progress usage'
    icon = 'example.svg'
    nodeid = 'org.sysess.sympathy.examples.progress'
    author = 'Magnus Sandén <magnus.sanden@combine.se>'
    copyright = '(C)2015 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.Development.Example)

    parameters = synode.parameters()
    parameters.set_float(
        'delay', value=0.02, label='Delay:',
        description='Delay between tables')

    def execute(self, node_context):
        """
        Loop with customizable delay from 0 to 99 and update the node's
        progress accordingly each iteration.
        """
        delay = node_context.parameters['delay'].value
        for i in range(100):
            self.set_progress(float(i))

            # In real applications this could be e.g. some lengthy calculation.
            time.sleep(delay)


class ControllerExample(synode.Node):
    """
    This example node demonstrates three things:

    - How to use controllers to create more advanced configuration guis, while
      still relying on the automatic configuration builder. For more
      information about controllers see :ref:`the user manual<controllers>`.
    - How to read from and write to a list of tables.
    - How to use the source method of tables and other data types to copy data
      from one file to another, making links whenever possible.

    To run it you can connect its input port to e.g. a :ref:`Random Tables`
    node.

    :Ref. nodes: :ref:`Hello World Example`
    """

    name = 'Controller example'
    description = 'Node demonstrating controller usage'
    icon = 'example.svg'
    nodeid = 'org.sysess.sympathy.examples.controller'
    author = 'Magnus Sandén <magnus.sanden@combine.se>'
    copyright = '(C)2015 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.Development.Example)

    inputs = Ports([Port.Tables('Input Tables', name='input')])
    outputs = Ports([Port.Tables('Output Tables', name='output')])

    parameters = synode.parameters()
    parameters.set_boolean(
        'every_second_table', value=True, label='Take every second table',
        description='When checked, node will copy every second table in input '
                    'list to output. If unchecked all the tables will be '
                    'copied.')
    parameters.set_list(
        'even_odd', value=[0], plist=['Even', 'Odd'],
        description='When "Take every second table" is checked this parameter '
                    'determines if the node should take even numbered tables '
                    'or odd numbered tables. When "Take every second table" '
                    'is not checked this parameter has no effect.',
        editor=synode.Util.combo_editor().value())

    controllers = synode.controller(
        when=synode.field('every_second_table', 'checked'),
        action=synode.field('even_odd', 'enabled'))

    def execute(self, node_context):
        """
        Loop over all the tables in the input and forward some or all of them
        depending on the configuration.
        """
        all_tables = not node_context.parameters['every_second_table'].value
        even = node_context.parameters['even_odd'].selected == 'Even'

        out_tables = node_context.output['output']
        for i, in_table in enumerate(node_context.input['input']):
            if (all_tables or
                    even and i % 2 == 0 or
                    not even and i % 2 == 1):
                out_table = table.File()
                out_table.source(in_table)
                out_tables.append(out_table)
