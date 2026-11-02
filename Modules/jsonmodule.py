"""Modules/jsonmodule.py — json 모듈 (CPython 의 Modules/_json.c). dumps/loads."""
import json as _j
from decimal import Decimal
from Objects.object import *
from Objects.classobject import Instance
from Objects.moduleobject import ModuleDef, string, integer

mod = ModuleDef('json')


def to_py(ip, v):
    t = type(v)
    if v is None or t in (bool, int, float, str): return v
    if t is F32: return float(v)
    if t is Decimal: return float(v)
    if t is Char: return v.c
    if t in (AList, AArray, tuple, ASet): return [to_py(ip, x) for x in (list(v.keys()) if t is ASet else v)]
    if t is AMap:
        for k in v:
            if type(k) is not str: raise ip.rt('TypeError', 'json.dumps: map 의 키는 string 이어야 합니다')
        return {k: to_py(ip, x) for k, x in v.items()}
    raise ip.rt('TypeError', 'json.dumps: %s 값은 직렬화할 수 없습니다' % fmt(ip.type_of(v)))


def from_py(v):
    if isinstance(v, dict):
        m = AMap(); m.kt = T_STRING; m.vt = T_OBJECT
        for k, x in v.items(): m[k] = from_py(x)
        return m
    if isinstance(v, list): return AList([from_py(x) for x in v], T_OBJECT)
    return v


@mod.fn(argc=(1, 2))
def dumps(ip, args):
    ind = integer(ip, args[1], 'json.dumps') if len(args) > 1 else None
    return _j.dumps(to_py(ip, args[0]), ensure_ascii=False, indent=ind)


@mod.fn(argc=1)
def loads(ip, args):
    try: return from_py(_j.loads(string(ip, args[0], 'json.loads')))
    except _j.JSONDecodeError as ex: raise ip.rt('ValueError', 'json.loads: ' + str(ex))


def init(ip): return mod.members
