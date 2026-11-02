"""Python/ceval.py — 식 평가 루프와 함수 호출 (CPython 의 Python/ceval.c)."""
import sys, os, math, struct, functools, operator, gc
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from Python.state import state
from Python.errors import *
from Objects.object import *
from Objects.funcobject import *
from Objects.frameobject import *
from Objects.classobject import *
from Parser.ast import *


class EvalMixin:
    def e_name(s, n, env):
        nm = n.name; e = env
        while e is not None:
            v = e.vars.get(nm)
            if v is not None: return v[0]
            e = e.parent
        raise s.rt('NameError', '정의되지 않은 이름: ' + nm)

    def e_this(s, n, env):
        v = env.lookup('this')
        if v is None: raise s.rt('NameError', "'this' 는 인스턴스 메서드 안에서만 사용할 수 있습니다")
        return v[0]

    def e_list(s, n, env):
        return AList([s.ev(i, env) for i in n.items], None, True)

    def e_tuple(s, n, env):
        return tuple(s.ev(i, env) for i in n.items)

    def e_set(s, n, env):
        r = ASet([], None, True)
        for i in n.items:
            x = s.ev(i, env)
            try: r[x] = True
            except TypeError: raise s.rt('TypeError', '해시할 수 없는 값은 set 에 넣을 수 없습니다')
        return r

    def e_map(s, n, env):
        m = AMap(); m.lit = True
        for k, v in n.pairs:
            kk = s.ev(k, env)
            try: m[kk] = s.ev(v, env)
            except TypeError: raise s.rt('TypeError', '해시할 수 없는 값은 map 키가 될 수 없습니다')
        return m

    def e_unary(s, n, env):
        v = s.ev(n.e, env); op = n.op
        if op == 'not':
            if v is True: return False
            if v is False: return True
            raise s.rt('TypeError', "'!'/'not' 은(는) bool 에만 사용할 수 있습니다")
        if isinstance(v, Instance):
            m = s.find_member(v.cls, 'operator' + op)
            if m: return s.call_function(m[0].func, [], v)
        k = KIND.get(type(v))
        if k not in NUMERIC: raise s.rt('TypeError', "단항 '%s' 을(를) %s 에 적용할 수 없습니다" % (op, fmt(s.type_of(v))))
        return -v if op == '-' else v

    def e_binary(s, n, env):
        a = s.ev(n.l, env); b = s.ev(n.r, env); op = n.op
        if a.__class__ is int and b.__class__ is int:
            if op == '+': return a + b
            if op == '-': return a - b
            if op == '*': return a * b
            if op == '<': return a < b
            if op == '>': return a > b
            if op == '==': return a == b
            if op == '<=': return a <= b
            if op == '>=': return a >= b
            if op == '!=': return a != b
        s.line = n.line
        return s.binop(op, a, b)

    def e_logic(s, n, env):
        a = s.cond(s.ev(n.l, env))
        if n.op == 'and':
            return s.cond(s.ev(n.r, env)) if a else False
        return True if a else s.cond(s.ev(n.r, env))

    def e_coal(s, n, env):
        a = s.ev(n.l, env)
        return a if a is not None else s.ev(n.r, env)

    def e_pipe(s, n, env):
        x = s.ev(n.l, env); r = n.r
        if r.__class__ is Call:
            f = s.ev(r.fn, env)
            return s.call(f, [x] + [s.ev(a, env) for a in r.args], r.targs)
        return s.call(s.ev(r, env), [x])

    def e_range(s, n, env):
        a = s.ev(n.l, env); b = s.ev(n.r, env)
        if type(a) is not int or type(b) is not int: raise s.rt('TypeError', "범위(..)의 양끝은 정수여야 합니다")
        return Rng(a, b)

    def e_is(s, n, env):
        r = s.is_instance(s.ev(n.e, env), n.ty, env)
        return (not r) if n.neg else r

    def e_in(s, n, env):
        x = s.ev(n.e, env); c = s.ev(n.c, env)
        r = s.contains(c, x)
        return (not r) if n.neg else r

    def e_chain(s, n, env):
        try: return s.ev(n.e, env)
        except ShortCircuit: return None

    def e_lambda(s, n, env):
        return Function(name='<lambda>', params=n.params, rtype=n.rtype, body=n.body, expr=n.expr, env=env,
                        tparams=[], owner=s.ctx_cls, file=s.ctx_file, tv=s.tv, is_lambda=True)

    def e_call(s, n, env):
        f = s.ev(n.fn, env)
        args = [s.ev(a, env) for a in n.args]
        s.line = n.line
        return s.call(f, args, n.targs)

    def e_new(s, n, env):
        t = n.ty; args = [s.ev(a, env) for a in n.args]
        s.line = n.line
        if t.name in COLL and env.lookup(t.name) is None: return s.new_builtin(t, args, env)
        cls = s.lookup_class(t.name, env)
        return s.instantiate(cls, args, t.args)

    def e_cast(s, n, env):
        return s.do_cast(s.ev(n.e, env), n.ty, env)

    def e_member(s, n, env):
        o = n.obj
        if o.__class__ is SuperN: return s.super_member(o, n.name, env)
        obj = s.ev(o, env)
        if obj is None:
            if n.safe: raise ShortCircuit
            raise s.rt('NullError', "null 값의 멤버 '%s' 에 접근할 수 없습니다" % n.name)
        s.line = n.line
        return s.get_member(obj, n.name)

    def e_index(s, n, env):
        obj = s.ev(n.obj, env); idx = s.ev(n.idx, env)
        s.line = n.line
        return s.get_index(obj, idx)

    def e_assign(s, n, env):
        t = n.target; op = n.op; c = t.__class__
        if c is Name:
            slot = env.lookup(t.name)
            if slot is None: raise s.rt('NameError', '정의되지 않은 이름: ' + t.name)
            if slot[2]: raise s.rt('TypeError', "상수 '%s' 에는 대입할 수 없습니다" % t.name)
            if op == '=': v = s.ev(n.value, env)
            elif op == '??=':
                if slot[0] is not None: return slot[0]
                v = s.ev(n.value, env)
            else:
                r = s.ev(n.value, env); s.line = n.line
                v = s.binop(op[:-1], slot[0], r)
            if slot[1] is not None: v = s.coerce(v, slot[1], None, env)
            slot[0] = v
            return v
        if c is Member:
            obj = s.ev(t.obj, env)
            if obj is None: raise s.rt('NullError', "null 값의 멤버 '%s' 에 대입할 수 없습니다" % t.name)
            if op == '=': v = s.ev(n.value, env)
            else:
                cur = s.get_member(obj, t.name)
                if op == '??=':
                    if cur is not None: return cur
                    v = s.ev(n.value, env)
                else:
                    r = s.ev(n.value, env); s.line = n.line
                    v = s.binop(op[:-1], cur, r)
            s.line = n.line
            s.set_member(obj, t.name, v)
            return v
        obj = s.ev(t.obj, env); idx = s.ev(t.idx, env)
        if op == '=': v = s.ev(n.value, env)
        else:
            cur = s.get_index(obj, idx)
            if op == '??=':
                if cur is not None: return cur
                v = s.ev(n.value, env)
            else:
                r = s.ev(n.value, env); s.line = n.line
                v = s.binop(op[:-1], cur, r)
        s.line = n.line
        s.set_index(obj, idx, v)
        return v

    def get_index(s, o, i):
        t = type(o)
        if t in (AList, AArray, tuple, str):
            if type(i) is Rng:
                r = o[i.a:i.b]
                if t is AList: return AList(r, o.elem)
                if t is AArray: return AArray(r, o.elem)
                return r
            if type(i) is not int: raise s.rt('TypeError', '인덱스는 int 여야 합니다')
            if i < 0 or i >= len(o): raise s.rt('IndexError', '인덱스 %d 이(가) 범위를 벗어났습니다 (길이 %d)' % (i, len(o)))
            return Char(o[i]) if t is str else o[i]
        if t is AMap:
            try:
                if i in o: return o[i]
            except TypeError: raise s.rt('TypeError', '해시할 수 없는 키입니다')
            raise s.rt('KeyError', '키가 없습니다: ' + s.to_str(i, True))
        if o is None: raise s.rt('NullError', 'null 값은 인덱싱할 수 없습니다')
        raise s.rt('TypeError', '%s 은(는) 인덱싱할 수 없습니다' % fmt(s.type_of(o)))

    def set_index(s, o, i, v):
        t = type(o)
        if t in (AList, AArray):
            if type(i) is not int: raise s.rt('TypeError', '인덱스는 int 여야 합니다')
            if i < 0 or i >= len(o): raise s.rt('IndexError', '인덱스 %d 이(가) 범위를 벗어났습니다 (길이 %d)' % (i, len(o)))
            if o.elem is not None: v = s.coerce(v, o.elem)
            o[i] = v; return
        if t is AMap:
            if o.kt is not None: i = s.coerce(i, o.kt); v = s.coerce(v, o.vt)
            elif not o:
                o.kt = s.type_of(i); o.vt = s.type_of(v)
            try: o[i] = v
            except TypeError: raise s.rt('TypeError', '해시할 수 없는 키입니다')
            return
        raise s.rt('TypeError', '%s 은(는) 인덱스 대입을 지원하지 않습니다' % fmt(s.type_of(o)))

    def call(s, f, args, targs=None):
        c = f.__class__
        if c is Function: return s.call_function(f, args, None, targs)
        if c is BoundMethod: return s.call_function(f.func, args, f.this, targs)
        if c is Builtin:
            try: return f.fn(s, args)
            except (IndexError, TypeError, ValueError, AttributeError) as ex:
                raise s.rt('TypeError', '%s: 잘못된 인자입니다 (%s)' % (f.name, ex))
        if c is ClassObj: raise s.rt('TypeError', "클래스는 직접 호출할 수 없습니다. 'new %s(...)' 를 사용하세요" % f.name)
        raise s.rt('TypeError', '호출할 수 없는 값입니다: ' + s.to_str(f, True))

    def bind_params(s, f, env, args, tv):
        ps = f.params; n = len(ps); na = len(args)
        if na > n: raise s.rt('TypeError', "%s: 인자가 너무 많습니다 (최대 %d개, 전달 %d개)" % (f.name, n, na))
        vs = env.vars
        for i, p in enumerate(ps):
            if i < na: v = args[i]
            elif p.default is not None: v = s.ev(p.default, env)
            else: raise s.rt('TypeError', "%s: 인자 '%s' 이(가) 필요합니다" % (f.name, p.name))
            t = p.ty
            if t is not None and t.name != 'var':
                if tv and v is not None: s.bind_tv(t, s.type_of(v), tv)
                v = s.coerce(v, t, tv, f.env)
            else: t = None
            vs[p.name] = [v, t, False]

    def check_bounds(s, f, tv):
        for nm, bound in f.tparams:
            b = tv.get(nm)
            if bound is None or b is None or bound.name == 'object': continue
            bc = s.lookup_class(bound.name, f.env)
            c = b.cls or s.lookup_class_opt(b.name, f.env)
            if c is None or bc not in c.all_types:
                raise s.rt('TypeError', "타입 인자 %s 은(는) 제약 %s 를 만족하지 않습니다" % (fmt(b), bound.name))

    def call_function(s, f, args, this=None, targs=None):
        if s.depth > 2500: raise s.rt('RuntimeError', '호출 깊이 초과 (재귀가 너무 깊습니다)')
        env = Env(f.env)
        if this is not None: env.vars['this'] = [this, None, True]
        tv = dict(f.tv) if f.tv else {}
        if this is not None and this.cls.tparams:
            for tp in this.cls.tparams: tv[tp] = this.targs.get(tp)
        for i, (nm, bd) in enumerate(f.tparams):
            tv[nm] = targs[i] if targs and i < len(targs) else None
        saved = (s.ctx_cls, s.ctx_file, s.tv)
        s.ctx_cls = f.owner; s.ctx_file = f.file; s.tv = tv; s.depth += 1
        try:
            s.bind_params(f, env, args, tv)
            if f.tparams: s.check_bounds(f, tv)
            if f.expr is not None: res = s.ev(f.expr, env)
            else:
                b = f.body
                if b.fns or b.classes: s.hoist(b, env)
                r = s.exec_stmts(b.stmts, env)
                res = r[1] if (r is not None and r[0] == 'return') else None
            return s.finish_return(f, res, env, tv)
        finally:
            s.ctx_cls, s.ctx_file, s.tv = saved; s.depth -= 1

    def finish_return(s, f, res, env, tv):
        rt = f.rtype
        if rt is not None:
            if rt.name == 'void':
                if res is not None: raise s.rt('TypeError', "void 함수 '%s' 는 값을 반환할 수 없습니다" % f.name)
                return None
            return s.coerce(res, rt, tv, f.env)
        if f.is_lambda: return res
        inf = f.inferred
        if inf is None:
            if res is None: f.inferred = 'void'
            else:
                t = s.type_of(res)
                f.inferred = TypeRef(t.name, [], False, t.cls)
            return res
        if inf == 'void':
            if res is not None: raise s.rt('TypeError', "함수 '%s' 의 반환 타입이 일관되지 않습니다 (void 와 %s)" % (f.name, fmt(s.type_of(res))))
            return None
        if res is None: raise s.rt('TypeError', "함수 '%s' 의 반환 타입이 일관되지 않습니다 (%s 와 void)" % (f.name, fmt(inf)))
        try: return s.coerce(res, inf, tv, f.env)
        except AsterError:
            raise s.rt('TypeError', "함수 '%s' 의 반환 타입이 일관되지 않습니다 (%s 와 %s)" % (f.name, fmt(inf), fmt(s.type_of(res))))
