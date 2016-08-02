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
import operator
from collections import OrderedDict

from . import parameter_helper_gui as gui

# Import * to ensure that the API is backwards compatible with older versions
# of the parameter helper API where everything was in a single module.
from .parameter_helper_gui import *  # noqa
from .parameter_helper_visitors import *  # noqa


class ParameterEntity(object):
    __slots__ = ('_name', '_parameter_dict')

    def __init__(self, parameter_dict, name, ptype,
                 label=None, description=None, order=None, **kwargs):
        super(ParameterEntity, self).__init__()
        self._parameter_dict = parameter_dict
        self.name = name
        self.type = ptype
        if order is not None:
            self.order = order
        if label is not None:
            self.label = label
        if description is not None:
            self.description = description

    @property
    def parameter_dict(self):
        return self._parameter_dict

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def type(self):
        return self._parameter_dict['type']

    @type.setter
    def type(self, ptype):
        self._parameter_dict['type'] = ptype

    @property
    def label(self):
        try:
            return self._parameter_dict['label']
        except KeyError:
            return ""

    @label.setter
    def label(self, label):
        self._parameter_dict['label'] = label

    @property
    def description(self):
        try:
            return self._parameter_dict['description']
        except KeyError:
            return ""

    @description.setter
    def description(self, description):
        self._parameter_dict['description'] = description

    @property
    def order(self):
        try:
            return self._parameter_dict['order']
        except KeyError:
            return None

    @order.setter
    def order(self, order):
        self._parameter_dict['order'] = order

    def as_dict(self):
        raise NotImplementedError("Must extend this method!")


class ParameterValue(ParameterEntity):
    """docstring for ParameterValue"""
    __slots__ = ('_parameter_dict')

    def __init__(self, parameter_dict, name, ptype, value,
                 editor=None, **kwargs):
        super(ParameterValue, self).__init__(
            parameter_dict, name, ptype, **kwargs)
        self._parameter_dict = parameter_dict
        self.value = value
        self.editor = editor

    @property
    def value(self):
        return self._parameter_dict['value']

    @value.setter
    def value(self, value):
        self._parameter_dict['value'] = value

    @property
    def editor(self):
        return self._parameter_dict['editor']

    @editor.setter
    def editor(self, item):
        self._parameter_dict['editor'] = item

    def as_dict(self):
        return ({
            "type": self.type,
            "value": self.value})

    def __str__(self):
        return str({
            "type": self.type,
            "value": self.value})


class ParameterInteger(ParameterValue):
    def __init__(self, parameter_dict, name, value=0, **kwargs):
        super(ParameterInteger, self).__init__(
            parameter_dict, name, "integer", value, **kwargs)

    def gui(self):
        if self.editor is None:
            return gui.ParameterNumericValueWidget(self)
        else:
            return gui.ParameterNumericValueWidget(
                self,
                gui.editor_factory(
                    self.editor['type'],
                    self.editor,
                    self))

    def accept(self, visitor):
        visitor.visit_integer(self)


class ParameterFloat(ParameterValue):
    def __init__(self, parameter_dict, name, value=0, **kwargs):
        super(ParameterFloat, self).__init__(
            parameter_dict, name, "float", value, **kwargs)

    def gui(self):
        return gui.ParameterNumericValueWidget(self)

    def accept(self, visitor):
        visitor.visit_float(self)


class ParameterString(ParameterValue):
    def __init__(self, parameter_dict, name, value="", **kwargs):
        super(ParameterString, self).__init__(
            parameter_dict, name, "string", value, **kwargs)

    def gui(self):
        if self.editor is None:
            return gui.ParameterStringWidget(self)
        else:
            return gui.ParameterStringWidget(
                self, gui.editor_factory(
                    self.editor['type'],
                    self.editor,
                    self))

    def accept(self, visitor):
        visitor.visit_string(self)


class ParameterBoolean(ParameterValue):
    def __init__(self, parameter_dict, name, value=False, **kwargs):
        super(ParameterBoolean, self).__init__(
            parameter_dict, name, "boolean", value, **kwargs)

    def gui(self):
        return gui.ParameterBooleanWidget(self)

    def accept(self, visitor):
        visitor.visit_boolean(self)


class ParameterList(ParameterEntity):
    """ParameterList"""
    def __init__(self, parameter_dict, name, plist=None, value=None,
                 editor=None, **kwargs):
        super(ParameterList, self).__init__(
            parameter_dict, name, 'list', **kwargs)

        if plist is None:
            plist = []
            value = [0]
        self.value = value
        self.value_names = kwargs.get('value_names', [])

        # This special handling is due to the name 'list' in kwargs
        # is reserved in Python and cannot be used as an an argument.

        if plist != []:
            self.list = plist
        else:
            self.list = kwargs.get('list', [])

        self.passthrough = kwargs.get('passthrough', False)
        self.editor = editor

    @property
    def selected(self):
        """Return the first selected item in the value list,
        does not support multi-select."""
        try:
            return self._parameter_dict['list'][self.value[0]]
        except:
            return None

    @selected.setter
    def selected(self, item):
        self.value = [self._parameter_dict['list'].index(item)]

    @property
    def value(self):
        return self._parameter_dict['value']

    @value.setter
    def value(self, value_):
        if ('list' in self._parameter_dict and
                self._parameter_dict['list'] != []):
            self._parameter_dict['value_names'] = [
                self._parameter_dict['list'][item] for item in value_]
        self._parameter_dict['value'] = value_

    @property
    def value_names(self):
        return self._parameter_dict['value_names']

    @value_names.setter
    def value_names(self, value_names_):
        if 'list' in self._parameter_dict:
            self._parameter_dict['value'] = [
                self._parameter_dict['list'].index(item)
                for item in value_names_]
        self._parameter_dict['value_names'] = value_names_

    @property
    def passthrough(self):
        return self._parameter_dict['passthrough']

    @passthrough.setter
    def passthrough(self, passthrough_):
        self._parameter_dict['passthrough'] = passthrough_

    @property
    def list(self):
        return self._parameter_dict['list']

    @list.setter
    def list(self, plist):
        self._parameter_dict['list'] = plist

    @property
    def editor(self):
        return self._parameter_dict['editor']

    @editor.setter
    def editor(self, item):
        self._parameter_dict['editor'] = item

    def gui(self):
        return gui.ParameterListWidget(
            self, gui.editor_factory(
                self.editor['type'],
                self.editor,
                self))

    def accept(self, visitor):
        visitor.visit_list(self)


class ParameterGroup(ParameterEntity):
    def __init__(self, parameter_dict, name, ptype="group", **kwargs):
        super(ParameterGroup, self).__init__(
            parameter_dict, name, ptype, **kwargs)
        self._subgroups = OrderedDict()
        self._parameter_dict = parameter_dict

    def create_group(self, name, label="", order=None):
        try:
            # If the parameter_dict contains the key
            # it will be used instead of creating a new.
            self._subgroups[name] = ParameterGroup(
                self._parameter_dict[name], name)
        except KeyError:
            self._parameter_dict[name] = OrderedDict()
            self._subgroups[name] = ParameterGroup(
                self._parameter_dict[name], name, label=label, order=order)
        return self._subgroups[name]

    def create_page(self, name, label="", order=None):
        try:
            # If the parameter_dict contains the key
            # it will be used instead of creating a new.
            self._subgroups[name] = ParameterPage(
                self._parameter_dict[name], name)
        except KeyError:
            self._parameter_dict[name] = OrderedDict()
            self._subgroups[name] = ParameterPage(
                self._parameter_dict[name], name, label=label, order=order)
        return self._subgroups[name]

    def set_integer(self, name, value=0, label="",
                    description="", order=None, **kwargs):
        self._set_value(ParameterInteger, name, value, label=label,
                        description=description, order=order, **kwargs)

    def set_float(self, name, value=0.0, label="",
                  description="", order=None, **kwargs):
        self._set_value(ParameterFloat, name, value, label=label,
                        description=description, order=order, **kwargs)

    def set_string(self, name, value="", label="",
                   description="", order=None, **kwargs):
        self._set_value(ParameterString, name, value, label=label,
                        description=description, order=order, **kwargs)

    def set_boolean(self, name, value=False, label="",
                    description="", order=None, **kwargs):
        self._set_value(ParameterBoolean, name, value, label=label,
                        description=description, order=order, **kwargs)

    def set_list(self, name, plist=None, value=None, label="",
                 description="", order=None, **kwargs):
        if plist is None:
            plist = []
        if value is None:
            value = [0]
        try:
            self._subgroups[name].list = plist
            self._subgroups[name].value = value
        except KeyError:
            self._parameter_dict[name] = {}
            self._subgroups[name] = ParameterList(
                self._parameter_dict[name], name, plist, value,
                label=label, description=description, order=order, **kwargs)
        return self._subgroups[name]

    def set_custom(self, custom_handler, name, **kwargs):
        return custom_handler.create_custom_parameters(self, name, **kwargs)

    def value_or_default(self, name, default):
        try:
            return self._subgroups[name].value
        except KeyError:
            return default

    def value_or_empty(self, name):
        return self.value_or_default(name, '')

    def keys(self):
        return self._subgroups.keys()

    def children(self):
        return sorted(self._subgroups.values(),
                      key=operator.attrgetter('order'))

    def reorder(self):
        items = self._subgroups.values()
        if items:
            orders = [getattr(item, 'order', None) for item in items]
            maxorder = (max(orders) or 0) + 1
            orders = [maxorder if order is None else order for order in orders]
            for i, (order, item) in enumerate(sorted(
                    zip(orders, items), key=lambda x: x[0])):
                item.order = i

    def gui(self):
        return gui.ParameterGroupWidget(self)

    def accept(self, visitor):
        visitor.visit_group(self)

    def _set_value(self, value_class, name, value="", label="",
                   description="", order=0, **kwargs):
        try:
            self._subgroups[name].value = value
        except KeyError:
            self._parameter_dict[name] = {}
            self._subgroups[name] = value_class(
                self._parameter_dict[name], name, value,
                label=label, description=description, order=order, **kwargs)
        return self._subgroups[name]

    def _dict(self):
        return self._parameter_dict

    def __getitem__(self, name):
        return self._subgroups[name]

    def __setitem__(self, name, value):
        self._parameter_dict[name] = value._parameter_dict
        self._subgroups[name] = value

    def __iter__(self):
        for name in self.keys():
            yield name

    def __contains__(self, name):
        return name in self._subgroups

    def __str__(self):
        return str(self._parameter_dict)


class ParameterPage(ParameterGroup):
    def __init__(self, parameter_dict, name, **kwargs):
        super(ParameterPage, self).__init__(
            parameter_dict, name, "page", **kwargs)

    def accept(self, visitor):
        visitor.visit_page(self)


class ParameterRoot(ParameterGroup):
    def __init__(self, parameter_data=None, custom_handler=None):
        if parameter_data is None:
            parameter_dict = OrderedDict()
        elif isinstance(parameter_data, ParameterGroup):
            parameter_dict = parameter_data.parameter_dict
        else:
            parameter_dict = parameter_data
        super(ParameterRoot, self).__init__(parameter_dict, "root")
        ParameterBuilder(self, custom_handler).build()

    def accept(self, visitor):
        visitor.visit_root(self)


class ParameterBuilder(object):
    """ParameterBuilder"""
    def __init__(self, parameter_group, custom_handler):
        super(ParameterBuilder, self).__init__()
        self._parameter_group = parameter_group
        self._custom_handler = custom_handler

    def build(self):
        for name, value in self._parameter_group._dict().iteritems():
            if isinstance(value, dict):
                self._factory(name, value)

    def _factory(self, name, value_dict):
        ptype = value_dict['type']
        if ptype == "group":
            new_group = self._parameter_group.create_group(name)
            # Build groups recursively
            ParameterBuilder(new_group, self._custom_handler).build()
        elif ptype == "page":
            new_page = self._parameter_group.create_page(name)
            # Build groups recursively
            ParameterBuilder(new_page, self._custom_handler).build()
        elif ptype == "integer":
            self._parameter_group.set_integer(name, **value_dict)
        elif ptype == "float":
            self._parameter_group.set_float(name, **value_dict)
        elif ptype == "string":
            self._parameter_group.set_string(name, **value_dict)
        elif ptype == "boolean":
            self._parameter_group.set_boolean(name, **value_dict)
        elif ptype == "list":
            self._parameter_group.set_list(name, **value_dict)
        elif ptype == "custom":
            self._parameter_group.set_custom(
                self._custom_handler, name, **value_dict)
        else:
            raise NotImplementedError(
                "Factory for type not implemented!")


class ParameterCustom(ParameterEntity):
    def __init__(self, parameter_dict, name):
        super(ParameterCustom, self).__init__(
            parameter_dict, name, "custom")

    def accept(self, visitor):
        visitor.visit_custom(self)


class CustomParameterHandler(object):
    def create_custom_parameters(self, parameter_group, name, **kwargs):
        parameter_group._parameter_dict[name] = {}
        parameter_group._subgroups[name] = ParameterCustom(
            parameter_group._parameter_dict, name)
        return parameter_group._subgroups[name]
