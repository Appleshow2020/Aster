"""Python/executor.py — 문장 실행(제어 흐름·선언·예외 처리)."""
import sys, os, math, struct, functools, operator, gc
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from Python.state import state
from Python.errors import *
from Objects.object import *
from Objects.funcobject import *
from Objects.frameobject import *
from Objects.classobject import *
from Parser.ast import *


class ExecMixin:
    def exec_stmts(s, stmts, env):
        ex = s.EX
        for st in stmts:
            s.line = st.line
            r = ex[st.__class__](st, env)
            if r is not None: return r
        return None

    def run_stmt(s, st, env):
        s.line = st.line
        return s.EX[st.__class__](st, env)

    def hoist(s, n, env):
        for fd in n.fns: s.define_func(fd, env)
        if n.classes: s.hoist_classes(n.classes, env)

    def define_func(s, fd, env):
        env.vars[fd.name] = [s.make_func(fd, env), TypeRef('fn'), False]

    def make_func(s, fd, env, owner=None):
        return Function(name=fd.name, params=fd.params, rtype=fd.rtype, body=fd.body, expr=fd.expr, env=env,
                        tparams=fd.tparams or [], owner=owner if owner is not None else s.ctx_cls,
                        file=s.ctx_file, tv=s.tv or None, node=fd, static='static' in fd.mods)

    def x_func(s, n, env):
        slot = env.vars.get(n.name)
        if slot is not None and getattr(slot[0], 'node', None) is n: return None
        if n.body is None and n.expr is None: raise s.rt('TypeError', "함수 '%s' 에 본문이 없습니다" % n.name)
        s.define_func(n, env)

    def x_expr(s, n, env):
        s.ev(n.e, env)

    def x_var(s, n, env):
        t = n.ty
        if n.name in env.vars and not s.repl: raise s.rt('NameError', "이미 선언된 변수입니다: " + n.name)
        if n.init is None:
            if t.name == 'var': raise s.rt('TypeError', "var 는 초기값이 필요합니다")
            v = s.default_value(t)
            if v is NO_DEFAULT: raise s.rt('TypeError', "'%s' 은(는) 초기값이 필요합니다" % n.name)
            vt = t
        else:
            v = s.ev(n.init, env)
            if t.name == 'var':
                if v is None: raise s.rt('TypeError', "var 는 null 로 타입을 추론할 수 없습니다")
                s.infer_collection(v); vt = s.type_of(v)
            else:
                v = s.coerce(v, t, None, env); vt = t
        env.vars[n.name] = [v, vt, bool(n.const)]

    def x_block(s, n, env):
        e = Env(env)
        if n.fns or n.classes: s.hoist(n, e)
        return s.exec_stmts(n.stmts, e)

    def x_if(s, n, env):
        if s.cond(s.ev(n.c, env)): return s.run_stmt(n.t, env)
        if n.e is not None: return s.run_stmt(n.e, env)

    def x_while(s, n, env):
        while True:
            if not s.cond(s.ev(n.c, env)): break
            r = s.run_stmt(n.b, env)
            if r is not None:
                if r is BRK: break
                if r is CNT: continue
                return r

    def x_for(s, n, env):
        e = Env(env)
        if n.init is not None: s.run_stmt(n.init, e)
        while True:
            if n.c is not None and not s.cond(s.ev(n.c, e)): break
            r = s.run_stmt(n.b, e)
            if r is not None:
                if r is BRK: break
                if r is not CNT: return r
            if n.step is not None: s.ev(n.step, e)

    def x_foreach(s, n, env):
        seq = s.iter_values(s.ev(n.it, env)); t = n.ty
        if t is not None and t.name == 'var': t = None
        for v in seq:
            e = Env(env)
            if t is not None: v = s.coerce(v, t, None, env)
            e.vars[n.name] = [v, t, False]
            r = s.run_stmt(n.b, e)
            if r is not None:
                if r is BRK: break
                if r is CNT: continue
                return r

    def x_return(s, n, env):
        return ('return', s.ev(n.e, env) if n.e is not None else None)

    def error_cls(s, name):
        slot = s.root.vars.get(name)
        return slot[0] if slot else s.root.vars['Error'][0]

    def make_error(s, kind, msg):
        o = Instance(s.error_cls(kind)); o.fields['message'] = msg
        return o

    def x_throw(s, n, env):
        v = s.ev(n.e, env)
        if type(v) is str: v = s.make_error('Error', v)
        elif not (isinstance(v, Instance) and s.error_cls('Error') in v.cls.all_types):
            raise s.rt('TypeError', 'throw 에는 Error 또는 string 만 사용할 수 있습니다')
        raise AsterThrow(v)

    def to_thrown(s, ex):
        if isinstance(ex, AsterThrow): return ex.value
        if isinstance(ex, RecursionError): return s.make_error('RuntimeError', '재귀가 너무 깊습니다')
        return s.make_error(ex.kind, ex.msg)

    def x_try(s, n, env):
        res = None; exc = None
        try:
            try:
                res = s.x_block(n.b, env)
            except (AsterError, AsterThrow, RecursionError) as ex:
                val = s.to_thrown(ex)
                for ty, name, blk in n.catches:
                    if ty is None or s.is_instance(val, ty, env):
                        e = Env(env)
                        if name: e.vars[name] = [val, None, False]
                        if blk.fns or blk.classes: s.hoist(blk, e)
                        res = s.exec_stmts(blk.stmts, e)
                        break
                else:
                    raise
        except BaseException as ex2:
            exc = ex2
        if n.fin is not None:
            fr = s.x_block(n.fin, env)
            if fr is not None: return fr
        if exc is not None: raise exc
        return res
