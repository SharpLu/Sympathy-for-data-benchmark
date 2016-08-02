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
import json
import copy
from sympathy import syi as syi_module
from sympathy.api import qt
QtGui = qt.import_module('QtGui')


def ports_to_dict(port_dict):
    new_ports = []
    for port_name, port_value in port_dict.iteritems():
        new_port_value = copy.deepcopy(port_value)
        new_port_value['key'] = port_name
        new_ports.append(new_port_value)
    return new_ports


def node_to_dict(node):
    _dict = node['definition']
    _dict['id'] = node['definition']['nodeid']
    _dict['label'] = node['definition']['name']
    _dict['ports'] = {}

    _dict['ports']['inputs'] = ports_to_dict(
        node['definition'].get('inputs', {}))
    _dict['ports']['outputs'] = ports_to_dict(
        node['definition'].get('outputs', {}))
    _dict['parameters'] = {}
    _dict['parameters']['data'] = json.dumps(node['parameters'])
    return _dict


def to_clipboard(syi, context):
    from sympathy.platform import flow_model
    from sympathy.platform import qt_compat
    # QtCore = qt_compat.QtCore
    qt_app = QtGui.qApp

    clipboard = qt_app.clipboard()

    # connection_manager = syi.connection_manager
    # if syi_module.QT_APP is not None:
    #     clipboard = syi_module.QT_APP.clipboard()
    # else:
    #     from sympathy.platform import qt_compat
    #     QtGui = qt_compat.import_module('QtGui')
    #     syi_module.QT_APP = QtGui.QApplication(sys.argv)

    flow = flow_model.Flow()
    for node in context['nodes']:
        flow.append_node(
            flow_model.Node.from_dict(node_to_dict(node._definition)))
    d = flow.to_clipboard()

    print json.dumps(d, indent=4)

    mime_type_itemlist = 'application-x-sympathy-itemlist'
    # mime_type_node = 'application-x-sympathy-node'
    QtCore = qt_compat.import_module('QtCore')
    mime_data = QtCore.QMimeData()
    mime_data.setData(
        mime_type_itemlist, QtCore.QByteArray(json.dumps(d)))
    clipboard.setMimeData(mime_data)


def execute_node_and_update_viewer(node_cls, viewer_manager, nodes):
    def instantiate(**kwargs):
        data = node_cls(**kwargs)
        nodes.append(data)
        try:
            viewer_manager.update(data)
        except (IndexError, IOError):
            pass
        return data
    return instantiate


class NodeCreatorWrapper(object):
    def __init__(self, syi, viewer_manager, context):
        self._syi = syi
        self._viewer_manager = viewer_manager
        self._context = context
        for key, val in vars(syi.node_creator).iteritems():
            setattr(self, key, execute_node_and_update_viewer(
                val, self._viewer_manager, self._context['nodes']))


class SyiPlaygroundWrapper(object):
    def __init__(self, syi, viewer_manager, context):
        if syi is None:
            self._syi = syi_module.Syi()
        else:
            self._syi = syi
        self._viewer_manager = viewer_manager
        self._context = context
        self._node_creator_wrapper = NodeCreatorWrapper(
            self._syi, self._viewer_manager, self._context)

    @property
    def node_creator(self):
        return self._node_creator_wrapper


class PlayGround(object):
    def __init__(self, syi=None, viewer_manager=None):
        self._context = {
            'nodes': []
        }

        self._viewer_manager = viewer_manager
        self._syi = SyiPlaygroundWrapper(syi, viewer_manager, self._context)

    @property
    def nc(self):
        """Shortcut to Syi node creator."""
        return self._syi.node_creator

    @property
    def viewer(self):
        return self._viewer_manager

    @property
    def syi(self):
        return self._syi

    def to_clipboard(self):
        to_clipboard(self._syi._syi, self._context)
