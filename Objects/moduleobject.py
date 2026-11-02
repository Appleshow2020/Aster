"""Objects/moduleobject.py — 모듈 객체와 네이티브 모듈 정의 도우미 (CPython 의 Objects/moduleobject.c + PyMethodDef 테이블).

네이티브 모듈(Modules/*.py)은 다음처럼 작성한다.

    mod = ModuleDef('math')
    @mod.fn()
    def sqrt(ip, args): ...
    mod.const('pi', 3.14159)
    def init(ip): return mod.members
"""
from Objects.object import *
from Objects.funcobject import Builtin
from Objects.frameobject import Env
from Objects.classobject import NamespaceObj


class ModuleDef:
    def __init__(s, name):
        s.name = name; s.members = {}

    def fn(s, name=None, argc=None):
        def deco(f):
            nm = name or f.__name__.rstrip('_')
            if argc is None: s.members[nm] = Builtin(s.name + '.' + nm, f)
            else:
                lo, hi = argc if isinstance(argc, tuple) else (argc, argc)

                def checked(ip, args, f=f, nm=nm):
                    if len(args) < lo or len(args) > hi:
                        want = str(lo) if lo == hi else '%d~%d' % (lo, hi)
                        raise ip.rt('TypeError', '%s.%s: 인자 %s개가 필요합니다 (전달 %d개)' % (s.name, nm, want, len(args)))
                    return f(ip, args)
                s.members[nm] = Builtin(s.name + '.' + nm, checked)
            return f
        return deco

    def const(s, name, value): s.members[name] = value


def make_module(name, members, path=None):
    ns = NamespaceObj(name, Env()); ns.is_module = True; ns.path = path
    for k, v in members.items():
        ns.env.vars[k] = [v, None, True]
    return ns


def number(ip, v, where):
    if KIND.get(type(v)) not in NUMERIC:
        raise ip.rt('TypeError', '%s: 숫자가 필요하지만 %s 값이 주어졌습니다' % (where, fmt(ip.type_of(v))))
    return v


def string(ip, v, where):
    if type(v) is not str:
        raise ip.rt('TypeError', '%s: string 이 필요하지만 %s 값이 주어졌습니다' % (where, fmt(ip.type_of(v))))
    return v


def integer(ip, v, where):
    if type(v) is not int:
        raise ip.rt('TypeError', '%s: int 가 필요하지만 %s 값이 주어졌습니다' % (where, fmt(ip.type_of(v))))
    return v
