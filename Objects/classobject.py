"""Objects/classobject.py — 클래스·인스턴스·네임스페이스 객체와 클래스 모델 (MRO, 접근 제한, 생성)."""
import sys, os, math, struct, functools, operator, gc
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from Python.state import state
from Python.errors import *
from Objects.object import *
from Objects.funcobject import *
from Objects.frameobject import *
from Parser.ast import *


class Mem:
    def __init__(s, **kw):
        s.static = False; s.const = False; s.type = None; s.func = None; s.getter = None; s.setter = None
        s.gacc = None; s.sacc = None; s.init = None; s.owner = None
        s.__dict__.update(kw)

class ClassObj:
    def __init__(s, name, is_iface):
        s.name = name; s.is_iface = is_iface; s.bases = []; s.ifaces = []; s.members = {}
        s.mro = []; s.all_types = set(); s.ilist = []; s.tparams = []; s.env = None; s.file = ''
        s.statics = {}; s.inits = []; s.ctor = None; s.dtor = None; s.node = None; s.mcache = {}

class NamespaceObj:
    def __init__(s, name, env): s.name = name; s.env = env; s.acc = {}; s.is_module = False; s.path = None

class Instance:
    __slots__ = ('cls', 'fields', 'targs', '__weakref__')
    def __init__(s, cls): s.cls = cls; s.fields = {}; s.targs = {}

class InstanceD(Instance):
    __slots__ = ()
    def __del__(s):
        try:
            if state.interp is not None: state.interp.destruct(s)
        except BaseException:
            pass


class ClassMixin:
    def c3(s, cls, bases):
        seqs = [b.mro[:] for b in bases] + [bases[:]]
        res = [cls]
        while True:
            seqs = [q for q in seqs if q]
            if not seqs: return res
            for q in seqs:
                c = q[0]
                if not any(c in t[1:] for t in seqs): break
            else:
                raise s.rt('TypeError', '다중 상속의 MRO 를 결정할 수 없습니다: ' + cls.name)
            res.append(c)
            for q in seqs:
                if q[0] is c: q.pop(0)

    def bases_ready(s, d, env):
        for t in list(d.bases) + list(d.ifaces):
            if s.lookup_class_opt(t.name, env) is None: return False
        return True

    def hoist_classes(s, decls, env):
        pending = list(decls); progress = True
        while pending and progress:
            progress = False
            for d in list(pending):
                if s.bases_ready(d, env):
                    s.define_class(d, env); pending.remove(d); progress = True

    def x_class(s, n, env):
        slot = env.vars.get(n.name)
        if slot is not None and isinstance(slot[0], ClassObj) and slot[0].node is n: return None
        s.define_class(n, env)

    def define_class(s, d, env):
        iface = d.kind == 'interface'
        cls = ClassObj(d.name, iface); cls.node = d; cls.env = env; cls.file = s.ctx_file
        cls.tparams = [t[0] for t in d.tparams]
        for t in d.bases:
            b = s.lookup_class(t.name, env)
            if b.is_iface: raise s.rt('TypeError', "클래스는 인터페이스를 extends 할 수 없습니다 (implements 사용): " + b.name)
            cls.bases.append(b)
        for t in d.ifaces:
            b = s.lookup_class(t.name, env)
            if not b.is_iface: raise s.rt('TypeError', "implements/extends 대상은 인터페이스여야 합니다: " + b.name)
            cls.ifaces.append(b)
        cls.mro = s.c3(cls, cls.bases)
        cls.all_types = set(cls.mro)
        il = []
        for c in cls.mro:
            for i in c.ifaces:
                for x in [i] + i.ilist:
                    if x not in il: il.append(x)
        cls.ilist = il
        for i in il: cls.all_types.add(i)
        defacc = 'public' if iface else 'private'
        env.vars[d.name] = [cls, TypeRef('class'), True]
        statics = []
        for m in d.members:
            c = m.__class__
            if c is FieldD:
                acc = access_of(m.mods, defacc)
                if 'static' in m.mods or 'const' in m.mods:
                    cls.members[m.name] = Mem(kind='field', name=m.name, access=acc, static=True,
                                              const='const' in m.mods, type=m.ty, owner=cls)
                    statics.append(m)
                else:
                    cls.members[m.name] = Mem(kind='field', name=m.name, access=acc, type=m.ty, owner=cls)
                    cls.inits.append((m.name, m.ty, m.init, False))
            elif c is FuncDecl:
                if m.body is None and m.expr is None and not iface:
                    raise s.rt('TypeError', "메서드 '%s' 에 본문이 없습니다" % m.name)
                f = s.make_func(m, env, cls)
                cls.members[m.name] = Mem(kind='method', name=m.name, access=access_of(m.mods, defacc),
                                          static='static' in m.mods, func=f, owner=cls)
            elif c is PropD:
                mem = Mem(kind='property', name=m.name, access=access_of(m.mods, defacc), type=m.ty, owner=cls)
                if m.getter:
                    body, acc = m.getter; mem.gacc = acc
                    mem.getter = 'auto' if body == 'auto' else Function(
                        name='get_' + m.name, params=[], rtype=m.ty, body=body, expr=None, env=env, tparams=[],
                        owner=cls, file=s.ctx_file)
                if m.setter:
                    body, acc = m.setter; mem.sacc = acc
                    mem.setter = 'auto' if body == 'auto' else Function(
                        name='set_' + m.name, params=[Param(m.ty, 'value', None)], rtype=None, body=body, expr=None,
                        env=env, tparams=[], owner=cls, file=s.ctx_file)
                cls.members[m.name] = mem
                cls.inits.append(('$' + m.name, m.ty, m.init, True))
            elif c is CtorD:
                cls.ctor = Function(name='constructor', params=m.params, rtype=None, body=m.body, expr=None, env=env,
                                    tparams=[], owner=cls, file=s.ctx_file, initlist=m.initlist, is_ctor=True)
            elif c is DtorD:
                cls.dtor = Function(name='destructor', params=[], rtype=None, body=m.body, expr=None, env=env,
                                    tparams=[], owner=cls, file=s.ctx_file)
        if not iface:
            for i in cls.ilist:
                for nm, mem in i.members.items():
                    abstract = (mem.kind == 'method' and mem.func.body is None and mem.func.expr is None)
                    if mem.kind == 'property' or abstract:
                        impl = s.find_member(cls, nm)
                        if impl is None or impl[0].owner is i or (impl[0].kind == 'method' and impl[0].func.body is None and impl[0].func.expr is None):
                            raise s.rt('TypeError', "클래스 %s 은(는) 인터페이스 %s 의 '%s' 를 구현하지 않았습니다" % (d.name, i.name, nm))
        saved = (s.ctx_cls, s.ctx_file)
        s.ctx_cls = cls
        try:
            for m in statics:
                v = s.ev(m.init, env) if m.init is not None else s.default_value(m.ty)
                if v is NO_DEFAULT: raise s.rt('TypeError', "static 필드 '%s' 에는 초기값이 필요합니다" % m.name)
                cls.statics[m.name] = s.coerce(v, m.ty, {}, env)
        finally:
            s.ctx_cls, s.ctx_file = saved
        return cls

    def find_member(s, cls, name):
        r = cls.mcache.get(name, 0)
        if r != 0: return r
        r = None
        for c in cls.mro:
            m = c.members.get(name)
            if m is not None: r = (m, c); break
        if r is None:
            for i in cls.ilist:
                m = i.members.get(name)
                if m is not None and m.kind == 'method' and (m.func.body is not None or m.func.expr is not None):
                    r = (m, i); break
        cls.mcache[name] = r
        return r

    def check_access(s, acc, owner, name):
        if acc == 'public' or acc == 'internal': return
        cc = s.ctx_cls
        if acc == 'private':
            if cc is not owner: raise s.rt('AccessError', "'%s.%s' 은(는) private 멤버입니다" % (owner.name, name))
        elif acc == 'protected':
            if cc is None or owner not in cc.mro:
                raise s.rt('AccessError', "'%s.%s' 은(는) protected 멤버입니다" % (owner.name, name))
        elif acc == 'file':
            if s.ctx_file != owner.file: raise s.rt('AccessError', "'%s.%s' 은(는) file 멤버입니다" % (owner.name, name))

    def itv(s, o):
        if not o.cls.tparams: return {}
        return {tp: o.targs.get(tp) for tp in o.cls.tparams}

    def get_member(s, o, name):
        if isinstance(o, Instance):
            fm = s.find_member(o.cls, name)
            if fm is None: raise s.rt('NameError', "%s 에는 '%s' 멤버가 없습니다" % (o.cls.name, name))
            m, owner = fm
            if m.kind == 'property':
                s.check_access(m.gacc or m.access, owner, name)
                if m.getter is None: raise s.rt('AccessError', "프로퍼티 '%s' 은(는) 읽을 수 없습니다 (get 없음)" % name)
                if m.getter == 'auto':
                    try: return o.fields['$' + name]
                    except KeyError: raise s.rt('NullError', "프로퍼티 '%s' 이(가) 초기화되지 않았습니다" % name)
                return s.call_function(m.getter, [], o)
            s.check_access(m.access, owner, name)
            if m.kind == 'field':
                if m.static: return owner.statics[name]
                try: return o.fields[name]
                except KeyError: raise s.rt('NullError', "필드 '%s' 이(가) 초기화되지 않았습니다" % name)
            return m.func if m.static else BoundMethod(m.func, o)
        if isinstance(o, ClassObj):
            fm = s.find_member(o, name)
            if fm is None: raise s.rt('NameError', "%s 에는 '%s' 멤버가 없습니다" % (o.name, name))
            m, owner = fm
            if not m.static: raise s.rt('TypeError', "'%s' 은(는) 인스턴스 멤버입니다 (new 로 생성 후 사용)" % name)
            s.check_access(m.access, owner, name)
            return owner.statics[name] if m.kind == 'field' else m.func
        if isinstance(o, NamespaceObj):
            slot = o.env.vars.get(name)
            if slot is None: raise s.rt('NameError', "네임스페이스 %s 에는 '%s' 이(가) 없습니다" % (o.name, name))
            a = o.acc.get(name)
            if a:
                if a[0] == 'private': raise s.rt('AccessError', "'%s.%s' 은(는) private 입니다" % (o.name, name))
                if a[0] == 'file' and a[1] != s.ctx_file: raise s.rt('AccessError', "'%s.%s' 은(는) file 접근 제한입니다" % (o.name, name))
            return slot[0]
        return s.builtin_member(o, name)

    def set_member(s, o, name, v):
        if isinstance(o, Instance):
            fm = s.find_member(o.cls, name)
            if fm is None: raise s.rt('NameError', "%s 에는 '%s' 멤버가 없습니다" % (o.cls.name, name))
            m, owner = fm
            if m.kind == 'property':
                s.check_access(m.sacc or m.access, owner, name)
                if m.setter is None: raise s.rt('AccessError', "프로퍼티 '%s' 은(는) 읽기 전용입니다" % name)
                if m.setter == 'auto':
                    o.fields['$' + name] = s.coerce(v, m.type, s.itv(o), owner.env); return
                s.call_function(m.setter, [v], o); return
            if m.kind != 'field': raise s.rt('TypeError', "'%s' 에는 대입할 수 없습니다" % name)
            s.check_access(m.access, owner, name)
            if m.const: raise s.rt('TypeError', "상수 '%s' 에는 대입할 수 없습니다" % name)
            v = s.coerce(v, m.type, s.itv(o), owner.env)
            if m.static: owner.statics[name] = v
            else: o.fields[name] = v
            return
        if isinstance(o, ClassObj):
            fm = s.find_member(o, name)
            if fm is None or not fm[0].static or fm[0].kind != 'field':
                raise s.rt('NameError', "%s 에는 static 필드 '%s' 이(가) 없습니다" % (o.name, name))
            m, owner = fm
            s.check_access(m.access, owner, name)
            if m.const: raise s.rt('TypeError', "상수 '%s' 에는 대입할 수 없습니다" % name)
            owner.statics[name] = s.coerce(v, m.type, {}, owner.env); return
        raise s.rt('TypeError', "%s 의 멤버 '%s' 에는 대입할 수 없습니다" % (fmt(s.type_of(o)), name))

    def super_member(s, o, name, env):
        slot = env.lookup('this')
        if slot is None: raise s.rt('NameError', "'super' 는 인스턴스 메서드 안에서만 사용할 수 있습니다")
        this = slot[0]
        if o.ty is not None:
            chain = s.lookup_class(o.ty.name, env).mro
        else:
            mro = this.cls.mro
            idx = mro.index(s.ctx_cls) if s.ctx_cls in mro else -1
            chain = mro[idx + 1:]
        for c in chain:
            m = c.members.get(name)
            if m is not None and m.kind == 'method': return BoundMethod(m.func, this)
        for i in this.cls.ilist:
            m = i.members.get(name)
            if m is not None and m.kind == 'method' and (m.func.body is not None or m.func.expr is not None):
                return BoundMethod(m.func, this)
        raise s.rt('NameError', "부모 클래스에 메서드 '%s' 이(가) 없습니다" % name)

    def instantiate(s, cls, args, targs):
        if cls.is_iface: raise s.rt('TypeError', "인터페이스는 인스턴스화할 수 없습니다: " + cls.name)
        has_d = any(c.dtor for c in cls.mro)
        o = (InstanceD if has_d else Instance)(cls)
        if targs and cls.tparams: o.targs = dict(zip(cls.tparams, targs))
        s.run_init(cls, o, args, set())
        return o

    def run_init(s, c, obj, args, done):
        if c in done: return
        done.add(c)
        ctor = c.ctor
        tv = {tp: obj.targs.get(tp) for tp in c.tparams}
        saved = (s.ctx_cls, s.ctx_file, s.tv)
        s.ctx_cls = c; s.ctx_file = c.file; s.tv = tv; s.depth += 1
        try:
            env = Env(c.env); env.vars['this'] = [obj, None, True]
            init = []
            if ctor is not None:
                s.bind_params(ctor, env, args, tv); init = ctor.initlist or []
            elif args:
                if not c.bases: raise s.rt('TypeError', "%s 에는 생성자가 없어 인자를 받을 수 없습니다" % c.name)
                s.run_init(c.bases[0], obj, args, done)
            for pty, aexprs in init:
                if pty is None:
                    if len(c.bases) != 1: raise s.rt('TypeError', "부모가 여러 개이면 super<Parent>(...) 로 지정하세요")
                    pc = c.bases[0]
                else:
                    pc = s.lookup_class(pty.name, c.env)
                    if pc not in c.bases: raise s.rt('TypeError', "%s 은(는) %s 의 직접 부모가 아닙니다" % (pc.name, c.name))
                s.run_init(pc, obj, [s.ev(a, env) for a in aexprs], done)
            for b in c.bases: s.run_init(b, obj, [], done)
            for nm, ty, ie, isprop in c.inits:
                if ie is not None: v = s.coerce(s.ev(ie, env), ty, tv, c.env)
                else:
                    v = s.default_value(ty)
                    if v is NO_DEFAULT: continue
                obj.fields[nm] = v
            if ctor is not None:
                b = ctor.body
                if b.fns or b.classes: s.hoist(b, env)
                s.exec_stmts(b.stmts, env)
        finally:
            s.ctx_cls, s.ctx_file, s.tv = saved; s.depth -= 1
        for tp in c.tparams:
            if tv.get(tp) is not None: obj.targs[tp] = tv[tp]

    def destruct(s, obj):
        if s.glob is None: return
        for c in obj.cls.mro:
            if c.dtor is not None:
                try: s.call_function(c.dtor, [], obj)
                except Exception: pass
