"""Modules/mathmodule.py — math 모듈 (CPython 의 Modules/mathmodule.c). 숫자 인자를 받아 double 을 돌려준다."""
import math as _m
from Objects.object import *
from Objects.moduleobject import ModuleDef, number, integer

mod = ModuleDef('math')
mod.const('pi', _m.pi); mod.const('e', _m.e); mod.const('tau', _m.tau)
mod.const('inf', _m.inf); mod.const('nan', _m.nan)


def _unary(name, pyfn):
    def f(ip, args):
        x = float(number(ip, args[0], 'math.' + name))
        try: return float(pyfn(x))
        except (ValueError, OverflowError) as ex:
            raise ip.rt('ValueError', 'math.%s: 정의역 오류 (%s)' % (name, ex))
    mod.fn(name, argc=1)(f)


for _n in ('sqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'exp', 'log2', 'log10', 'sinh', 'cosh', 'tanh',
           'degrees', 'radians', 'fabs'):
    _unary(_n, getattr(_m, _n))


@mod.fn(argc=(1, 2))
def log(ip, args):
    x = float(number(ip, args[0], 'math.log'))
    try: return _m.log(x) if len(args) == 1 else _m.log(x, float(number(ip, args[1], 'math.log')))
    except (ValueError, ZeroDivisionError): raise ip.rt('ValueError', 'math.log: 정의역 오류')


@mod.fn(argc=2)
def atan2(ip, args): return _m.atan2(float(number(ip, args[0], 'math.atan2')), float(number(ip, args[1], 'math.atan2')))


@mod.fn(argc=2)
def hypot(ip, args): return _m.hypot(float(number(ip, args[0], 'math.hypot')), float(number(ip, args[1], 'math.hypot')))


@mod.fn(argc=2)
def pow(ip, args):
    try: return float(_m.pow(float(number(ip, args[0], 'math.pow')), float(number(ip, args[1], 'math.pow'))))
    except (ValueError, OverflowError): raise ip.rt('ValueError', 'math.pow: 정의역 오류')


@mod.fn(argc=1)
def floor(ip, args): return _m.floor(number(ip, args[0], 'math.floor'))


@mod.fn(argc=1)
def ceil(ip, args): return _m.ceil(number(ip, args[0], 'math.ceil'))


@mod.fn(argc=1)
def trunc(ip, args): return _m.trunc(number(ip, args[0], 'math.trunc'))


@mod.fn(argc=1)
def isnan(ip, args): return _m.isnan(float(number(ip, args[0], 'math.isnan')))


@mod.fn(argc=1)
def isinf(ip, args): return _m.isinf(float(number(ip, args[0], 'math.isinf')))


@mod.fn(argc=2)
def gcd(ip, args): return _m.gcd(integer(ip, args[0], 'math.gcd'), integer(ip, args[1], 'math.gcd'))


@mod.fn(argc=1)
def factorial(ip, args):
    n = integer(ip, args[0], 'math.factorial')
    if n < 0 or n > 5000: raise ip.rt('ValueError', 'math.factorial: 0..5000 범위여야 합니다')
    return _m.factorial(n)


def init(ip): return mod.members
