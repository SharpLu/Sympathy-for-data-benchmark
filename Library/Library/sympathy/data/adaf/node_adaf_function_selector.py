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
Please see :ref:`F(x) Table` for the basics on f(x) nodes.

The main base class for adaf f(x) nodes is called ``ADAFWrapper``. It gives
access to the variables ``self.in_adaf`` and ``self.out_adaf`` which are of the
type :class:`adaf.File` so you will need to use the :ref:`adafapi`.
"""
from sympathy.api import node as synode
from sympathy.api import adaf
from sympathy.api import table
from sympathy.api import adaf_wrapper
from sympathy.api.nodeconfig import Port, Ports
from sylib.function_selector_base import (
    SuperNode, SuperNodeList, FunctionSelectorBase, FunctionSelectorBaseList)


class FunctionSelectorADAF(SuperNode, synode.Node):
    """
    Apply functions to an ADAF.

    :Inputs:
        **port1** : Datasource
            Path to Python file with scripted functions.
        **port2** : ADAF
            ADAF with data to apply functions to.
    :Outputs:
        **port3** : ADAF
            ADAF with the results from the applied functions.
    :Configuration:
        **Clean output**
            If disabled the incoming data will be copied to the output before
            running the nodes.
        **Select functions**
            Choose one or many of the listed functions to run.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) Table` :ref:`F(x) ADAFs`
    """
    name = 'F(x) ADAF'
    description = ('Select functions from the datasource to be applied '
                   'to the incoming ADAF.')
    nodeid = 'org.sysess.sympathy.data.adaf.functionselectoradaf'

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.ADAF('Input ADAF', name='port2')])
    outputs = Ports([Port.ADAF(
        'Output ADAF with function(s) applied', name='port3')])

    def __init__(self):
        super(FunctionSelectorADAF, self).__init__()
        self._function_selector_base = FunctionSelectorBase(
            adaf_wrapper.ADAFWrapper, adaf)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_single(
            node_context, self.set_progress)


class FunctionSelectorADAFs(SuperNodeList, synode.Node):
    """
    Apply functions to a list of ADAFs.

    Can be used with either the main base class or with the base class
    ``ADAFsWrapper`` which gives access to the entire list of ADAFs at once.
    When using this base class you should access the input and output data with
    ``self.in_adaf_list`` and ``self.out_adaf_list`` respectively. They are
    both of the type ``adaf.FileList``.

    See also :ref:`F(x) Table` for a brief discussion of when to use the
    "plural" base classes.

    :Inputs:
        **port1** : Datasource
            Path to Python file with scripted functions.
        **port2** : ADAFs
            ADAFs with data to apply functions to.
    :Outputs:
        **port3** : ADAFs
            ADAFs with the results from the applied functions.
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
            Choose one or many of the listed functions to run.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) ADAF`
    """
    name = 'F(x) ADAFs'
    description = ('Select functions from the datasource to be applied '
                   'to the ADAFs in the incoming list.')
    nodeid = 'org.sysess.sympathy.data.adaf.functionselectoradafmultiple'

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.ADAFs('Input ADAF', name='port2')])
    outputs = Ports([Port.ADAFs(
        'Output ADAFs with function(s) applied', name='port3')])

    def __init__(self):
        super(FunctionSelectorADAFs, self).__init__()
        self._function_selector_base = FunctionSelectorBaseList(
            adaf_wrapper.ADAFWrapper, adaf)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_multiple(
            node_context, self.set_progress)


class FunctionSelectorADAFsToTables(SuperNodeList, synode.Node):
    """
    Apply functions to a list of ADAFs outputting a list of Tables.

    With this node you should use one of the base classes
    ``ADAFToTableWrapper`` or ``ADAFsToTablesWrapper``. ``ADAFToTableWrapper``
    gives access to the input adafs one at a time as ``self.in_adaf`` and the
    output tables one at a time as ``self.out_table``. ``ADAFsToTablesWrapper``
    gives access to the input adafs all at once as ``self.in_adaf_list`` and
    the output tables all at once as ``self.out_table_list``.

    See :ref:`F(x) Table` for a brief discussion of when to use the "plural"
    base classes.

    :Inputs:
        **port1** : Datasource
            Path to Python file with scripted functions.
        **port2** : ADAFs
            ADAFs with data to apply functions to.
    :Outputs:
        **port3** : Tables
            Tables with the results from the applied functions.
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
            Choose one or many of the listed functions to run.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) ADAFs`
    """

    name = 'F(x) ADAFs to Tables'
    description = ('Select functions from the datasource to be applied '
                   'to the ADAFs in the incoming list.')
    nodeid = 'org.sysess.sympathy.data.adaf.functionselectoradafstotables'

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.Adafs('Input ADAFs', name='port2')])
    outputs = Ports([Port.Tables(
        'Output ADAFs with function(s) applied, output as Tables',
        name='port3')])

    def __init__(self):
        super(FunctionSelectorADAFsToTables, self).__init__()
        self._function_selector_base = FunctionSelectorBaseList(
            adaf_wrapper.ADAFToTableWrapper, adaf, table)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_multiple(
            node_context, self.set_progress)


class FunctionSelectorADAFsWithExtra(SuperNodeList, synode.Node):
    """
    Apply functions to a list of ADAFs. Also passes an extra auxiliary Table to
    the functions.

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
            Choose one or many of the listed functions to run.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) Table`
    """

    name = 'F(x) ADAFs With Extra Input'
    description = 'Select and apply functions to ADAFs.'
    nodeid = (
        'org.sysess.sympathy.data.adaf.'
        'functionselectoradafmultiplewithextra')

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.Table('Specification Table', name='extra'),
        Port.ADAFs('Input ADAFs', name='port2')])
    outputs = Ports([Port.ADAFs(
        'Output ADAFs with function(s) applied', name='port3')])

    def __init__(self):
        super(FunctionSelectorADAFsWithExtra, self).__init__()
        self._function_selector_base = FunctionSelectorBaseList(
            adaf_wrapper.ADAFWrapper, adaf)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_multiple(node_context,
                                                      self.set_progress)


class FunctionSelectorADAFsWithExtras(SuperNodeList, synode.Node):
    """
    Apply functions to a list of ADAFs. Also passes an extra auxiliary list of
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
            Choose one or many of the listed functions to run.
        **Enable pass-through**
            If disabled only selected functions are run. Enable this to
            override the functions selection and run all functions in the
            python file.
    :Ref. nodes: :ref:`F(x) Table`
    """

    name = 'F(x) ADAFs With Extras Input'
    description = 'Select and apply functions to ADAFs.'
    nodeid = (
        'org.sysess.sympathy.data.adaf.'
        'functionselectoradafmultiplewithextras')

    inputs = Ports([
        Port.Datasource('Python *.py file', name='port1', requiresdata=True),
        Port.Tables('Specification Tables', name='extra'),
        Port.ADAFs('Input ADAFs', name='port2')])
    outputs = Ports([Port.ADAFs(
        'Output ADAFs with function(s) applied', name='port3')])

    def __init__(self):
        super(FunctionSelectorADAFsWithExtras, self).__init__()
        self._function_selector_base = FunctionSelectorBaseList(
            adaf_wrapper.ADAFWrapper, adaf)

    def exec_parameter_view(self, node_context):
        return self._function_selector_base.exec_parameter_view(node_context)

    def adjust_parameters(self, node_context):
        return self._function_selector_base.adjust_parameters(node_context)

    def execute(self, node_context):
        self._function_selector_base.execute_multiple(node_context,
                                                      self.set_progress)
