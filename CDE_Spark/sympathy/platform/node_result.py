import json
import traceback
import collections
import sys
import dateutil.parser
import logging

from . exceptions import SyNodeError

from .. utils.prim import limit_traceback

node_perf_logger = logging.getLogger('node.perf')


class ExceptionInformation(object):
    """Information about a single exception."""

    def __init__(self):
        super(ExceptionInformation, self).__init__()
        self._type = ''
        self._string = ''
        self._node_error = False
        self._trace = []
        self._details = ''

    @classmethod
    def from_exc_info(cls, limit_filename=None):
        """
        Usage:
        ei = ExceptionInformation.from_exc_info()
        """
        instance = cls()
        type_, value, frame = sys.exc_info()
        instance.set_from_exc_info(type_, value, frame, limit_filename)
        return instance

    def _get_trace_step(self, function, line, filename):
        step = collections.namedtuple(
            'ExceptionTraceStep', ['function', 'line', 'filename'])
        step.function = function
        step.line = line
        step.filename = filename
        return step

    @classmethod
    def from_dict(cls, d):
        if d is None:
            return cls()
        instance = cls()
        instance._type = d['type']
        instance._string = d['string']
        instance._node_error = d['node_error']
        instance._trace = []
        for function, line, filename in d['trace']:
            instance._trace.append(
                instance._get_trace_step(function, line, filename))
        instance._details = d['details']
        return instance

    def set_from_exc_info(self, type_, value, frame, limit_filename=None):
        """Set exception information from the output of sys.exc_info()."""
        if type_ is None:
            self._type = u''
        else:
            self._type = type_.__name__
        self._string = unicode(value)
        self._trace = []
        self._node_error = issubclass(type_, SyNodeError)
        if self._node_error:
            self._details = value.help_text
        else:
            fs_encoding = sys.getfilesystemencoding()
            trace_lines = []
            for line in traceback.format_exception(type_, value, frame):
                if isinstance(line, str):
                    line = line.decode(fs_encoding)
                trace_lines.append(line)

            self._details = limit_traceback(trace_lines, limit_filename)

            while frame:
                self._trace.append(self._get_trace_step(
                    frame.tb_frame.f_code.co_name,
                    frame.tb_frame.f_lineno,
                    frame.tb_frame.f_code.co_filename.decode(
                        sys.getfilesystemencoding())))
                frame = frame.tb_next

    def __str__(self):
        if self.is_raised():
            return self._details
        else:
            return ''

    def to_dict(self):
        return {
            'type': unicode(self._type),
            'string': unicode(self._string),
            'node_error': self._node_error,
            'trace': [(f.function, f.line, f.filename) for f in self._trace],
            'details': unicode(self._details)}

    def is_raised(self):
        return self._type is not None and self._type != ''

    @property
    def type(self):
        return self._type

    @property
    def string(self):
        return self._string

    @property
    def node_error(self):
        return self._node_error

    @property
    def details(self):
        return self._details


class NodeResult(object):
    """
    Wrapper for node execution/validation/configuration outputs.
    """

    def __init__(self):
        super(NodeResult, self).__init__()
        self._stderr = u''
        self._stdout = u''
        self._exception = ExceptionInformation()
        self._valid = True
        self._output = None
        self._times = {}

    @classmethod
    def from_dict(cls, d):
        instance = cls()
        instance._stdout = d['stdout']
        instance._stderr = d['stderr']
        instance._exception = ExceptionInformation.from_dict(d['exception'])
        instance._valid = d['valid']
        instance._output = d['output']
        instance._times = {k: dateutil.parser.parse(v)
                           for k, v in d['times'].items()}
        return instance

    def update(self, other):
        if 'stdout' in other:
            self._stdout = other['stdout']
        if 'stderr' in other:
            self._stderr = other['stderr']
        if 'exception' in other:
            self._exception = ExceptionInformation.from_dict(
                other['exception'])
        if 'valid' in other:
            self._valid = other['valid']
        if 'output' in other:
            self._output = other['output']
        if 'times' in other:
            self._times = {k: dateutil.parser.parse(v)
                           for k, v in other['times'].items()}

    @property
    def stderr(self):
        return self._stderr

    @stderr.setter
    def stderr(self, value):
        self._stderr = value

    @property
    def stdout(self):
        return self._stdout

    @stdout.setter
    def stdout(self, value):
        self._stdout = value

    @property
    def exception(self):
        return self._exception

    @exception.setter
    def exception(self, value):
        self._exception = value

    def store_current_exception(self, limit_filename=None):
        self._exception = ExceptionInformation.from_exc_info(
            limit_filename)

    @property
    def output(self):
        if self._output:
            return json.loads(self._output)
        else:
            return None

    @output.setter
    def output(self, value):
        self._output = json.dumps(value)

    @property
    def valid(self):
        return self._valid

    @valid.setter
    def valid(self, value):
        self._valid = value

    @property
    def times(self):
        return self._times

    def format_std_output(self):
        output = u''
        if len(self._stdout) > 0:
            output += u'----- stdout: {}\n'.format(self._stdout)

        if len(self._stderr) > 0:
            output += u'----- stderr: {}\n'.format(self._stderr)
        return output

    def to_dict(self):
        return {
            'stdout': self._stdout,
            'stderr': self._stderr,
            'exception': (self._exception.to_dict()
                          if self._exception is not None else None),
            'valid': self._valid,
            'output': self._output,
            'times': {k: v.isoformat() for k, v in self._times.items()}}

    def __str__(self):
        return json.dumps(self.to_dict(), indent=2)

    def has_exception(self):
        return self._exception.is_raised()

    def has_error(self):
        return self.has_exception()

    def log_times(self):
        for k, v in sorted(self._times.items(), key=lambda x: x[1]):
            node_perf_logger.debug('{} {}'.format(v.isoformat(), k))
