import os
import sys
import ctypes
import threading
import subprocess
import re
import logging
core_logger = logging.getLogger('core')
cygcore = re.compile('^processor[\t]*: [0-9]*.*$')


def thread_count():
    try:
        import psutil
        try:
            return psutil.NUM_CPUS
        except AttributeError:
            return psutil.cpu_count()
    except ImportError:
        if sys.platform == 'cygwin':
            with open('/proc/cpuinfo') as f:
                count = 0
                for line in f:
                    if cygcore.match(line):
                        count += 1
                return count

        core_logger.debug('Could not determine number of threads.')
        return 1



def Popen(args, **kwargs):
    stdin = kwargs.pop('stdin', None)
    stdout = kwargs.pop('stdout', None)
    stderr = kwargs.pop('stderr', None)
    close_fds = kwargs.pop('close_fds', False)

    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    if close_fds is None:
        close_fds = os.name == 'posix'

    return subprocess.Popen(args,
                            stdin=stdin,
                            stdout=stdout,
                            stderr=stderr,
                            close_fds=close_fds,
                            **kwargs)


def run_spyder(filenames=None):
    filenames = filenames or []
    startup_file = os.path.abspath(os.path.join(
        os.environ['SY_APPLICATION_DIR'], 'Python', 'sympathy', 'utils',
        'python_startup.py'))

    os.environ['PYTHONPATH'] = '{}{}{}'.format(
        os.environ['PYTHONPATH'],
        os.path.pathsep,
        os.environ['SY_PYTHON_SUPPORT'])
    os.environ['PYTHONSTARTUP'] = startup_file
    Popen(
        [sys.executable, '-c', """
import sys
from spyderlib import start_app
sys.argv = sys.argv[:1] + [arg.decode("utf8") for arg in sys.argv[1:]]
start_app.main()""",
         ] + [filename.encode('utf8') for filename in filenames],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

if os.name == 'nt':
    import pywintypes
    import win32api
    import win32con
    import win32file
    import win32job
    import win32process
elif os.name == 'posix':
    import fcntl


class TimeoutError(Exception):
    pass


class IFileLock(object):
    def __init__(self, file_object):
        self._file = file_object

    def aquire(self):
        raise NotImplemented

    def release(self):
        raise NotImplemented

    def __enter__(self):
        self.aquire()

    def __exit__(self, *args):
        self.release()


class FileLockUnix(IFileLock):
    def aquire(self):
        fcntl.fcntl(self._file.fileno(), fcntl.LOCK_EX)

    def release(self):
        fcntl.fcntl(self._file.fileno(), fcntl.LOCK_UN)


class FileLockCygwin(IFileLock):
    def aquire(self):
        core_logger.debug('File lock is not implemented for cygwin.')

    def release(self):
        core_logger.debug('File lock is not implemented for cygwin.')


class FileLockDarwin(IFileLock):
    def aquire(self):
        fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)

    def release(self):
        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)


class FileLockWindows(IFileLock):
    def aquire(self):
        win32file.LockFileEx(win32file._get_osfhandle(self._file.fileno()),
                             win32con.LOCKFILE_EXCLUSIVE_LOCK, 0, -0x10000,
                             pywintypes.OVERLAPPED())

    def release(self):
        try:
            win32file.UnlockFileEx(
                win32file._get_osfhandle(self._file.fileno()),
                0, -0x10000, pywintypes.OVERLAPPED())
        except pywintypes.error as e:
            # Do not fail unlocking unlocked file.
            if e[0] == 158:
                pass
            else:
                raise


class FileLockTimeout(IFileLock):
    def __init__(self, file_object, timeout):
        self.timeout = float(timeout)
        self._file_lock = _file_lock_factory()(file_object)

    def aquire(self):
        def run_aquire():
            self._file_lock.aquire()
            with mutex:
                if done.is_set():
                    self.release()
                done.set()

        mutex = threading.Lock()
        done = threading.Event()
        thread = threading.Thread(target=run_aquire)
        thread.daemon = True
        thread.start()
        thread.join(self.timeout)
        with mutex:
            if not done.is_set():
                done.set()
                raise TimeoutError

    def release(self):
        self._file_lock.release()


class FileLock(IFileLock):
    def __init__(self, file_object, timeout=None):
        self.timeout = timeout
        if timeout is None:
            self._file_lock = _file_lock_factory()(file_object)
        else:
            self._file_lock = FileLockTimeout(file_object, timeout)

    def aquire(self):
        self._file_lock.aquire()

    def release(self):
        self._file_lock.release()


def _file_lock_factory():
    if os.name == 'nt':
        return FileLockWindows
    elif os.name == 'posix':
        if sys.platform == 'darwin':
            return FileLockDarwin
        if sys.platform == 'cygwin':
            return FileLockCygwin
        return FileLockUnix
    assert(False)


class IProcessGroup(object):
    def __init__(self):
        raise NotImplemented

    def add_pid(self, pid):
        raise NotImplemented

    def subprocess_arguments(self):
        raise NotImplemented


class ProcessGroupWindows(IProcessGroup):
    def __init__(self):
        hJob = win32job.CreateJobObject(None, '')
        info = win32job.QueryInformationJobObject(
            hJob, win32job.JobObjectExtendedLimitInformation)
        info['BasicLimitInformation']['LimitFlags'] = (
            win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
        win32job.SetInformationJobObject(
            hJob, win32job.JobObjectExtendedLimitInformation, info)
        self._hJob = hJob

    def add_pid(self, pid):
        hProcess = win32api.OpenProcess(win32con.PROCESS_SET_QUOTA |
                                        win32con.PROCESS_TERMINATE,
                                        False, pid)
        win32job.AssignProcessToJobObject(self._hJob, hProcess)
        win32api.CloseHandle(hProcess)

    def subprocess_arguments(self):
        return {'creationflags': win32process.CREATE_BREAKAWAY_FROM_JOB}


class ProcessGroupUnix(IProcessGroup):
    def __init__(self):
        os.setpgrp()

    def add_pid(self, pid):
        # Currently inherited from the parent process.
        # For more fine grained control or to cover more usecases, this
        # Would have to be refined.
        pass

    def subprocess_arguments(self):
        return {'close_fds': True}


def process_group_factory():
    if os.name == 'nt':
        return ProcessGroupWindows()
    elif os.name == 'posix':
        return ProcessGroupUnix()
    assert(False)


def focus_widget(widget):
    """
    Brings a widget window into focus on systems where it is needed (currently
    Windows).
    """
    if sys.platform == 'win32':
        null_ptr = ctypes.POINTER(ctypes.c_int)()
        bg_hwnd = widget.winId()
        try:
            bg_pid = ctypes.windll.user32.GetWindowThreadProcessId(
                bg_hwnd, null_ptr)
        except ctypes.ArgumentError:
            ctypes.pythonapi.PyCObject_AsVoidPtr.restype = ctypes.c_void_p
            ctypes.pythonapi.PyCObject_AsVoidPtr.argtypes = [ctypes.py_object]
            bg_hwnd = ctypes.pythonapi.PyCObject_AsVoidPtr(bg_hwnd)
            bg_pid = ctypes.windll.user32.GetWindowThreadProcessId(
                bg_hwnd, null_ptr)

        fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
        fg_pid = ctypes.windll.user32.GetWindowThreadProcessId(
            fg_hwnd, null_ptr)

        if bg_pid == 0 or fg_pid == 0:
            return

        if ctypes.windll.user32.AttachThreadInput(fg_pid, bg_pid, 1) == 0:
            return

        if ctypes.windll.user32.SetForegroundWindow(bg_hwnd) == 0:
            return

        if ctypes.windll.user32.BringWindowToTop(fg_hwnd) == 0:
            return

        if ctypes.windll.user32.BringWindowToTop(bg_hwnd) == 0:
            return

        if ctypes.windll.user32.AttachThreadInput(fg_pid, bg_pid, 0) == 0:
            return
