"""Modules/posixmodule.py — os 모듈 (CPython 의 Modules/posixmodule.c)."""
import os as _o
from Objects.object import *
from Objects.moduleobject import ModuleDef, string

mod = ModuleDef('os')
mod.const('sep', _o.sep); mod.const('name', _o.name); mod.const('linesep', _o.linesep)


def _oserr(ip, ex): return ip.rt('IOError', '%s: %s' % (ex.strerror or ex, getattr(ex, 'filename', '') or ''))


@mod.fn(argc=0)
def getcwd(ip, args): return _o.getcwd()


@mod.fn(argc=(1, 2))
def getenv(ip, args):
    v = _o.environ.get(string(ip, args[0], 'os.getenv'))
    return v if v is not None else (args[1] if len(args) > 1 else None)


@mod.fn(argc=1)
def listdir(ip, args):
    try: return AList(sorted(_o.listdir(string(ip, args[0], 'os.listdir'))), T_STRING)
    except OSError as ex: raise _oserr(ip, ex)


@mod.fn(argc=1)
def exists(ip, args): return _o.path.exists(string(ip, args[0], 'os.exists'))


@mod.fn(argc=1)
def isfile(ip, args): return _o.path.isfile(string(ip, args[0], 'os.isfile'))


@mod.fn(argc=1)
def isdir(ip, args): return _o.path.isdir(string(ip, args[0], 'os.isdir'))


@mod.fn(argc=(1, 8))
def join(ip, args): return _o.path.join(*[string(ip, a, 'os.join') for a in args])


@mod.fn(argc=1)
def basename(ip, args): return _o.path.basename(string(ip, args[0], 'os.basename'))


@mod.fn(argc=1)
def dirname(ip, args): return _o.path.dirname(string(ip, args[0], 'os.dirname'))


@mod.fn(argc=1)
def splitext(ip, args): return tuple(_o.path.splitext(string(ip, args[0], 'os.splitext')))


@mod.fn(argc=1)
def remove(ip, args):
    try: _o.remove(string(ip, args[0], 'os.remove'))
    except OSError as ex: raise _oserr(ip, ex)


@mod.fn(argc=1)
def mkdir(ip, args):
    try: _o.makedirs(string(ip, args[0], 'os.mkdir'), exist_ok=True)
    except OSError as ex: raise _oserr(ip, ex)


@mod.fn(argc=0)
def cpu_count(ip, args): return _o.cpu_count() or 1


def init(ip): return mod.members
