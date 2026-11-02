"""Python/importer.py — 네임스페이스와 모듈 임포트 (CPython 의 Python/import.c + importlib).

임포트 규칙
  import A.B;            프로그램 안에서 선언한 namespace 의 멤버를 현재 스코프로 가져온다(using).
  import math;           모듈을 찾아 `math` 이름으로 바인딩한다.
  import a.b as x;       별칭으로 바인딩.
  from m import f, g as h;
  import "file.ast";     경로로 파일을 현재 전역 스코프에서 실행한다.

모듈 탐색 순서: 이미 로드된 모듈 → 네이티브 모듈(Modules/) → sys.path 의 `<이름>.ast` 또는 `<이름>/__init__.ast`.
"""
import sys, os, math, struct, functools, operator, gc, importlib
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from Python.state import state
from Python.errors import *
from Objects.object import *
from Objects.funcobject import *
from Objects.frameobject import *
from Objects.classobject import *
from Objects.moduleobject import make_module
from Parser.ast import *
from Parser.tokenizer import lex
from Parser.parser import Parser
from Modules import NATIVE


class ImportMixin:
    # ── namespace (프로그램 내부) ──
    def get_ns(s, parts):
        cur = s.glob; ns = None
        for p in parts:
            slot = cur.vars.get(p)
            if slot is None:
                ns = NamespaceObj(p, Env(s.glob)); cur.vars[p] = [ns, None, True]
            elif isinstance(slot[0], NamespaceObj): ns = slot[0]
            else: raise s.rt('NameError', "'%s' 은(는) 네임스페이스가 아닙니다" % p)
            cur = ns.env
        return ns

    def record_access(s, ns, stmts):
        for st in stmts:
            c = st.__class__
            if c in (FuncDecl, ClassDecl): ns.acc[st.name] = (access_of(st.mods, 'internal'), s.ctx_file)
            elif c is VarDecl: ns.acc[st.name] = ('internal', s.ctx_file)

    def x_namespace(s, n, env):
        ns = s.get_ns(n.path)
        s.record_access(ns, n.body.stmts)
        s.hoist(n.body, ns.env)
        return s.exec_stmts(n.body.stmts, ns.env)

    def find_program_ns(s, parts):
        cur = s.glob; ns = None
        for p in parts:
            slot = cur.vars.get(p)
            if slot is None or not isinstance(slot[0], NamespaceObj) or slot[0].is_module: return None
            ns = slot[0]; cur = ns.env
        return ns

    def visible(s, ns, name):
        a = ns.acc.get(name)
        return not (a and (a[0] == 'private' or (a[0] == 'file' and a[1] != s.ctx_file)))

    # ── 모듈 ──
    def find_module_file(s, name):
        rel = name.replace('.', os.sep)
        for d in list(s.path):
            for cand in (os.path.join(d, rel + '.ast'), os.path.join(d, rel, '__init__.ast')):
                if os.path.isfile(cand): return cand
        return None

    def import_module(s, name):
        m = s.modules.get(name)
        if m is not None: return m
        spec = NATIVE.get(name)
        if spec is not None:
            members = importlib.import_module(spec).init(s)
            m = make_module(name, members); s.modules[name] = m
            return m
        path = s.find_module_file(name)
        if path is None:
            raise s.rt('ImportError', "'%s' 모듈을 찾을 수 없습니다 (검색 경로: %s)" % (name, ', '.join(s.path)))
        m = make_module(name, {}, path); m.env.parent = s.root
        s.modules[name] = m
        try:
            with open(path, encoding='utf-8') as fh: src = fh.read()
            s.run_source(src, path, m.env, m)
        except BaseException:
            s.modules.pop(name, None); raise
        return m

    def bind_module(s, env, parts, mod):
        if len(parts) == 1:
            env.vars[parts[0]] = [mod, None, True]; return
        cur = env
        for p in parts[:-1]:
            slot = cur.vars.get(p)
            if slot is None or not isinstance(slot[0], NamespaceObj):
                ns = NamespaceObj(p, Env()); ns.is_module = True
                cur.vars[p] = [ns, None, True]; slot = cur.vars[p]
            cur = slot[0].env
        cur.vars[parts[-1]] = [mod, None, True]

    def x_import(s, n, env):
        if n.isfile:
            base = os.path.dirname(os.path.abspath(s.ctx_file)) if os.path.exists(s.ctx_file) else os.getcwd()
            p = os.path.join(base, n.target)
            if not os.path.exists(p): p = os.path.abspath(n.target)
            if not os.path.exists(p): raise s.rt('ImportError', "import 파일을 찾을 수 없습니다: " + n.target)
            ap = os.path.abspath(p)
            if ap in s.imported: return None
            s.imported.add(ap)
            with open(ap, encoding='utf-8') as fh: src = fh.read()
            s.run_source(src, ap, s.glob)
            return None
        parts = n.target
        pns = s.find_program_ns(parts)
        if pns is not None and not n.alias:
            if n.names:
                for nm, al in n.names:
                    slot = pns.env.vars.get(nm)
                    if slot is None or not s.visible(pns, nm): raise s.rt('ImportError', "'%s' 에 '%s' 이(가) 없습니다" % ('.'.join(parts), nm))
                    env.vars[al or nm] = slot
            else:
                for k, slot in pns.env.vars.items():
                    if s.visible(pns, k) and k not in env.vars: env.vars[k] = slot
            return None
        mod = s.import_module('.'.join(parts))
        if n.names:
            for nm, al in n.names:
                slot = mod.env.vars.get(nm)
                if slot is None or not s.visible(mod, nm):
                    raise s.rt('ImportError', "모듈 '%s' 에 '%s' 이(가) 없습니다" % ('.'.join(parts), nm))
                env.vars[al or nm] = slot
        elif n.alias: env.vars[n.alias] = [mod, None, True]
        else: s.bind_module(env, parts, mod)

    def run_source(s, src, fname, env, ns=None):
        toks = lex(src, fname)
        prog = Parser(toks, fname).parse_program()
        saved = s.ctx_file; s.ctx_file = fname
        try:
            if ns is not None: s.record_access(ns, prog.stmts)
            s.hoist(prog, env)
            return s.exec_stmts(prog.stmts, env)
        finally:
            s.ctx_file = saved
