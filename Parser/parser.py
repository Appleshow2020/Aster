"""Parser/parser.py — 재귀 하강 파서 (토큰 → AST)."""
from Objects.object import *
from Python.errors import *
from Parser.ast import *


class Parser:
    def __init__(s, toks, fname='<main>'):
        s.t = toks; s.p = 0; s.f = fname

    @property
    def tok(s): return s.t[s.p]

    def peek(s, k=1):
        j = s.p + k
        return s.t[j] if j < len(s.t) else s.t[-1]

    def adv(s):
        t = s.t[s.p]
        if t.type != 'eof': s.p += 1
        return t

    def desc(s, t):
        return {'eof': '파일 끝', 'nl': '줄바꿈'}.get(t.type) or repr(t.value if t.type != 'lit' else str(t.value))

    def err(s, msg, t=None):
        t = t or s.tok
        raise AsterSyntaxError(msg, t.line, s.f)

    def is_op(s, v): t = s.t[s.p]; return t.type == 'op' and t.value == v
    def is_kw(s, v): t = s.t[s.p]; return t.type == 'kw' and t.value == v

    def accept_op(s, v):
        if s.is_op(v): s.adv(); return True
        return False

    def accept_kw(s, v):
        if s.is_kw(v): s.adv(); return True
        return False

    def expect_op(s, v):
        if not s.is_op(v): s.err("'%s' 이(가) 필요하지만 %s 을(를) 만났습니다" % (v, s.desc(s.tok)))
        return s.adv()

    def expect_kw(s, v):
        if not s.is_kw(v): s.err("'%s' 키워드가 필요합니다" % v)
        return s.adv()

    def expect_id(s):
        if s.tok.type != 'id': s.err('식별자가 필요하지만 %s 을(를) 만났습니다' % s.desc(s.tok))
        return s.adv().value

    def skip_nl(s):
        while s.tok.type == 'nl': s.adv()

    def skip_terms(s):
        while s.tok.type == 'nl' or s.is_op(';'): s.adv()

    def end_stmt(s):
        t = s.tok
        if t.type == 'op' and t.value == ';': s.adv(); return
        if t.type == 'nl': s.adv(); return
        if t.type == 'eof' or (t.type == 'op' and t.value == '}'): return
        s.err('문장이 끝나야 하는 위치에 %s 이(가) 있습니다' % s.desc(t))

    # ── 프로그램 / 블록 ──
    def parse_program(s):
        stmts = s.parse_stmts(False)
        return s.mkblock(stmts, 1)

    def mkblock(s, stmts, line):
        return Block(stmts, [x for x in stmts if x.__class__ is FuncDecl],
                     [x for x in stmts if x.__class__ is ClassDecl], line=line)

    def parse_stmts(s, in_brace):
        out = []
        while True:
            s.skip_terms()
            t = s.tok
            if t.type == 'eof':
                if in_brace: s.err("'}' 이(가) 필요합니다")
                break
            if in_brace and t.type == 'op' and t.value == '}': break
            out.append(s.parse_statement())
        return out

    def parse_block(s):
        s.skip_nl()
        t = s.expect_op('{')
        stmts = s.parse_stmts(True)
        s.expect_op('}')
        return s.mkblock(stmts, t.line)

    def parse_body(s):
        s.skip_nl()
        return s.parse_statement()

    # ── 타입 ──
    def parse_type(s):
        t = s.tok
        if t.type != 'id' and not (t.type == 'kw' and t.value == 'fn'): s.err('타입 이름이 필요합니다')
        s.adv(); name = t.value
        while s.tok.type == 'op' and s.tok.value in ('.', '::') and s.peek().type == 'id':
            s.adv(); name += '.' + s.adv().value
        args = []
        if name == 'fn' and s.is_op('('):
            s.adv()
            if not s.is_op(')'):
                while True:
                    args.append(s.parse_type())
                    if not s.accept_op(','): break
            s.expect_op(')'); s.expect_op('->'); args.append(s.parse_type())
        elif s.is_op('<'):
            s.adv()
            while True:
                args.append(s.parse_type())
                if not s.accept_op(','): break
            s.expect_op('>')
        nullable = s.accept_op('?')
        return TypeRef(name, args, nullable)

    def parse_tparams(s):
        ps = []
        if s.is_op('<'):
            s.adv()
            while True:
                nm = s.expect_id(); bound = None
                if s.accept_op(':'): bound = s.parse_type()
                ps.append((nm, bound))
                if not s.accept_op(','): break
            s.expect_op('>')
        return ps

    def parse_param(s):
        ty = s.parse_type(); name = s.expect_id(); d = None
        if s.accept_op('='): d = s.parse_expr()
        return Param(ty, name, d)

    def parse_params(s):
        ps = []
        if not s.is_op(')'):
            while True:
                ps.append(s.parse_param())
                if not s.accept_op(','): break
        s.expect_op(')')
        return ps

    def parse_modifiers(s):
        mods = set()
        while True:
            t = s.tok
            if t.type == 'kw' and t.value in MODS:
                mods.add(t.value); s.adv()
            elif t.type == 'id' and t.value == 'file':
                n = s.peek()
                if n.type == 'id' or (n.type == 'kw' and n.value in DECLKW):
                    mods.add('file'); s.adv()
                else: break
            else: break
        return mods

    # ── 문장 ──
    def parse_statement(s):
        line = s.tok.line
        mods = s.parse_modifiers()
        t = s.tok
        if t.type == 'kw' and t.value in ('class', 'interface'): return s.parse_class(mods)
        if t.type == 'kw' and t.value == 'fn' and s.peek().type == 'id': return s.parse_func(mods)
        if mods:
            d = s.try_var_decl(mods)
            if d is None: s.err('수식어 뒤에는 선언이 와야 합니다')
            return d
        if t.type == 'op':
            if t.value == '{': return s.parse_block()
        if t.type == 'kw':
            v = t.value
            if v == 'if': return s.parse_if()
            if v == 'while':
                s.adv(); s.expect_op('('); c = s.parse_expr(); s.expect_op(')')
                return WhileN(c, s.parse_body(), line=line)
            if v == 'for': return s.parse_for()
            if v == 'break': s.adv(); s.end_stmt(); return BreakN(line=line)
            if v == 'continue': s.adv(); s.end_stmt(); return ContinueN(line=line)
            if v == 'return':
                s.adv(); e = None
                if not (s.tok.type in ('nl', 'eof') or s.is_op(';') or s.is_op('}')): e = s.parse_expr()
                s.end_stmt(); return ReturnN(e, line=line)
            if v == 'throw':
                s.adv(); e = s.parse_expr(); s.end_stmt(); return ThrowN(e, line=line)
            if v == 'try': return s.parse_try()
            if v == 'namespace':
                s.adv(); path = [s.expect_id()]
                while s.accept_op('.'): path.append(s.expect_id())
                return NamespaceN(path, s.parse_block(), line=line)
            if v == 'import':
                s.adv()
                if s.tok.type == 'lit' and isinstance(s.tok.value, str):
                    tg = s.adv().value; s.end_stmt(); return ImportN(tg, True, None, None, line=line)
                path = [s.expect_id()]
                while s.accept_op('.'): path.append(s.expect_id())
                alias = None
                if s.tok.type == 'id' and s.tok.value == 'as':
                    s.adv(); alias = s.expect_id()
                s.end_stmt(); return ImportN(path, False, alias, None, line=line)
        if t.type == 'id' and t.value == 'from' and s.is_from_import():
            s.adv(); path = [s.expect_id()]
            while s.accept_op('.'): path.append(s.expect_id())
            s.expect_kw('import'); names = []
            while True:
                nm = s.expect_id(); al = None
                if s.tok.type == 'id' and s.tok.value == 'as':
                    s.adv(); al = s.expect_id()
                names.append((nm, al))
                if not s.accept_op(','): break
            s.end_stmt(); return ImportN(path, False, None, names, line=line)
        d = s.try_var_decl(mods)
        if d is not None: return d
        e = s.parse_expr(); s.end_stmt()
        return ExprStmt(e, line=line)

    def is_from_import(s):
        j = s.p + 1
        if s.t[j].type != 'id': return False
        j += 1
        while s.t[j].type == 'op' and s.t[j].value == '.' and s.t[j + 1].type == 'id': j += 2
        return s.t[j].type == 'kw' and s.t[j].value == 'import'

    def try_var_decl(s, mods):
        start = s.p; t = s.tok
        if t.type != 'id' and not (t.type == 'kw' and t.value == 'fn'): return None
        try:
            ty = s.parse_type()
        except AsterSyntaxError:
            s.p = start; return None
        n = s.tok; nx = s.peek()
        if n.type == 'id' and ((nx.type == 'op' and nx.value in ('=', ';', '}')) or nx.type in ('nl', 'eof')):
            s.adv(); init = None
            if s.accept_op('='): init = s.parse_expr()
            s.end_stmt()
            if 'const' in mods and init is None: s.err('const 는 초기값이 필요합니다', n)
            return VarDecl(ty, n.value, init, 'const' in mods, line=n.line)
        s.p = start; return None

    def parse_if(s):
        line = s.adv().line
        s.expect_op('('); c = s.parse_expr(); s.expect_op(')')
        th = s.parse_body(); el = None
        save = s.p; s.skip_nl()
        if s.is_kw('else'):
            s.adv(); s.skip_nl()
            el = s.parse_if() if s.is_kw('if') else s.parse_statement()
        else: s.p = save
        return IfN(c, th, el, line=line)

    def parse_for(s):
        line = s.adv().line
        s.expect_op('(')
        start = s.p
        if s.tok.type == 'id' and s.peek().type == 'kw' and s.peek().value == 'in':
            nm = s.adv().value; s.adv(); it = s.parse_expr(); s.expect_op(')')
            return ForEachN(None, nm, it, s.parse_body(), line=line)
        try:
            ty = s.parse_type()
            if s.tok.type == 'id' and s.peek().type == 'kw' and s.peek().value == 'in':
                nm = s.adv().value; s.adv(); it = s.parse_expr(); s.expect_op(')')
                return ForEachN(ty, nm, it, s.parse_body(), line=line)
        except AsterSyntaxError:
            pass
        s.p = start
        init = None
        if s.is_op(';'): s.adv()
        else:
            init = s.try_var_decl(set())
            if init is None:
                init = ExprStmt(s.parse_expr(), line=line); s.expect_op(';')
        c = None
        if not s.is_op(';'): c = s.parse_expr()
        s.expect_op(';')
        step = None
        if not s.is_op(')'): step = s.parse_expr()
        s.expect_op(')')
        return ForN(init, c, step, s.parse_body(), line=line)

    def parse_try(s):
        line = s.adv().line
        blk = s.parse_block(); catches = []; fin = None
        while True:
            save = s.p; s.skip_nl()
            if s.is_kw('catch'):
                s.adv(); ty = None; name = None
                if s.accept_op('('):
                    if s.tok.type == 'id' and s.peek().type == 'op' and s.peek().value == ')':
                        name = s.adv().value
                    else:
                        ty = s.parse_type()
                        if s.tok.type == 'id': name = s.adv().value
                    s.expect_op(')')
                catches.append((ty, name, s.parse_block()))
            elif s.is_kw('finally'):
                s.adv(); fin = s.parse_block()
            else:
                s.p = save; break
        if not catches and fin is None: s.err('try 에는 catch 또는 finally 가 필요합니다')
        return TryN(blk, catches, fin, line=line)

    # ── 함수 / 클래스 ──
    def parse_func(s, mods):
        line = s.adv().line  # fn
        t = s.tok
        if t.type == 'kw' and t.value == 'operator':
            s.adv(); o = s.tok
            if o.type != 'op': s.err('연산자 기호가 필요합니다')
            s.adv(); name = 'operator' + o.value
        else: name = s.expect_id()
        tparams = s.parse_tparams()
        s.expect_op('('); params = s.parse_params()
        rtype = None
        if s.accept_op('->'): rtype = s.parse_type()
        body = None; expr = None
        save = s.p; s.skip_nl()
        if s.is_op('{'): body = s.parse_block()
        elif s.is_op('=>'):
            s.adv(); expr = s.parse_expr(); s.end_stmt()
        else:
            s.p = save; s.end_stmt()
        return FuncDecl(name, tparams, params, rtype, body, expr, mods, line=line)

    def parse_class(s, mods):
        t = s.adv(); kind = t.value; name = s.expect_id(); tparams = s.parse_tparams()
        bases = []; ifaces = []
        while True:
            if s.is_kw('extends'):
                s.adv()
                while True:
                    (ifaces if kind == 'interface' else bases).append(s.parse_type())
                    if not s.accept_op(','): break
            elif s.is_kw('implements'):
                s.adv()
                while True:
                    ifaces.append(s.parse_type())
                    if not s.accept_op(','): break
            else: break
        s.skip_nl(); s.expect_op('{')
        members = []
        while True:
            s.skip_terms()
            if s.is_op('}'): break
            if s.tok.type == 'eof': s.err("'}' 이(가) 필요합니다")
            members.append(s.parse_member())
        s.expect_op('}')
        return ClassDecl(name, kind, tparams, bases, ifaces, members, mods, line=t.line)

    def parse_member(s):
        line = s.tok.line
        mods = s.parse_modifiers(); t = s.tok
        if t.type == 'kw':
            if t.value == 'constructor':
                s.adv(); s.expect_op('('); params = s.parse_params(); init = []
                if s.accept_op(':'):
                    while True:
                        s.expect_kw('super'); pty = None
                        if s.accept_op('<'):
                            pty = s.parse_type(); s.expect_op('>')
                        s.expect_op('('); args = s.parse_args()
                        init.append((pty, args))
                        if not s.accept_op(','): break
                return CtorD(mods, params, init, s.parse_block(), line=line)
            if t.value == 'destructor':
                s.adv(); s.expect_op('('); s.expect_op(')')
                return DtorD(s.parse_block(), line=line)
            if t.value == 'fn': return s.parse_func(mods)
            if t.value == 'property': return s.parse_property(mods)
        ty = s.parse_type(); name = s.expect_id(); init = None
        if s.accept_op('='): init = s.parse_expr()
        s.end_stmt()
        return FieldD(mods, ty, name, init, line=line)

    def parse_property(s, mods):
        line = s.adv().line
        if 'static' in mods: s.err('static property 는 지원하지 않습니다')
        ty = s.parse_type(); name = s.expect_id()
        s.skip_nl(); s.expect_op('{')
        g = None; st = None
        s.skip_terms()
        while not s.is_op('}'):
            am = s.parse_modifiers(); acc = access_of(am, None)
            t = s.tok
            if t.type != 'id' or t.value not in ('get', 'set'): s.err('get 또는 set 이 필요합니다')
            s.adv()
            if s.is_op('{'): body = s.parse_block()
            elif s.is_op('=>') and t.value == 'get':
                s.adv(); e = s.parse_expr()
                body = s.mkblock([ReturnN(e, line=t.line)], t.line)
            else: body = 'auto'
            if t.value == 'get': g = (body, acc)
            else: st = (body, acc)
            s.skip_terms()
        s.expect_op('}')
        init = None
        if s.accept_op('='): init = s.parse_expr()
        s.end_stmt()
        return PropD(mods, ty, name, g, st, init, line=line)

    # ── 식 ──
    def parse_expr(s): return s.parse_assign()

    def parse_assign(s):
        left = s.parse_pipe(); t = s.tok
        if t.type == 'op' and t.value in ASSIGN_OPS:
            if left.__class__ not in (Name, Member, Index): s.err('대입할 수 없는 대상입니다')
            s.adv(); right = s.parse_assign()
            return Assign(t.value, left, right, line=t.line)
        return left

    def parse_pipe(s):
        left = s.parse_coal()
        while s.is_op('|>'):
            t = s.adv(); left = Pipe(left, s.parse_coal(), line=t.line)
        return left

    def parse_coal(s):
        left = s.parse_or()
        if s.is_op('??'):
            t = s.adv(); return Coal(left, s.parse_coal(), line=t.line)
        return left

    def parse_or(s):
        left = s.parse_and()
        while s.is_op('||') or s.is_kw('or'):
            t = s.adv(); left = Logic('or', left, s.parse_and(), line=t.line)
        return left

    def parse_and(s):
        left = s.parse_not()
        while s.is_op('&&') or s.is_kw('and'):
            t = s.adv(); left = Logic('and', left, s.parse_not(), line=t.line)
        return left

    def parse_not(s):
        if s.is_op('!') or s.is_kw('not'):
            t = s.adv(); return Unary('not', s.parse_not(), line=t.line)
        return s.parse_cmp()

    def parse_cmp(s):
        left = s.parse_range()
        while True:
            t = s.tok
            if t.type == 'op' and t.value in CMP:
                s.adv(); left = Binary(t.value, left, s.parse_range(), line=t.line)
            elif t.type == 'kw' and t.value == 'is':
                s.adv(); neg = s.accept_kw('not')
                ty = None
                if not s.accept_kw('null'): ty = s.parse_type()
                left = IsN(left, ty, neg, line=t.line)
            elif t.type == 'kw' and t.value == 'in':
                s.adv(); left = InN(left, s.parse_range(), False, line=t.line)
            elif t.type == 'kw' and t.value == 'not' and s.peek().type == 'kw' and s.peek().value == 'in':
                s.adv(); s.adv(); left = InN(left, s.parse_range(), True, line=t.line)
            else: break
        return left

    def parse_range(s):
        left = s.parse_add()
        if s.is_op('..'):
            t = s.adv(); return RangeN(left, s.parse_add(), line=t.line)
        return left

    def parse_add(s):
        left = s.parse_mul()
        while s.tok.type == 'op' and s.tok.value in ('+', '-'):
            t = s.adv(); left = Binary(t.value, left, s.parse_mul(), line=t.line)
        return left

    def parse_mul(s):
        left = s.parse_unary()
        while s.tok.type == 'op' and s.tok.value in ('*', '/', '//', '%'):
            t = s.adv(); left = Binary(t.value, left, s.parse_unary(), line=t.line)
        return left

    def parse_unary(s):
        if s.tok.type == 'op' and s.tok.value in ('-', '+'):
            t = s.adv(); return Unary(t.value, s.parse_unary(), line=t.line)
        return s.parse_power()

    def parse_power(s):
        base = s.parse_postfix()
        if s.is_op('**'):
            t = s.adv(); return Binary('**', base, s.parse_unary(), line=t.line)
        return base

    def parse_args(s):
        args = []
        if not s.is_op(')'):
            while True:
                args.append(s.parse_expr())
                if not s.accept_op(','): break
        s.expect_op(')')
        return args

    def try_generic_call(s, e):
        save = s.p
        try:
            s.adv(); targs = [s.parse_type()]
            while s.accept_op(','): targs.append(s.parse_type())
            s.expect_op('>')
            if s.is_op('('):
                t = s.adv(); return Call(e, s.parse_args(), targs, line=t.line)
        except AsterSyntaxError:
            pass
        s.p = save
        return None

    def parse_postfix(s):
        e = s.parse_primary(); safe = False
        while True:
            t = s.tok
            if t.type != 'op': break
            v = t.value
            if v == '(':
                s.adv(); e = Call(e, s.parse_args(), None, line=t.line)
            elif v in ('.', '::'):
                s.adv(); e = Member(e, s.expect_id(), False, line=t.line)
            elif v == '?.':
                s.adv(); e = Member(e, s.expect_id(), True, line=t.line); safe = True
            elif v == '[':
                s.adv(); idx = s.parse_expr(); s.expect_op(']'); e = Index(e, idx, line=t.line)
            elif v == '<' and e.__class__ in (Name, Member):
                r = s.try_generic_call(e)
                if r is None: break
                e = r
            else: break
        return Chain(e, line=e.line) if safe else e

    def paren_is_lambda(s):
        d = 0; j = s.p
        while True:
            t = s.t[j]
            if t.type == 'eof': return False
            if t.type == 'op':
                if t.value == '(': d += 1
                elif t.value == ')':
                    d -= 1
                    if d == 0:
                        n = s.t[j + 1]
                        return n.type == 'op' and n.value == '=>'
            j += 1

    def parse_lparams(s):
        ps = []
        if not s.is_op(')'):
            while True:
                t = s.tok
                if t.type == 'id' and s.peek().type == 'op' and s.peek().value in (',', ')'):
                    s.adv(); ps.append(Param(None, t.value, None))
                else: ps.append(s.parse_param())
                if not s.accept_op(','): break
        s.expect_op(')')
        return ps

    def parse_lambda_rest(s, params, rtype, line):
        if s.is_op('{'):
            return LambdaN(params, rtype, None, s.parse_block(), line=line)
        s.expect_op('=>')
        if s.is_op('{'):
            return LambdaN(params, rtype, None, s.parse_block(), line=line)
        return LambdaN(params, rtype, s.parse_assign(), None, line=line)

    def parse_primary(s):
        t = s.tok; ty = t.type; v = t.value; line = t.line
        if ty == 'lit':
            s.adv(); return Lit(v, line=line)
        if ty == 'id':
            n = s.peek()
            if n.type == 'op' and n.value == '=>':
                s.adv(); return s.parse_lambda_rest([Param(None, v, None)], None, line)
            s.adv(); return Name(v, line=line)
        if ty == 'kw':
            if v == 'true': s.adv(); return Lit(True, line=line)
            if v == 'false': s.adv(); return Lit(False, line=line)
            if v == 'null': s.adv(); return Lit(None, line=line)
            if v == 'this': s.adv(); return ThisN(line=line)
            if v == 'super':
                s.adv(); sty = None
                if s.accept_op('<'):
                    sty = s.parse_type(); s.expect_op('>')
                if not (s.is_op('.') or s.is_op('::')): s.err("super 뒤에는 '.메서드' 가 와야 합니다")
                return SuperN(sty, line=line)
            if v == 'new':
                s.adv(); nty = s.parse_type(); s.expect_op('(')
                return NewN(nty, s.parse_args(), line=line)
            if v == 'cast':
                s.adv(); s.expect_op('<'); cty = s.parse_type(); s.expect_op('>'); s.expect_op('(')
                e = s.parse_expr(); s.expect_op(')')
                return CastN(cty, e, line=line)
            if v == 'fn':
                s.adv(); s.expect_op('('); ps = s.parse_lparams(); rt = None
                if s.accept_op('->'): rt = s.parse_type()
                return s.parse_lambda_rest(ps, rt, line)
        if ty == 'op':
            if v == '(':
                if s.paren_is_lambda():
                    s.adv(); ps = s.parse_lparams(); return s.parse_lambda_rest(ps, None, line)
                s.adv()
                if s.accept_op(')'): return TupleLit([], line=line)
                e = s.parse_expr()
                if s.is_op(','):
                    items = [e]
                    while s.accept_op(','):
                        if s.is_op(')'): break
                        items.append(s.parse_expr())
                    s.expect_op(')'); return TupleLit(items, line=line)
                s.expect_op(')'); return e
            if v == '[':
                s.adv(); items = []
                while not s.is_op(']'):
                    items.append(s.parse_expr())
                    if not s.accept_op(','): break
                s.expect_op(']'); return ListLit(items, line=line)
            if v == '{':
                s.adv(); s.skip_nl()
                if s.accept_op('}'): return MapLit([], line=line)
                first = s.parse_expr(); s.skip_nl()
                if s.is_op(':'):
                    s.adv(); s.skip_nl(); pairs = [(first, s.parse_expr())]; s.skip_nl()
                    while s.accept_op(','):
                        s.skip_nl()
                        if s.is_op('}'): break
                        k = s.parse_expr(); s.skip_nl(); s.expect_op(':'); s.skip_nl()
                        pairs.append((k, s.parse_expr())); s.skip_nl()
                    s.expect_op('}'); return MapLit(pairs, line=line)
                items = [first]
                while s.accept_op(','):
                    s.skip_nl()
                    if s.is_op('}'): break
                    items.append(s.parse_expr()); s.skip_nl()
                s.expect_op('}'); return SetLit(items, line=line)
        s.err('식에서 예상하지 못한 토큰: ' + s.desc(t))
