from sympathy.api import node as synode
from sympathy.api.nodeconfig import Port, Ports, Tag, Tags
from sympathy.api import report


class SuperNodeGeneric(synode.Node):
    author = 'Erik der Hagopian <erik.hagopian@sysess.org>'
    copyright = '(C) 2015 System Engineering Software Society'
    version = '1.0'
    tags = Tags(Tag.Hidden.Deprecated)


def extend(destination, source):
    for element in source:
        destination.append(element)


class ADAFs2List(SuperNodeGeneric):
    """Convert ADAFs to [ADAF]."""

    name = 'ADAFs to [ADAF]'
    nodeid = 'org.sysess.sympathy.list.adafs2list'

    inputs = Ports([
        Port.ADAFs('Input ADAFs', name='adafs')])
    outputs = Ports([
        Port.Custom('[adaf]', 'Input ADAFs converted to List', name='list')])

    def execute(self, node_context):
        extend(node_context.output['list'], node_context.input['adafs'])


class List2ADAFs(SuperNodeGeneric):
    """Convert [ADAF] to ADAFs."""

    name = '[ADAF] to ADAFs'
    nodeid = 'org.sysess.sympathy.list.list2adafs'

    inputs = Ports([
        Port.Custom('[adaf]', 'Input List', name='list')])
    outputs = Ports([
        Port.ADAFs('Input List converted to ADAFs', name='adafs')])

    def execute(self, node_context):
        extend(node_context.output['adafs'], node_context.input['list'])


class Tables2List(SuperNodeGeneric):
    """Convert Tables to [Table]."""

    name = 'Tables to [Table]'
    nodeid = 'org.sysess.sympathy.list.tables2list'

    inputs = Ports([
        Port.Tables('Input Tables', name='tables')])
    outputs = Ports([
        Port.Custom('[table]', 'Input Tables converted to List', name='list')])

    def execute(self, node_context):
        extend(node_context.output['list'], node_context.input['tables'])


class List2Tables(SuperNodeGeneric):
    """Convert [Table] to Tables."""

    name = '[Table] to Tables'
    nodeid = 'org.sysess.sympathy.list.list2tables'

    inputs = Ports([
        Port.Custom('[table]', 'Input List', name='list')])
    outputs = Ports([
        Port.Tables('Input List converted to Tables', name='tables')])

    def execute(self, node_context):
        extend(node_context.output['tables'], node_context.input['list'])


class Texts2List(SuperNodeGeneric):
    """Convert Texts to [Text]."""

    name = 'Texts to [Text]'
    nodeid = 'org.sysess.sympathy.list.texts2list'

    inputs = Ports([
        Port.Texts('Input Texts', name='texts')])
    outputs = Ports([
        Port.Custom('[text]', 'Input Texts converted to List', name='list')])

    def execute(self, node_context):
        extend(node_context.output['list'], node_context.input['texts'])


class List2Texts(SuperNodeGeneric):
    """Convert [Text] to Texts."""

    name = '[Text] to Texts'
    nodeid = 'org.sysess.sympathy.list.list2texts'

    inputs = Ports([
        Port.Custom('[text]', 'Input List', name='list')])
    outputs = Ports([
        Port.Texts('Input List converted to Texts', name='texts')])

    def execute(self, node_context):
        extend(node_context.output['texts'], node_context.input['list'])


class Datasources2List(SuperNodeGeneric):
    """Convert Datasources to [Datasource]."""

    name = 'Datasources to [Datasource]'
    nodeid = 'org.sysess.sympathy.list.datasources2list'

    inputs = Ports([
        Port.Datasources('Input Datasources', name='datasources')])
    outputs = Ports([
        Port.Custom(
            '[datasource]', 'Input Datasources converted to List', name='list',
            scheme='text')])

    def execute(self, node_context):
        extend(node_context.output['list'], node_context.input['datasources'])


class List2Datasources(SuperNodeGeneric):
    """Convert [Datasource] to Datasources."""

    name = '[Datasource] to Datasources'
    nodeid = 'org.sysess.sympathy.list.list2datasources'

    inputs = Ports([
        Port.Custom('[datasource]', 'Input List', name='list', scheme='text')])
    outputs = Ports([
        Port.Datasources(
            'Input List converted to Datasources', name='datasources')])

    def execute(self, node_context):
        extend(node_context.output['datasources'], node_context.input['list'])


class Reports2List(SuperNodeGeneric):
    """Convert Reports to [Report]."""

    name = 'Reports to [Report]'
    nodeid = 'org.sysess.sympathy.list.reports2list'

    inputs = Ports([
        report.Reports('Input Reports', name='reports')])
    outputs = Ports([
        Port.Custom(
            '[report]', 'Input Reports converted to List', name='list')])

    def execute(self, node_context):
        extend(node_context.output['list'], node_context.input['reports'])


class List2Reports(SuperNodeGeneric):
    """Convert [Report] to Reports."""

    name = '[Report] to Reports'
    nodeid = 'org.sysess.sympathy.list.list2reports'

    inputs = Ports([
        Port.Custom('[report]', 'Input List', name='list')])
    outputs = Ports([
        report.Reports('Input List converted to Reports', name='reports')])

    def execute(self, node_context):
        extend(node_context.output['reports'], node_context.input['list'])
