"""Python/bltinmodule.py — 내장 함수와 내장 타입 메서드 (CPython 의 Python/bltinmodule.c)."""
import sys, os, math, struct, functools, operator, gc
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from Python.state import state
from Python.errors import *
from Objects.object import *
from Objects.funcobject import *
from Objects.frameobject import *
from Objects.classobject import *


class BuiltinsMixin:
    def new_builtin(s, t, args, env):
        n = t.name; te = t.args[0] if t.args else None
        if n == 'map':
            m = AMap()
            if len(t.args) == 2: m.kt, m.vt = t.args
            if args: raise s.rt('TypeError', 'new map 은 인자를 받지 않습니다')
            return m
        if n == 'array':
            if not args or type(args[0]) is not int or args[0] < 0:
                raise s.rt('TypeError', 'new array<T>(크기[, 채움값]) 형식이어야 합니다')
            if len(args) > 1: fill = args[1]
            else:
                fill = s.default_value(te) if te else None
                if fill is NO_DEFAULT: raise s.rt('TypeError', '이 타입에는 기본값이 없습니다. 채움값을 지정하세요')
            if te is not None: fill = s.coerce(fill, te, None, env)
            return AArray([fill] * args[0], te)
        items = s.iter_values(args[0]) if args else []
        if te is not None: items = [s.coerce(x, te, None, env) for x in items]
        return AList(items, te) if n == 'list' else ASet(items, te)

    def do_cast(s, v, t, env):
        n = t.name; nl = t.nullable

        def fail(msg):
            if nl: return None
            raise s.rt('ValueError', msg)
        if v is None: return None if nl else fail('null 은(는) 변환할 수 없습니다')
        k = KIND.get(type(v))
        try:
            if n in ('int', 'long', 'byte'):
                if k == 'int': x = v
                elif k in ('double', 'float'):
                    if v != v or v in (math.inf, -math.inf): return fail('NaN/무한대는 정수로 변환할 수 없습니다')
                    x = int(v)
                elif k == 'decimal': x = int(v)
                elif k == 'char': x = ord(v.c)
                elif k == 'string': x = int(v.strip())
                else: return fail('%s 을(를) %s 로 변환할 수 없습니다' % (fmt(s.type_of(v)), n))
                if not PRIM[n](x): return fail('값 %d 이(가) %s 범위를 벗어났습니다' % (x, n))
                return x
            if n in ('double', 'float'):
                if k in ('int', 'double', 'float', 'decimal'): x = float(v)
                elif k == 'string': x = float(v.strip())
                else: return fail('%s 을(를) %s 로 변환할 수 없습니다' % (fmt(s.type_of(v)), n))
                return x if n == 'double' else mkf32(x)
            if n == 'decimal':
                if k == 'int': return Decimal(v)
                if k == 'double': return Decimal(repr(v))
                if k == 'float': return Decimal(f32str(v))
                if k == 'decimal': return v
                if k == 'string': return Decimal(v.strip())
                return fail('%s 을(를) decimal 로 변환할 수 없습니다' % fmt(s.type_of(v)))
            if n == 'string': return s.to_str(v)
            if n == 'char':
                if k == 'char': return v
                if k == 'int': return Char(chr(v))
                if k == 'string' and len(v) == 1: return Char(v)
                return fail('%s 을(를) char 로 변환할 수 없습니다' % fmt(s.type_of(v)))
            if n == 'bool':
                if k == 'bool': return v
                if k == 'string' and v in ('true', 'false'): return v == 'true'
                return fail('%s 을(를) bool 로 변환할 수 없습니다' % fmt(s.type_of(v)))
        except (ValueError, InvalidOperation, OverflowError):
            return fail('%s 을(를) %s 로 변환할 수 없습니다' % (s.to_str(v, True), n))
        if s.is_instance(v, TypeRef(n, t.args, False, t.cls), env): return v
        return fail('%s 을(를) %s 로 변환할 수 없습니다' % (fmt(s.type_of(v)), fmt(t)))

    def builtin_member(s, o, name):
        t = type(o)
        if name == 'length':
            if t in (AList, AArray, tuple, str, ASet, AMap): return len(o)
            if t is Rng: return max(0, o.b - o.a)
        if t is Rng and name in ('start', 'end'): return o.a if name == 'start' else o.b
        tbl = s.METHODS.get(t)
        f = tbl.get(name) if tbl else None
        if f is None and name == 'toString': f = lambda it, ob, a: it.to_str(ob)
        if f is None: raise s.rt('NameError', "%s 에는 '%s' 멤버가 없습니다" % (fmt(s.type_of(o)), name))
        return Builtin(name, lambda it, a, f=f, o=o: f(it, o, a))

    def sort_list(s, lst):
        def cmp(x, y):
            if s.compare('<', x, y): return -1
            if s.compare('<', y, x): return 1
            return 0
        lst.sort(key=functools.cmp_to_key(cmp))

    def install_builtins(s):
        def ce(o, x):
            return s.coerce(x, o.elem) if o.elem is not None else x

        def mapped(it, o, a):
            r = AList([it.call(a[0], [x]) for x in s.iter_values(o)])
            r.elem = s.common_type(list(r)) if r else None
            return r

        def lremove(it, o, a):
            for i, y in enumerate(o):
                if it.eq(a[0], y): del o[i]; return True
            return False

        def lindex(it, o, a):
            for i, y in enumerate(o):
                if it.eq(a[0], y): return i
            return -1

        def lpop(it, o, a):
            if not o: raise it.rt('IndexError', '빈 리스트에서 pop 할 수 없습니다')
            return o.pop()

        def linsert(it, o, a):
            if type(a[0]) is not int or a[0] < 0 or a[0] > len(o): raise it.rt('IndexError', '삽입 위치가 범위를 벗어났습니다')
            o.insert(a[0], ce(o, a[1]))

        def lremoveat(it, o, a):
            if type(a[0]) is not int or a[0] < 0 or a[0] >= len(o): raise it.rt('IndexError', '인덱스가 범위를 벗어났습니다')
            return o.pop(a[0])

        def reduce_(it, o, a):
            acc = a[1]
            for x in s.iter_values(o): acc = it.call(a[0], [acc, x])
            return acc

        def foreach(it, o, a):
            for x in s.iter_values(o): it.call(a[0], [x])

        def join(it, o, a):
            return (a[0] if a else '').join(it.to_str(x) for x in s.iter_values(o))

        def sort_(it, o, a): it.sort_list(o)

        def rev(it, o, a): o.reverse()

        def mget(it, o, a):
            if a[0] in o: return o[a[0]]
            return a[1] if len(a) > 1 else None

        def mremove(it, o, a):
            if a[0] in o: del o[a[0]]; return True
            return False

        def sadd(it, o, a):
            x = ce(o, a[0])
            if x in o: return False
            o[x] = True; return True

        def sremove(it, o, a):
            if a[0] in o: del o[a[0]]; return True
            return False

        def split(it, o, a):
            parts = o.split(txt(a[0])) if a else o.split()
            return AList(parts, T_STRING)

        def substring(it, o, a):
            i = a[0]; j = a[1] if len(a) > 1 else len(o)
            if type(i) is not int or type(j) is not int or i < 0 or j > len(o) or i > j: raise it.rt('IndexError', 'substring 범위 오류')
            return o[i:j]

        listm = {
            'add': lambda it, o, a: o.append(ce(o, a[0])), 'insert': linsert, 'remove': lremove, 'removeAt': lremoveat,
            'pop': lpop, 'contains': lambda it, o, a: it.contains(o, a[0]), 'indexOf': lindex,
            'clear': lambda it, o, a: o.clear(), 'sort': sort_, 'reverse': rev, 'join': join,
            'copy': lambda it, o, a: AList(o, o.elem), 'map': mapped,
            'filter': lambda it, o, a: AList([x for x in o if it.cond(it.call(a[0], [x]))], o.elem),
            'reduce': reduce_, 'forEach': foreach,
            'any': lambda it, o, a: any(it.cond(it.call(a[0], [x])) for x in o),
            'all': lambda it, o, a: all(it.cond(it.call(a[0], [x])) for x in o),
        }
        arrm = {'contains': listm['contains'], 'indexOf': lindex, 'sort': sort_, 'reverse': rev, 'join': join,
                'copy': lambda it, o, a: AArray(o, o.elem), 'map': mapped, 'forEach': foreach,
                'toList': lambda it, o, a: AList(o, o.elem)}
        setm = {'add': sadd, 'has': lambda it, o, a: a[0] in o, 'contains': lambda it, o, a: a[0] in o,
                'remove': sremove, 'clear': lambda it, o, a: o.clear(),
                'toList': lambda it, o, a: AList(list(o), o.elem), 'forEach': foreach}
        mapm = {'has': lambda it, o, a: a[0] in o, 'containsKey': lambda it, o, a: a[0] in o, 'get': mget,
                'keys': lambda it, o, a: AList(list(o.keys()), o.kt),
                'values': lambda it, o, a: AList(list(o.values()), o.vt),
                'items': lambda it, o, a: AList([(k, v) for k, v in o.items()]),
                'remove': mremove, 'clear': lambda it, o, a: o.clear()}
        strm = {
            'upper': lambda it, o, a: o.upper(), 'lower': lambda it, o, a: o.lower(), 'trim': lambda it, o, a: o.strip(),
            'split': split, 'contains': lambda it, o, a: txt(a[0]) in o,
            'startsWith': lambda it, o, a: o.startswith(txt(a[0])), 'endsWith': lambda it, o, a: o.endswith(txt(a[0])),
            'replace': lambda it, o, a: o.replace(txt(a[0]), txt(a[1])), 'indexOf': lambda it, o, a: o.find(txt(a[0])),
            'substring': substring,
            'join': lambda it, o, a: o.join(it.to_str(x) for x in s.iter_values(a[0])),
            'chars': lambda it, o, a: AList([Char(c) for c in o], T_CHAR),
        }
        s.METHODS = {str: strm, AList: listm, AArray: arrm, ASet: setm, AMap: mapm,
                     Rng: {'toList': lambda it, o, a: AList(range(o.a, o.b), T_INT),
                           'forEach': foreach, 'map': mapped}}
        g = s.root.vars

        def reg(name, fn): g[name] = [Builtin(name, fn), TypeRef('fn'), True]

        def b_print(it, a):
            sys.stdout.write(' '.join(it.to_str(x) for x in a) + '\n')

        def b_input(it, a):
            if a: sys.stdout.write(it.to_str(a[0])); sys.stdout.flush()
            return sys.stdin.readline().rstrip('\r\n')

        def b_len(it, a):
            return it.builtin_member(a[0], 'length')

        def num(it, v, nm):
            if KIND.get(type(v)) not in NUMERIC: raise it.rt('TypeError', '%s: 숫자가 필요합니다' % nm)
            return v

        def b_sqrt(it, a):
            x = float(num(it, a[0], 'sqrt'))
            if x < 0: raise it.rt('ValueError', 'sqrt: 음수는 사용할 수 없습니다')
            return math.sqrt(x)

        def pick(name, better):
            def f(it, a):
                items = it.iter_values(a[0]) if len(a) == 1 else a
                if not items: raise it.rt('ValueError', '%s: 값이 없습니다' % name)
                best = items[0]
                for x in items[1:]:
                    if it.compare(better, x, best): best = x
                return best
            return f

        def b_exit(it, a): raise ExitProgram(a[0] if a else 0)

        def b_assert(it, a):
            if not it.cond(a[0]): raise it.rt('RuntimeError', '단언 실패' + (': ' + it.to_str(a[1]) if len(a) > 1 else ''))

        reg('print', b_print); reg('input', b_input); reg('str', lambda it, a: it.to_str(a[0]))
        reg('len', b_len); reg('typeof', lambda it, a: fmt(it.type_of(a[0])))
        reg('abs', lambda it, a: abs(num(it, a[0], 'abs'))); reg('sqrt', b_sqrt)
        reg('min', pick('min', '<')); reg('max', pick('max', '>'))
        reg('floor', lambda it, a: math.floor(num(it, a[0], 'floor'))); reg('ceil', lambda it, a: math.ceil(num(it, a[0], 'ceil')))
        reg('round', lambda it, a: int(math.floor(num(it, a[0], 'round') + 0.5)))
        reg('exit', b_exit); reg('assert', b_assert)
