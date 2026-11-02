"""Modules/timemodule.py — time 모듈 (CPython 의 Modules/timemodule.c)."""
import time as _t
from Objects.object import *
from Objects.moduleobject import ModuleDef, number, string

mod = ModuleDef('time')


@mod.fn(argc=0)
def time(ip, args): return _t.time()


@mod.fn(argc=0)
def perf_counter(ip, args): return _t.perf_counter()


@mod.fn(argc=0)
def monotonic(ip, args): return _t.monotonic()


@mod.fn(argc=1)
def sleep(ip, args):
    x = float(number(ip, args[0], 'time.sleep'))
    if x < 0: raise ip.rt('ValueError', 'time.sleep: 음수는 사용할 수 없습니다')
    _t.sleep(x)


@mod.fn(argc=(0, 1))
def ctime(ip, args): return _t.ctime(float(number(ip, args[0], 'time.ctime')) if args else None)


@mod.fn(argc=1)
def strftime(ip, args): return _t.strftime(string(ip, args[0], 'time.strftime'))


def init(ip): return mod.members
