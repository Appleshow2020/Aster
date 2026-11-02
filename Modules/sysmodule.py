"""Modules/sysmodule.py — sys 모듈 (CPython 의 Python/sysmodule.c)."""
import sys as _s
from Objects.object import *
from Objects.moduleobject import ModuleDef, string, integer
from Python.errors import ExitProgram

mod = ModuleDef('sys')
mod.const('platform', _s.platform); mod.const('version', '0.4'); mod.const('maxsize', 2 ** 63 - 1)
mod.const('executable', _s.executable); mod.const('byteorder', _s.byteorder)


@mod.fn(argc=(0, 1))
def exit_(ip, args): raise ExitProgram(integer(ip, args[0], 'sys.exit') if args else 0)


@mod.fn(argc=1)
def stdout_write(ip, args): _s.stdout.write(ip.to_str(args[0]))


@mod.fn(argc=1)
def stderr_write(ip, args): _s.stderr.write(ip.to_str(args[0]))


@mod.fn(argc=0)
def stdin_readline(ip, args): return _s.stdin.readline()


@mod.fn(argc=0)
def modules(ip, args): return AList(sorted(ip.modules), T_STRING)


def init(ip):
    members = dict(mod.members)
    members['argv'] = ip.argv; members['path'] = ip.path
    return members
