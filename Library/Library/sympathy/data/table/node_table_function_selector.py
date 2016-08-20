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
The plethora of f(x) nodes all have a similar role as the
:ref:`Calculator Tables` node. But where the :ref:`Calculator Tables` node
shines when the calculations are simple, the f(x) nodes are better suited
for more advanced calculations since the code is kept in a separate python
file. You can place this python file anywhere, but it might be a good idea
to keep it in the same folder as your workflow or in a subfolder to that
folder.


The script file
^^^^^^^^^^^^^^^
When writing a "function" (it is actually a python class) you need to inherit
from one of the two classes ``TableWrapper`` or ``TablesWrapper``. The first
one is easier and should be your default choice.

The ``TableWrapper`` provides access to the input and output table with
``self.in_table`` and ``self.out_table`` respectively. These variables are of
type :class:`table.File`, so use the :ref:`tableapi` to read/write the data.
For example::

    from sympathy.api import table_wrapper

    class MyCalculation(table_wrapper.TableWrapper):
        def execute(self):
            spam = self.in_table.get_column_to_array('spam')

            # My super advanced calculation that totally couldn't be
            # done in the :ref:`Calculator Tables` node:
            more_spam = spam + 1

            self.out_table.set_column_from_array('more spam', more_spam)

When working with a list of tables you can use the same base class as above and
your code will conveniently be executed once for each table. Alternatively you
can use the class ``sympathy.api.table_wrapper.TablesWrapper`` (note the *s*).
This class will give access to the entire list all at once. This is useful for
when you need your code to be aware of several different tables from the list
at once, or if you need to output a list with a different number of tables than
the input. If you don't need any of these features you're better off using the
``TableWrapper`` base class.

When using the ``TablesWrapper`` base class you should access the input and
output data with ``self.in_table_list`` and ``self.out_table_list``
respectively (which are of the type ``table.FileList``). An example function::

    from sympathy.api import table_wrapper

    class MyCalculation(table_wrapper.TablesWrapper):
        def execute(self):
            for in_table in self.in_table_list:
                # Only input tables with a column named 'spam' will yield an
                # output table.
                if 'spam' not in in_table.column_names():
                    continue
                spam = in_table.get_column_to_array('spam')

                # My super advanced calculation that totally couldn't be
                # done in the :ref:`Calculator Tables` node:
                more_spam = spam + 1

                out_table = self.out_table_list.create()
                out_table.set_column_from_array('more spam', more_spam)
                self.out_table_list.append(out_table)

Three of the f(x) nodes (:ref:`F(x) Table With Extra Input`,
:ref:`F(x) Tables With Extra Input`, :ref:`F(x) Tables With Extras Input`) have
an extra table input port. You can access the extra table(s) as
``self.extra_table``.


Testing your script
^^^^^^^^^^^^^^^^^^^
When writing an f(x) script it can be convenient to be able to run the script
from inside Spyder without switching to Sympathy. To do this you should first
export all the data that the f(x) node receives on its input port as a sydata
file. Then add a code block like this to the end of your script file::

    if __name__ == "__main__":
        from sympathy.api import table
        input_filename = r"/path/to/input_file.sydata"

        with table.File(filename=input_filename, mode='r') as input_file:
            output_file = table.File()
            MyCalculation(input_file, output_file).execute()

You can now step through the code, set up break points and inspect variables as
you run the script. Note that this will only work if the script is meant to be
run with the *Clean output* option selected.


Configuration
^^^^^^^^^^^^^
When *Clean output* is enabled (the default) the output table will be empty
when the functions are run.

When the *Clean output* setting is disabled the entire input table will get
copied to the output before running the functions in the file. This is useful
when your functions should only add a few columns to a data table, but in this
case you must make sure that the output has the same number of rows as the
input.

By default (*pass-through* disabled) only the functions that you have manually
selected in the configuration will be run when you execute the node, but with
the *pass-through* setting enabled the node will run all the functions in the
selected file. This can be convenient in some situations when new functions are
added often.
"""
from sympathy.api import node as synode
from sympathy.api import table
from sympathy.api import table_wrapper
from sympathy.api.nodeconfig import Port, Ports
from sylib.function_selector_base import (
    SuperNode, SuperNodeList, FunctionSelectorBase, FunctionSelectorBaseList)


class FunctionSelectorTable(SuperNode, synode.Node):
    """
    Apply functions to a Table.

    :Inputs:
        **port1** : Datasource
            Path to Python file with scripted functions.
        **port2** : Tables
            Table with data to apply functions to.
    :Outputs:
        **port3** : Table
            Table with the results from the applied functions
    :Configuration:
        **Clean output**
            If disabled the incoming data will be copied to the output before
            running the nodes.
        **Select functions**
            Choose one or many of the listed functions to apply to the content
            of the incoming Table.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) Tables`
    """
    name = 'F(x) Table'
    description = 'Select and apply functions to a Table.'
    nodeid = 'org.sysess.sympathy.data.table.functionselectortable'

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.Table('Input', name='port2')])
    outputs = Ports([Port.Table('Output', name='port3')])

    def __init__(self):
        super(FunctionSelectorTable, self).__init__()
        self._function_selector_base = FunctionSelectorBase(
            table_wrapper.TableWrapper, table)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_single(node_context,
                                                    self.set_progress)


class FunctionSelectorTableWithExtra(SuperNode, synode.Node):
    """
    Apply functions to a Table. Also passes an extra auxiliary Table to the
    functions.

    :Inputs:
        **port1** : Datasource
            Path to Python file with scripted functions.
        **port2** : Tables
            Table with data to apply functions to.
    :Outputs:
        **port3** : Table
            Table with the results from the applied functions
    :Configuration:
        **Clean output**
            If disabled the incoming data will be copied to the output before
            running the nodes.
        **Select functions**
            Choose one or many of the listed functions to apply to the content
            of the incoming Table.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) Tables`
    """

    name = 'F(x) Table With Extra Input'
    description = 'Select and apply functions to a Table.'
    nodeid = 'org.sysess.sympathy.data.table.functionselectortablewithextra'

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.Table('Specification', name='extra'),
        Port.Table('Input Table', name='port2')])
    outputs = Ports([
        Port.Table('Table with function(s) applied', name='port3')])

    def __init__(self):
        super(FunctionSelectorTableWithExtra, self).__init__()
        self._function_selector_base = FunctionSelectorBase(
            table_wrapper.TableWrapper, table)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_single(node_context,
                                                    self.set_progress)


class FunctionSelectorTables(SuperNodeList, synode.Node):
    """
    Apply functions to a list of Tables.

    :Inputs:
        **port1** : Datasource
            Path to Python file with scripted functions.
        **port2** : Tables
            Tables with data to apply functions to.
    :Outputs:
        **port3** : Tables
            Tables with the results from the applied functions
    :Configuration:
        **Clean output**
            If disabled the incoming data will be copied to the output before
            running the nodes.
        **Put results in common outputs** : checkbox
            Use this checkbox if you want to gather all the results generated
            from an incoming Table into a common output. This requires that
            the results will all have the same length. An exception will be
            raised if the lengths of the outgoing results differ.
            It is used only when clean output is active. Otherwise it will be
            disabled and can be considered as checked.
        **Select functions**
            Choose one or many of the listed functions to apply to the content
            of the incoming Table.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) Table`
    """
    name = 'F(x) Tables'
    description = 'Select and apply functions to Tables.'
    nodeid = 'org.sysess.sympathy.data.table.functionselectortablemultiple'

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.Tables('Input Tables', name='port2')])
    outputs = Ports([
        Port.Tables('Tables with function(s) applied', name='port3')])

    def __init__(self):
        super(FunctionSelectorTables, self).__init__()
        self._function_selector_base = FunctionSelectorBaseList(
            table_wrapper.TableWrapper, table)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_multiple(node_context,
                                                      self.set_progress)


class FunctionSelectorTablesWithExtra(SuperNodeList, synode.Node):
    """
    Apply functions to a list of Tables. Also passes an extra auxiliary Table
    to the functions.

    :Inputs:
        **port1** : Datasource
            Path to Python file with scripted functions.
        **extra** : Table
            Extra Table with eg. specification data.
        **port2** : Tables
            Tables with data to apply functions to.
    :Outputs:
        **port3** : Tables
            Tables with the results from the applied functions
    :Configuration:
        **Clean output**
            If disabled the incoming data will be copied to the output before
            running the nodes.
        **Put results in common outputs** : checkbox
            Use this checkbox if you want to gather all the results generated
            from an incoming Table into a common output. This requires that
            the results will all have the same length. An exception will be
            raised if the lengths of the outgoing results differ.
            It is used only when clean output is active. Otherwise it will be
            disabled and can be considered as checked.
        **Select functions**
            Choose one or many of the listed functions to apply to the content
            of the incoming Table.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) Table`
    """

    name = 'F(x) Tables With Extra Input'
    description = 'Select and apply functions to Tables.'
    nodeid = (
        'org.sysess.sympathy.data.table.'
        'functionselectortablemultiplewithextra')

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.Table('Specification', name='extra'),
        Port.Tables('Input Tables', name='port2')])
    outputs = Ports([
        Port.Tables('Tables with function(s) applied', name='port3')])

    def __init__(self):
        super(FunctionSelectorTablesWithExtra, self).__init__()
        self._function_selector_base = FunctionSelectorBaseList(
            table_wrapper.TableWrapper,
            table)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_multiple(node_context,
                                                      self.set_progress)


class FunctionSelectorTablesWithExtras(SuperNodeList, synode.Node):
    """
    Apply functions to a list of Tables. Also passes an extra auxiliary list of
    Tables to the functions.

    :Inputs:
        **port1** : Datasource
            Path to Python file with scripted functions.
        **extra** : Tables
            Extra Tables with eg. specification data.
        **port2** : Tables
            Tables with data to apply functions to.
    :Outputs:
        **port3** : Tables
            Tables with the results from the applied functions
    :Configuration:
        **Clean output**
            If disabled the incoming data will be copied to the output before
            running the nodes.
        **Put results in common outputs** : checkbox
            Use this checkbox if you want to gather all the results generated
            from an incoming Table into a common output. This requires that
            the results will all have the same length. An exception will be
            raised if the lengths of the outgoing results differ.
            It is used only when clean output is active. Otherwise it will be
            disabled and can be considered as checked.
        **Select functions**
            Choose one or many of the listed functions to apply to the content
            of the incoming Table.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) Table`
    """

    name = 'F(x) Tables With Extras Input'
    description = 'Select and apply functions to Tables.'
    nodeid = (
        'org.sysess.sympathy.data.table.'
        'functionselectortablemultiplewithextras')

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.Tables('Specification', name='extra'),
        Port.Tables('Input Table', name='port2')])
    outputs = Ports([
        Port.Tables('Tables with function(s) applied', name='port3')])

    def __init__(self):
        super(FunctionSelectorTablesWithExtras, self).__init__()
        self._function_selector_base = FunctionSelectorBaseList(
            table_wrapper.TableWrapper,
            table)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_multiple(node_context,
                                                      self.set_progress)
