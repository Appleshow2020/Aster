"""Objects/typeobject.py — 타입 추론·타입 강제(coerce)·제네릭 바인딩 (CPython 의 Objects/typeobject.c)."""
import sys, os, math, struct, functools, operator, gc
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from Python.state import state
from Python.errors import *
from Objects.object import *
from Objects.funcobject import *
from Objects.frameobject import *
from Objects.classobject import *


class TypeMixin:
    def type_of(s, v):
        t = type(v)
        if v is None: return T_NULL
        if t is bool: return T_BOOL
        if t is int: return T_INT if -2147483648 <= v <= 2147483647 else T_LONG
        if t is float: return T_DOUBLE
        if t is F32: return T_FLOAT
        if t is Decimal: return T_DECIMAL
        if t is str: return T_STRING
        if t is Char: return T_CHAR
        if t in (AList, AArray, ASet): return TypeRef({AList: 'list', AArray: 'array', ASet: 'set'}[t], [v.elem or T_UNK])
        if t is AMap: return TypeRef('map', [v.kt or T_UNK, v.vt or T_UNK])
        if t is tuple: return TypeRef('tuple', [s.type_of(x) for x in v])
        if isinstance(v, Instance): return TypeRef(v.cls.name, [], False, v.cls)
        if t is Rng: return TypeRef('range')
        if t in CALLABLES: return TypeRef('fn')
        if t is ClassObj: return TypeRef('class')
        return TypeRef('namespace')

    def common_type(s, vals):
        ts = []; has_null = False
        for x in vals:
            if x is None: has_null = True
            else: ts.append(s.type_of(x))
        if not ts: return None
        first = ts[0]
        for x in ts[1:]:
            if not s.same_type(first, x):
                raise s.rt('TypeError', '컬렉션 요소 타입이 서로 다릅니다: %s, %s' % (fmt(first), fmt(x)))
        if has_null: return TypeRef(first.name, first.args, True, first.cls)
        return first

    def infer_collection(s, v):
        t = type(v)
        if t in (AList, AArray, ASet):
            if v.elem is None:
                et = s.common_type(list(v))
                if et is None: raise s.rt('TypeError', '빈 컬렉션은 var 로 추론할 수 없습니다. 타입을 명시하세요')
                v.elem = et
        elif t is AMap and v.kt is None:
            kt = s.common_type(list(v.keys())); vt = s.common_type(list(v.values()))
            if kt is None or vt is None: raise s.rt('TypeError', '빈 맵은 var 로 추론할 수 없습니다. 타입을 명시하세요')
            v.kt = kt; v.vt = vt

    def same_type(s, a, b, tv=None):
        tv = s.tv if tv is None else tv

        def res(t):
            k = 0
            while t is not None and t.name in tv and k < 20:
                t = tv[t.name]; k += 1
            return t
        a = res(a); b = res(b)
        if a is None or b is None or a.name == '?' or b.name == '?': return True
        if a.name != b.name or a.nullable != b.nullable: return False
        if a.args and b.args:
            return len(a.args) == len(b.args) and all(s.same_type(x, y, tv) for x, y in zip(a.args, b.args))
        return True

    def bind_tv(s, t, vt, tv):
        if t.name in tv:
            if tv[t.name] is None and vt.name not in ('?', 'null'): tv[t.name] = TypeRef(vt.name, vt.args, False, vt.cls)
            return
        if t.args and vt.args and t.name == vt.name:
            for a, b in zip(t.args, vt.args): s.bind_tv(a, b, tv)

    def default_value(s, t):
        if t.nullable: return None
        n = t.name
        if n in ('int', 'long', 'byte'): return 0
        if n == 'double': return 0.0
        if n == 'float': return F32(0.0)
        if n == 'decimal': return Decimal(0)
        if n == 'bool': return False
        if n == 'char': return Char('\0')
        if n == 'string': return ''
        return NO_DEFAULT

    def lookup_class_opt(s, name, env):
        parts = name.split('.')
        slot = (env or s.glob).lookup(parts[0])
        if slot is None: slot = s.glob.lookup(parts[0])
        obj = slot[0] if slot else None
        for p in parts[1:]:
            if isinstance(obj, NamespaceObj):
                s2 = obj.env.vars.get(p); obj = s2[0] if s2 else None
            else: return None
        return obj if isinstance(obj, ClassObj) else None

    def lookup_class(s, name, env):
        c = s.lookup_class_opt(name, env)
        if c is None: raise s.rt('NameError', '알 수 없는 클래스/타입: ' + name)
        return c

    def coerce_fail(s, v, t):
        if type(v) is int and t.name in ('byte', 'int', 'long'):
            raise s.rt('TypeError', '값 %d 이(가) %s 범위를 벗어났습니다' % (v, t.name))
        raise s.rt('TypeError', '%s 타입이 필요하지만 %s 값이 주어졌습니다 (암시적 변환 없음 — cast<%s>(...) 사용)'
                   % (fmt(t), fmt(s.type_of(v)), t.name))

    def coerce(s, v, t, tv=None, env=None):
        name = t.name
        if name == 'var': return v
        if tv is None: tv = s.tv
        if name in tv:
            b = tv[name]
            if v is None:
                if t.nullable or b is None or b.nullable: return None
                raise s.rt('TypeError', 'null 은(는) %s 타입에 대입할 수 없습니다' % fmt(b))
            if b is None: return v
            return s.coerce(v, b, tv, env)
        if v is None:
            if t.nullable: return None
            raise s.rt('TypeError', "null 은(는) %s 타입에 대입할 수 없습니다 ('%s?' 처럼 nullable 로 선언하세요)" % (fmt(t), t.name))
        chk = PRIM.get(name)
        if chk is not None:
            if chk(v): return v
            s.coerce_fail(v, t)
        if name in COLL: return s.coerce_coll(v, t, tv, env)
        if name == 'fn':
            if v.__class__ in CALLABLES: return v
            s.coerce_fail(v, t)
        if name == 'tuple':
            if type(v) is not tuple: s.coerce_fail(v, t)
            if t.args:
                if len(t.args) != len(v): raise s.rt('TypeError', '튜플 길이가 다릅니다')
                return tuple(s.coerce(x, ta, tv, env) for x, ta in zip(v, t.args))
            return v
        cls = t.cls
        if cls is None:
            cls = s.lookup_class_opt(name, env)
            if cls is None: raise s.rt('NameError', '알 수 없는 타입: ' + name)
            t.cls = cls
        if isinstance(v, Instance) and cls in v.cls.all_types: return v
        s.coerce_fail(v, t)

    def coerce_coll(s, v, t, tv, env):
        name = t.name
        want = {'list': AList, 'array': AArray, 'set': ASet, 'map': AMap}[name]
        if type(v) is not want:
            if name == 'array' and type(v) is AList and v.lit:
                nv = AArray(v); v = nv
            elif name == 'set' and type(v) is AMap and v.lit and not v:
                v = ASet()
            else: s.coerce_fail(v, t)
        if not t.args: return v
        if name == 'map':
            kt, vt = t.args
            if v.kt is None:
                items = list(v.items()); v.clear()
                for k, x in items: v[s.coerce(k, kt, tv, env)] = s.coerce(x, vt, tv, env)
                v.kt = kt; v.vt = vt
            elif not (s.same_type(v.kt, kt, tv) and s.same_type(v.vt, vt, tv)):
                raise s.rt('TypeError', '%s 타입이 필요하지만 %s 값이 주어졌습니다' % (fmt(t), fmt(s.type_of(v))))
        else:
            te = t.args[0]
            if v.elem is None:
                items = [s.coerce(x, te, tv, env) for x in v]
                if name == 'set':
                    v.clear()
                    for x in items: v[x] = True
                else: v[:] = items
                v.elem = te
            elif not s.same_type(v.elem, te, tv):
                raise s.rt('TypeError', '%s 타입이 필요하지만 %s 값이 주어졌습니다' % (fmt(t), fmt(s.type_of(v))))
        v.lit = False
        return v

    def is_instance(s, v, t, env):
        if t is None: return v is None
        if v is None: return t.nullable
        n = t.name
        chk = PRIM.get(n)
        if chk is not None: return chk(v)
        if n == 'list': return type(v) is AList and (not t.args or v.elem is None or s.same_type(v.elem, t.args[0]))
        if n == 'array': return type(v) is AArray
        if n == 'set': return type(v) is ASet
        if n == 'map': return type(v) is AMap
        if n == 'tuple': return type(v) is tuple
        if n == 'fn': return v.__class__ in CALLABLES
        if n in s.tv:
            b = s.tv[n]
            return True if b is None else s.is_instance(v, b, env)
        cls = t.cls or s.lookup_class_opt(n, env)
        if cls is None: raise s.rt('NameError', '알 수 없는 타입: ' + n)
        return isinstance(v, Instance) and cls in v.cls.all_types
