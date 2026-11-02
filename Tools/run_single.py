#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (참고용) 분해 이전의 단일 파일 구현. 현재 프로젝트는 run.py + 패키지 구조를 사용한다.
"""
Aster 0.4 인터프리터 (단일 파일)

사용법:
    python run.py program.ast     # 파일 실행
    python run.py --demo          # 내장 데모 실행
    python run.py                 # 대화형 REPL
    python run.py -c "print(1)"   # 코드 문자열 실행

[0.4 확정 사항 요약 — 0.3의 미정/제안 항목을 모두 확정]
 * 주석: '#' 한 줄, '/* ... */' 여러 줄 ('//'는 정수 나눗셈)
 * 줄바꿈이 문장 끝. 줄이 연산자/쉼표/여는 괄호로 끝나거나, 다음 줄이 '|>', '.', '?.', '&&', '||', '??', and, or 로
   시작하면 문장이 이어진다. 괄호 () [] 안에서는 줄바꿈이 무시된다.
 * 리터럴: 1(int) 1.5(double) 1.5f(float) 10.5m(decimal) 'A'(char) "s"(string), 정수는 int/long/byte 범위로 검사
 * 타입 검사는 '실행 시점'에 엄격하게 수행(암시적 변환 없음). int/int 의 '/' 는 double, '//' 는 정수 나눗셈
 * cast<T>(v): 실패 시 ValueError, 대상이 nullable(T?)이면 null 반환
 * 조건식은 반드시 bool. null 은 nullable(T?) 에만 대입 가능
 * 연산자 우선순위(낮음→높음): 대입 < |> < ?? < or,|| < and,&& < not,! < 비교(==,!=,<,>,<=,>=,is,in)
   < .. < + - < * / // % < 단항 +- < ** < 후위(호출 . ?. :: [])   ('**' 우측결합, '??' 우측결합)
 * 'is': 타입/클래스 검사(x is int, x is Shape, x is null, x is not T). 'in': 포함 검사
 * 범위 a..b 는 [a, b) 반개구간. 인덱스/슬라이스에도 사용(xs[1..3])
 * 파이프라인: x |> f  == f(x),  x |> f(a) == f(x, a)
 * 람다: x => x*2, (a, b) => a+b, fn(int x) => x*2, fn(x) { return x }
 * 컬렉션: list<T> map<K,V> set<T> array<T> tuple, 리터럴 [..] {k: v} {a, b} (a, b)
 * 접근 제한자: 멤버 기본값 private, 최상위 기본값 internal, 인터페이스 멤버는 public
 * 생성자 키워드는 constructor. 생성자를 생략하면 첫 부모 생성자를 상속. 소멸자는 destructor
   부모 생성자 호출: constructor(...) : super(...) {}  또는 super<Parent>(...), 나머지 부모는 인자 없이 자동 호출
 * 다중 상속: C3 MRO. super.method() 는 MRO 다음 클래스, super<Parent>.method() 는 지정 부모
 * 프로퍼티: property T Name { get; set; } / get {..} set {..}(value) / get => expr / private set
 * 연산자 오버로딩: fn operator+(Vec o) -> Vec, operator-() 단항, operator== 등, toString() 은 출력에 사용
 * 예외: throw "msg" 는 throw new Error("msg") 와 동일. catch (Type e) 여러 개 가능. 내장 Error 계열:
   Error, RuntimeError, TypeError, ValueError, NullError, IndexError, KeyError, ZeroDivisionError, NameError, AccessError
 * 모듈: namespace A.B { }, import A.B;, import "other.ast";  file 접근 제한자는 같은 소스 파일에서만 허용
 * 제네릭: fn f<T>(T v) -> T, class Box<T>, 제약 <T: Shape>. 반환 타입 생략 시 첫 반환 타입으로 고정
 * 메모리 관리: 자동(파이썬 GC). destructor 는 객체가 해제될 때 호출
"""
import sys, os, math, struct, threading, functools, operator, gc
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, getcontext

getcontext().prec = 40
VERSION = "0.4"
_CUR = None  # 현재 인터프리터(오류 줄번호용)


# ───────────────────────── 오류 ─────────────────────────
class AsterSyntaxError(Exception):
    def __init__(s, msg, line=0, file=''):
        Exception.__init__(s, msg); s.msg = msg; s.line = line; s.file = file


class AsterError(Exception):
    def __init__(s, kind, msg):
        Exception.__init__(s, msg); s.kind = kind; s.msg = msg
        s.line = _CUR.line if _CUR else 0
        s.file = _CUR.ctx_file if _CUR else ''


class AsterThrow(Exception):
    def __init__(s, value):
        Exception.__init__(s); s.value = value
        s.line = _CUR.line if _CUR else 0


class ShortCircuit(Exception):
    pass


class ExitProgram(Exception):
    def __init__(s, code=0):
        Exception.__init__(s); s.code = code


# ───────────────────────── 값 표현 ─────────────────────────
class Char:
    __slots__ = ('c',)
    def __init__(s, c): s.c = c
    def __eq__(s, o): return type(o) is Char and o.c == s.c
    def __ne__(s, o): return not s.__eq__(o)
    def __hash__(s): return hash(('char', s.c))
    def __lt__(s, o): return s.c < o.c
    def __le__(s, o): return s.c <= o.c
    def __gt__(s, o): return s.c > o.c
    def __ge__(s, o): return s.c >= o.c
    def __str__(s): return s.c


class F32(float):
    __slots__ = ()


def mkf32(x):
    try:
        return F32(struct.unpack('f', struct.pack('f', x))[0])
    except OverflowError:
        return F32(math.copysign(math.inf, x))


class AList(list):
    __slots__ = ('elem', 'lit')
    def __init__(s, it=(), elem=None, lit=False):
        list.__init__(s, it); s.elem = elem; s.lit = lit


class AArray(list):
    __slots__ = ('elem', 'lit')
    def __init__(s, it=(), elem=None, lit=False):
        list.__init__(s, it); s.elem = elem; s.lit = lit


class ASet(dict):
    __slots__ = ('elem', 'lit')
    def __init__(s, it=(), elem=None, lit=False):
        dict.__init__(s)
        for x in it: s[x] = True
        s.elem = elem; s.lit = lit


class AMap(dict):
    __slots__ = ('kt', 'vt', 'lit')
    def __init__(s):
        dict.__init__(s); s.kt = None; s.vt = None; s.lit = False


class Rng:
    __slots__ = ('a', 'b')
    def __init__(s, a, b): s.a = a; s.b = b


class TypeRef:
    __slots__ = ('name', 'args', 'nullable', 'cls')
    def __init__(s, name, args=None, nullable=False, cls=None):
        s.name = name; s.args = args or []; s.nullable = nullable; s.cls = cls


def fmt(t):
    if t is None: return '?'
    if t.name == 'fn' and t.args:
        s = 'fn(' + ', '.join(fmt(a) for a in t.args[:-1]) + ') -> ' + fmt(t.args[-1])
    elif t.args:
        s = t.name + '<' + ', '.join(fmt(a) for a in t.args) + '>'
    else:
        s = t.name
    return s + '?' if t.nullable else s


T_BOOL = TypeRef('bool'); T_INT = TypeRef('int'); T_LONG = TypeRef('long')
T_DOUBLE = TypeRef('double'); T_FLOAT = TypeRef('float'); T_DECIMAL = TypeRef('decimal')
T_CHAR = TypeRef('char'); T_STRING = TypeRef('string'); T_OBJECT = TypeRef('object')
T_UNK = TypeRef('?'); T_NULL = TypeRef('null')
KIND = {int: 'int', float: 'double', F32: 'float', Decimal: 'decimal', str: 'string', Char: 'char', bool: 'bool'}
NUMERIC = ('int', 'double', 'float', 'decimal')
PRIM = {
    'bool': lambda v: type(v) is bool,
    'byte': lambda v: type(v) is int and 0 <= v <= 255,
    'int': lambda v: type(v) is int and -2147483648 <= v <= 2147483647,
    'long': lambda v: type(v) is int and -9223372036854775808 <= v <= 9223372036854775807,
    'float': lambda v: type(v) is F32,
    'double': lambda v: type(v) is float,
    'decimal': lambda v: type(v) is Decimal,
    'char': lambda v: type(v) is Char,
    'string': lambda v: type(v) is str,
    'object': lambda v: True,
}
COLL = ('list', 'map', 'array', 'set')
NO_DEFAULT = object()


class Env:
    __slots__ = ('vars', 'parent')
    def __init__(s, parent=None): s.vars = {}; s.parent = parent
    def lookup(s, name):
        e = s
        while e is not None:
            v = e.vars.get(name)
            if v is not None: return v
            e = e.parent
        return None


class Function:
    inferred = None; is_lambda = False; initlist = None; is_ctor = False
    static = False; node = None; tv = None; tparams = ()
    def __init__(s, **kw): s.__dict__.update(kw)


class BoundMethod:
    __slots__ = ('func', 'this')
    def __init__(s, func, this): s.func = func; s.this = this


class Builtin:
    def __init__(s, name, fn): s.name = name; s.fn = fn


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
    def __init__(s, name, env): s.name = name; s.env = env; s.acc = {}


class Instance:
    __slots__ = ('cls', 'fields', 'targs', '__weakref__')
    def __init__(s, cls): s.cls = cls; s.fields = {}; s.targs = {}


class InstanceD(Instance):
    __slots__ = ()
    def __del__(s):
        try:
            if _CUR is not None: _CUR.destruct(s)
        except BaseException:
            pass


CALLABLES = (Function, BoundMethod, Builtin)
BRK = ('break',)
CNT = ('continue',)


# ───────────────────────── 렉서 ─────────────────────────
class Tok:
    __slots__ = ('type', 'value', 'line')
    def __init__(s, t, v, l): s.type = t; s.value = v; s.line = l
    def __repr__(s): return '%s:%r' % (s.type, s.value)


KEYWORDS = {'fn', 'class', 'interface', 'extends', 'implements', 'new', 'this', 'super', 'static', 'const',
            'if', 'else', 'while', 'for', 'in', 'break', 'continue', 'return', 'try', 'catch', 'finally',
            'throw', 'property', 'public', 'protected', 'private', 'internal', 'namespace', 'import',
            'true', 'false', 'null', 'is', 'not', 'and', 'or', 'cast', 'constructor', 'destructor', 'operator'}
OPS3 = {'??=', '**=', '//='}
OPS2 = {'==', '!=', '<=', '>=', '&&', '||', '??', '?.', '**', '//', '->', '=>', '|>', '..', '::',
        '+=', '-=', '*=', '/=', '%='}
OPS1 = set('+-*/%=<>!?.,;:()[]{}')
CONT_END = {'+', '-', '*', '/', '%', '=', '<', '>', '==', '!=', '<=', '>=', '&&', '||', '??', '?.', '**', '//',
            '->', '=>', '|>', '..', '::', '+=', '-=', '*=', '/=', '%=', '??=', '**=', '//=', ',', '.', '(', '[', ':'}
CONT_KW = {'and', 'or', 'not', 'is', 'in'}
ESC = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0', '\\': '\\', '"': '"', "'": "'", 'a': '\a', 'b': '\b'}


def lex(src, fname='<main>'):
    toks = []; i = 0; n = len(src); line = 1; depth = 0; stack = []

    def err(m): raise AsterSyntaxError(m, line, fname)

    def read_escape(j):
        # src[j] == '\\'
        if j + 1 >= n: err('문자열이 끝나지 않았습니다')
        e = src[j + 1]
        if e == 'u':
            h = src[j + 2:j + 6]
            try: return chr(int(h, 16)), j + 6
            except ValueError: err('잘못된 \\u 이스케이프')
        if e in ESC: return ESC[e], j + 2
        err('알 수 없는 이스케이프: \\' + e)

    while i < n:
        c = src[i]
        if c in ' \t\r':
            i += 1; continue
        if c == '\n':
            line += 1; i += 1
            if depth > 0: continue
            last = toks[-1] if toks else None
            if last is None or last.type == 'nl': continue
            if (last.type == 'op' and last.value in CONT_END) or (last.type == 'kw' and last.value in CONT_KW): continue
            j = i
            while j < n and src[j] in ' \t\r\n': j += 1
            nx = src[j:j + 4]
            if nx.startswith(('|>', '?.', '&&', '||', '??', 'and ', 'or ')) or (nx[:1] == '.' and nx[1:2].isalpha()):
                continue
            toks.append(Tok('nl', '\n', line - 1)); continue
        if c == '#':
            while i < n and src[i] != '\n': i += 1
            continue
        if c == '/' and src.startswith('/*', i):
            j = src.find('*/', i + 2)
            if j < 0: err('블록 주석이 닫히지 않았습니다')
            line += src.count('\n', i, j); i = j + 2; continue
        if c.isdigit():
            j = i
            if c == '0' and src[i + 1:i + 2] in ('x', 'X') and src[i + 1:i + 2] != '':
                j = i + 2
                while j < n and src[j] in '0123456789abcdefABCDEF_': j += 1
                toks.append(Tok('lit', int(src[i + 2:j].replace('_', ''), 16), line)); i = j; continue
            while j < n and (src[j].isdigit() or src[j] == '_'): j += 1
            isf = False
            if j + 1 < n and src[j] == '.' and src[j + 1].isdigit():
                isf = True; j += 1
                while j < n and (src[j].isdigit() or src[j] == '_'): j += 1
            if j < n and src[j] in 'eE':
                k = j + 1
                if k < n and src[k] in '+-': k += 1
                if k < n and src[k].isdigit():
                    isf = True; j = k
                    while j < n and src[j].isdigit(): j += 1
            text = src[i:j].replace('_', '')
            suf = ''
            if j < n and src[j] in 'fFmM' and not (j + 1 < n and (src[j + 1].isalnum() or src[j + 1] == '_')):
                suf = src[j].lower(); j += 1
            if j < n and (src[j].isalpha() or src[j] == '_'): err('숫자 리터럴 뒤에 잘못된 문자가 있습니다')
            try:
                if suf == 'f': val = mkf32(float(text))
                elif suf == 'm': val = Decimal(text)
                elif isf: val = float(text)
                else: val = int(text)
            except (ValueError, InvalidOperation):
                err('잘못된 숫자 리터럴: ' + text)
            toks.append(Tok('lit', val, line)); i = j; continue
        if c.isalpha() or c == '_':
            j = i
            while j < n and (src[j].isalnum() or src[j] == '_'): j += 1
            w = src[i:j]
            toks.append(Tok('kw' if w in KEYWORDS else 'id', w, line)); i = j; continue
        if c == '"':
            j = i + 1; buf = []
            while True:
                if j >= n or src[j] == '\n': err('문자열이 닫히지 않았습니다')
                if src[j] == '"': break
                if src[j] == '\\':
                    ch, j = read_escape(j); buf.append(ch)
                else:
                    buf.append(src[j]); j += 1
            toks.append(Tok('lit', ''.join(buf), line)); i = j + 1; continue
        if c == "'":
            j = i + 1
            if j >= n: err('char 리터럴이 닫히지 않았습니다')
            if src[j] == '\\': ch, j = read_escape(j)
            else: ch = src[j]; j += 1
            if j >= n or src[j] != "'": err("char 리터럴은 문자 하나여야 합니다 ('A')")
            toks.append(Tok('lit', Char(ch), line)); i = j + 1; continue
        three = src[i:i + 3]; two = src[i:i + 2]
        if three in OPS3: op = three
        elif two in OPS2: op = two
        elif c in OPS1: op = c
        else: err('알 수 없는 문자: %r' % c)
        if op in ('(', '['): depth += 1
        elif op in (')', ']'): depth = max(0, depth - 1)
        elif op == '{': stack.append(depth); depth = 0
        elif op == '}': depth = stack.pop() if stack else 0
        toks.append(Tok('op', op, line)); i += len(op)
    toks.append(Tok('nl', '\n', line)); toks.append(Tok('eof', None, line))
    return toks


# ───────────────────────── AST ─────────────────────────
class Node:
    __slots__ = ('line',)


def mk(name, *fields):
    def init(self, *a, line=0):
        for f in fields: setattr(self, f, None)
        for f, v in zip(fields, a): setattr(self, f, v)
        self.line = line
    return type(name, (Node,), {'__slots__': tuple(fields), '__init__': init})


Lit = mk('Lit', 'v'); Name = mk('Name', 'name'); ListLit = mk('ListLit', 'items'); MapLit = mk('MapLit', 'pairs')
SetLit = mk('SetLit', 'items'); TupleLit = mk('TupleLit', 'items'); Unary = mk('Unary', 'op', 'e')
Binary = mk('Binary', 'op', 'l', 'r'); Logic = mk('Logic', 'op', 'l', 'r'); Coal = mk('Coal', 'l', 'r')
Pipe = mk('Pipe', 'l', 'r'); RangeN = mk('RangeN', 'l', 'r'); IsN = mk('IsN', 'e', 'ty', 'neg')
InN = mk('InN', 'e', 'c', 'neg'); Assign = mk('Assign', 'op', 'target', 'value')
Call = mk('Call', 'fn', 'args', 'targs'); Member = mk('Member', 'obj', 'name', 'safe')
Index = mk('Index', 'obj', 'idx'); Chain = mk('Chain', 'e'); NewN = mk('NewN', 'ty', 'args')
CastN = mk('CastN', 'ty', 'e'); LambdaN = mk('LambdaN', 'params', 'rtype', 'expr', 'body')
ThisN = mk('ThisN'); SuperN = mk('SuperN', 'ty')
VarDecl = mk('VarDecl', 'ty', 'name', 'init', 'const'); ExprStmt = mk('ExprStmt', 'e')
Block = mk('Block', 'stmts', 'fns', 'classes'); IfN = mk('IfN', 'c', 't', 'e'); WhileN = mk('WhileN', 'c', 'b')
ForN = mk('ForN', 'init', 'c', 'step', 'b'); ForEachN = mk('ForEachN', 'ty', 'name', 'it', 'b')
BreakN = mk('BreakN'); ContinueN = mk('ContinueN'); ReturnN = mk('ReturnN', 'e'); ThrowN = mk('ThrowN', 'e')
TryN = mk('TryN', 'b', 'catches', 'fin')
FuncDecl = mk('FuncDecl', 'name', 'tparams', 'params', 'rtype', 'body', 'expr', 'mods')
ClassDecl = mk('ClassDecl', 'name', 'kind', 'tparams', 'bases', 'ifaces', 'members', 'mods')
NamespaceN = mk('NamespaceN', 'path', 'body'); ImportN = mk('ImportN', 'target', 'isfile')
Param = mk('Param', 'ty', 'name', 'default'); FieldD = mk('FieldD', 'mods', 'ty', 'name', 'init')
PropD = mk('PropD', 'mods', 'ty', 'name', 'getter', 'setter', 'init')
CtorD = mk('CtorD', 'mods', 'params', 'initlist', 'body'); DtorD = mk('DtorD', 'body')

ACCESS = ('public', 'protected', 'private', 'internal', 'file')
MODS = {'public', 'protected', 'private', 'internal', 'static', 'const'}
DECLKW = {'class', 'interface', 'fn', 'static', 'const', 'property', 'public', 'protected', 'private', 'internal'}
ASSIGN_OPS = {'=', '+=', '-=', '*=', '/=', '//=', '%=', '**=', '??='}
CMP = {'==', '!=', '<', '>', '<=', '>='}


def access_of(mods, default):
    for a in ACCESS:
        if a in mods: return a
    return default


# ───────────────────────── 파서 ─────────────────────────
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
        if t.type != 'id': s.err('타입 이름이 필요합니다')
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
                    tg = s.adv().value; s.end_stmt(); return ImportN(tg, True, line=line)
                path = [s.expect_id()]
                while s.accept_op('.'): path.append(s.expect_id())
                s.end_stmt(); return ImportN(path, False, line=line)
        d = s.try_var_decl(mods)
        if d is not None: return d
        e = s.parse_expr(); s.end_stmt()
        return ExprStmt(e, line=line)

    def try_var_decl(s, mods):
        start = s.p; t = s.tok
        if t.type != 'id': return None
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


# ───────────────────────── 인터프리터 ─────────────────────────
def f32str(x):
    if x != x: return 'NaN'
    if x in (math.inf, -math.inf): return 'Infinity' if x > 0 else '-Infinity'
    s = repr(float(x))
    for p in range(1, 10):
        c = '%.*g' % (p, x)
        if mkf32(float(c)) == x: s = c; break
    if 'e' not in s and '.' not in s: s += '.0'
    return s


def fmt_float(x):
    if x != x: return 'NaN'
    if x in (math.inf, -math.inf): return 'Infinity' if x > 0 else '-Infinity'
    return repr(float(x))


def esc_str(v):
    return v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')


def txt(v): return v.c if type(v) is Char else v


class Interp:
    def __init__(s):
        global _CUR
        _CUR = s
        s.line = 0; s.depth = 0; s.ctx_cls = None; s.ctx_file = '<main>'; s.tv = {}
        s.root = Env(); s.glob = Env(s.root); s.imported = set(); s.repl = False
        s.EV = {
            Lit: lambda n, e: n.v, Name: s.e_name, ListLit: s.e_list, MapLit: s.e_map, SetLit: s.e_set,
            TupleLit: s.e_tuple, Unary: s.e_unary, Binary: s.e_binary, Logic: s.e_logic, Coal: s.e_coal,
            Pipe: s.e_pipe, RangeN: s.e_range, IsN: s.e_is, InN: s.e_in, Assign: s.e_assign, Call: s.e_call,
            Member: s.e_member, Index: s.e_index, Chain: s.e_chain, NewN: s.e_new, CastN: s.e_cast,
            LambdaN: s.e_lambda, ThisN: s.e_this,
        }
        s.EX = {
            VarDecl: s.x_var, ExprStmt: s.x_expr, Block: s.x_block, IfN: s.x_if, WhileN: s.x_while, ForN: s.x_for,
            ForEachN: s.x_foreach, BreakN: lambda n, e: BRK, ContinueN: lambda n, e: CNT, ReturnN: s.x_return,
            ThrowN: s.x_throw, TryN: s.x_try, FuncDecl: s.x_func, ClassDecl: s.x_class,
            NamespaceN: s.x_namespace, ImportN: s.x_import,
        }
        s.install_builtins()
        s.run_source(PRELUDE, '<prelude>', s.root)

    def ev(s, n, env): return s.EV[n.__class__](n, env)

    def rt(s, kind, msg): return AsterError(kind, msg)

    # ── 타입 유틸 ──
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

    # ── 클래스 조회 ──
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

    # ── 타입 강제(coerce) ──
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

    # ── 연산 ──
    def eq(s, a, b):
        if a is None or b is None: return a is b
        if isinstance(a, Instance):
            m = s.find_member(a.cls, 'operator==')
            if m: return s.call_function(m[0].func, [b], a) is True
            return a is b
        if isinstance(b, Instance): return False
        ka = KIND.get(type(a)); kb = KIND.get(type(b))
        if ka != kb:
            if ka in NUMERIC and kb in NUMERIC:
                raise s.rt('TypeError', '%s 와(과) %s 는 비교할 수 없습니다 (cast 사용)' % (ka, kb))
            return False
        return a == b

    def compare(s, op, a, b):
        if isinstance(a, Instance):
            m = s.find_member(a.cls, 'operator' + op)
            if m: return s.call_function(m[0].func, [b], a)
            raise s.rt('TypeError', '%s 에는 operator%s 가 정의되지 않았습니다' % (a.cls.name, op))
        ka = KIND.get(type(a)); kb = KIND.get(type(b))
        if ka in ('string', 'char') and kb in ('string', 'char'): x, y = txt(a), txt(b)
        elif ka == kb and ka in NUMERIC: x, y = a, b
        else: raise s.rt('TypeError', "'%s' 연산을 %s, %s 에 적용할 수 없습니다" % (op, ka or s.type_of(a).name, kb or s.type_of(b).name))
        if op == '<': return x < y
        if op == '>': return x > y
        if op == '<=': return x <= y
        return x >= y

    def arith(s, op, a, b):
        if isinstance(a, Instance):
            m = s.find_member(a.cls, 'operator' + op)
            if m: return s.call_function(m[0].func, [b], a)
            raise s.rt('TypeError', '%s 에는 operator%s 가 정의되지 않았습니다' % (a.cls.name, op))
        ka = KIND.get(type(a)); kb = KIND.get(type(b))
        if op == '+' and ka in ('string', 'char') and kb in ('string', 'char'): return txt(a) + txt(b)
        if op == '*' and ka == 'string' and kb == 'int': return a * b
        if op == '*' and ka == 'int' and kb == 'string': return b * a
        if ka != kb or ka not in NUMERIC:
            raise s.rt('TypeError', "'%s' 연산을 %s, %s 에 적용할 수 없습니다" % (op, ka or s.type_of(a).name, kb or s.type_of(b).name))
        try:
            if op == '+': r = a + b
            elif op == '-': r = a - b
            elif op == '*': r = a * b
            elif op == '/':
                if b == 0: raise ZeroDivisionError
                r = a / b if ka != 'int' else float(a) / b if abs(a) < 2 ** 53 else a / b
            elif op == '//':
                if b == 0: raise ZeroDivisionError
                if ka == 'decimal': r = (a / b).to_integral_value(ROUND_FLOOR)
                else: r = a // b
            elif op == '%':
                if b == 0: raise ZeroDivisionError
                r = a % b
            elif op == '**':
                if ka == 'int': r = a ** b if b >= 0 else float(a) ** b
                elif ka == 'decimal': r = a ** b
                else: r = math.pow(a, b)
            else: raise s.rt('TypeError', '알 수 없는 연산자 ' + op)
        except ZeroDivisionError:
            raise s.rt('ZeroDivisionError', '0 으로 나눌 수 없습니다')
        except (OverflowError, ValueError):
            raise s.rt('RuntimeError', '수치 연산 오류 (%s %s %s)' % (a, op, b))
        if ka == 'float': return mkf32(r)
        return r

    def binop(s, op, a, b):
        if op == '==': return s.eq(a, b)
        if op == '!=': return not s.eq(a, b)
        if op in ('<', '>', '<=', '>='): return s.compare(op, a, b)
        return s.arith(op, a, b)

    def cond(s, v):
        if v is True: return True
        if v is False: return False
        raise s.rt('TypeError', '조건식은 bool 이어야 하지만 %s 값이 주어졌습니다' % fmt(s.type_of(v)))

    def contains(s, c, x):
        t = type(c)
        if t in (AList, AArray, tuple): return any(s.eq(x, y) for y in c)
        if t in (ASet, AMap):
            try: return x in c
            except TypeError: raise s.rt('TypeError', '해시할 수 없는 값입니다')
        if t is str:
            if type(x) not in (str, Char): raise s.rt('TypeError', "문자열 안에서는 string/char 만 찾을 수 있습니다")
            return txt(x) in c
        if t is Rng: return type(x) is int and c.a <= x < c.b
        raise s.rt('TypeError', "'in' 은(는) %s 에 사용할 수 없습니다" % fmt(s.type_of(c)))

    def iter_values(s, v):
        t = type(v)
        if t is Rng: return range(v.a, v.b)
        if t in (AList, AArray, tuple): return list(v)
        if t in (ASet, AMap): return list(v.keys())
        if t is str: return [Char(c) for c in v]
        raise s.rt('TypeError', '%s 은(는) 순회할 수 없습니다' % fmt(s.type_of(v)))

    # ── 문자열 변환 ──
    def to_str(s, v, nested=False):
        if v is None: return 'null'
        t = type(v)
        if t is str: return '"' + esc_str(v) + '"' if nested else v
        if t is bool: return 'true' if v else 'false'
        if t is int: return str(v)
        if t is float: return fmt_float(v)
        if t is F32: return f32str(v)
        if t is Decimal: return format(v, 'f')
        if t is Char: return "'" + v.c + "'" if nested else v.c
        if t in (AList, AArray): return '[' + ', '.join(s.to_str(x, True) for x in v) + ']'
        if t is tuple: return '(' + ', '.join(s.to_str(x, True) for x in v) + (',' if len(v) == 1 else '') + ')'
        if t is ASet: return '{' + ', '.join(s.to_str(x, True) for x in v) + '}'
        if t is AMap: return '{' + ', '.join('%s: %s' % (s.to_str(k, True), s.to_str(x, True)) for k, x in v.items()) + '}'
        if t is Rng: return '%d..%d' % (v.a, v.b)
        if isinstance(v, Instance):
            m = s.find_member(v.cls, 'toString')
            if m and m[0].kind == 'method':
                r = s.call_function(m[0].func, [], v)
                return r if type(r) is str else s.to_str(r)
            return '<%s>' % v.cls.name
        if t is ClassObj: return '<class %s>' % v.name
        if t is NamespaceObj: return '<namespace %s>' % v.name
        if t in CALLABLES:
            return '<fn %s>' % getattr(v, 'name', getattr(getattr(v, 'func', None), 'name', '?'))
        return str(v)

    # ───────── 식 평가 ─────────
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

    # ── 인덱싱 ──
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

    # ───────── 문장 실행 ─────────
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

    # ───────── 호출 ─────────
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

    # ───────── 클래스 ─────────
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

    # ── 인스턴스 생성 ──
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

    # ───────── 네임스페이스 / 임포트 / 실행 ─────────
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

    def x_namespace(s, n, env):
        ns = s.get_ns(n.path)
        for st in n.body.stmts:
            c = st.__class__
            if c in (FuncDecl, ClassDecl):
                ns.acc[st.name] = (access_of(st.mods, 'internal'), s.ctx_file)
            elif c is VarDecl: ns.acc[st.name] = ('internal', s.ctx_file)
        s.hoist(n.body, ns.env)
        return s.exec_stmts(n.body.stmts, ns.env)

    def x_import(s, n, env):
        if n.isfile:
            base = os.path.dirname(os.path.abspath(s.ctx_file)) if os.path.exists(s.ctx_file) else os.getcwd()
            p = os.path.join(base, n.target)
            if not os.path.exists(p): p = os.path.abspath(n.target)
            if not os.path.exists(p): raise s.rt('NameError', "import 파일을 찾을 수 없습니다: " + n.target)
            ap = os.path.abspath(p)
            if ap in s.imported: return None
            s.imported.add(ap)
            with open(ap, encoding='utf-8') as fh: src = fh.read()
            s.run_source(src, ap, s.glob)
            return None
        cur = s.glob; ns = None
        for p in n.target:
            slot = cur.vars.get(p) or s.glob.vars.get(p) if cur is s.glob else cur.vars.get(p)
            if slot is None or not isinstance(slot[0], NamespaceObj): raise s.rt('NameError', "네임스페이스를 찾을 수 없습니다: " + '.'.join(n.target))
            ns = slot[0]; cur = ns.env
        for k, slot in ns.env.vars.items():
            a = ns.acc.get(k)
            if a and (a[0] == 'private' or (a[0] == 'file' and a[1] != s.ctx_file)): continue
            if k not in env.vars: env.vars[k] = slot

    def run_source(s, src, fname, env):
        toks = lex(src, fname)
        prog = Parser(toks, fname).parse_program()
        saved = s.ctx_file; s.ctx_file = fname
        try:
            s.hoist(prog, env)
            return s.exec_stmts(prog.stmts, env)
        finally:
            s.ctx_file = saved

    # ───────── 내장 컬렉션 생성 / 형변환 ─────────
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

    # ───────── 내장 멤버 / 함수 ─────────
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
            'substring': substring, 'join': join,
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


PRELUDE = '''
class Error {
    public string message = ""
    constructor(string message = "") { this.message = message }
    public fn toString() -> string { return this.message }
}
class RuntimeError extends Error {}
class TypeError extends Error {}
class ValueError extends Error {}
class NullError extends Error {}
class IndexError extends Error {}
class KeyError extends Error {}
class ZeroDivisionError extends Error {}
class NameError extends Error {}
class AccessError extends Error {}
'''


DEMO = r'''
interface Movable {
    fn move(int x, int y) -> void
}

class Entity {
    protected int x = 0
    protected int y = 0
    public fn getPosition() { return (this.x, this.y) }
}

class Player extends Entity implements Movable {
    private string name
    private int health = 100
    public property int Score { get; private set; } = 0

    constructor(string name) { this.name = name }

    public fn move(int x, int y) -> void { this.x += x; this.y += y }

    public fn takeDamage(int amount) -> void {
        this.health -= amount
        if (this.health <= 0) { print("Player defeated") }
    }
    public fn addScore(int n) -> void { this.Score += n }
    public fn toString() -> string { return this.name + "(" + str(this.health) + ")" }
}

fn identity<T>(T value) -> T { return value }
fn doubleValue(int v) -> int { return v * 2 }

fn main() -> void {
    Player player = new Player("Aster")
    player.move(10, 5)
    player.takeDamage(20)
    player.addScore(7)
    print(player, player.getPosition(), player.Score)

    int? optionalValue = null
    int result = optionalValue ?? 0
    print("result:", result, identity<int>(42), 10 |> doubleValue)

    list<int> nums = [1, 2, 3, 4, 5]
    print(nums.map(x => x * x).filter(x => x > 4), (1..5).toList())
    map<string, int> scores = { "Alice": 100, "Bob": 90 }
    for (name in scores) { print(name, scores[name]) }

    try { throw "Something went wrong" }
    catch (error) { print("caught:", error) }
    finally { print("Finished") }

    try { int bad = cast<int>("abc") }
    catch (ValueError e) { print("ValueError:", e) }
    print(cast<int?>("abc"), 7 // 2, 7 / 2, 2 ** 10, 10.5m + 1.5m)
}

main()
'''


def report(ip, ex):
    if isinstance(ex, AsterSyntaxError):
        sys.stderr.write('구문 오류 (%s, 줄 %d): %s\n' % (ex.file, ex.line, ex.msg))
    elif isinstance(ex, AsterError):
        sys.stderr.write('오류 [%s] (%s, 줄 %d): %s\n' % (ex.kind, os.path.basename(str(ex.file)), ex.line, ex.msg))
    elif isinstance(ex, AsterThrow):
        try: m = ip.to_str(ex.value)
        except BaseException: m = '?'
        sys.stderr.write('처리되지 않은 예외 [%s] (줄 %d): %s\n' % (ex.value.cls.name, ex.line, m))
    elif isinstance(ex, RecursionError):
        sys.stderr.write('오류 [RuntimeError]: 재귀가 너무 깊습니다\n')


def run_main(argv, result):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    code = 0
    try:
        ip = Interp()
    except BaseException as ex:
        sys.stderr.write('초기화 실패: %r\n' % (ex,)); result.append(1); return
    try:
        if argv and argv[0] == '--demo':
            ip.run_source(DEMO, '<demo>', ip.glob)
        elif argv and argv[0] == '-c' and len(argv) > 1:
            ip.run_source(argv[1], '<cmd>', ip.glob)
        elif argv and argv[0] in ('-v', '--version'):
            print('Aster ' + VERSION)
        elif argv:
            path = argv[0]
            with open(path, encoding='utf-8') as fh: src = fh.read()
            ip.run_source(src, os.path.abspath(path), ip.glob)
        else:
            ip.repl = True
            print('Aster %s REPL — 종료: exit() 또는 Ctrl-D' % VERSION)
            buf = ''
            while True:
                try: line = input('... ' if buf else '>>> ')
                except EOFError: print(); break
                buf += line + '\n'
                if buf.count('{') > buf.count('}') or buf.count('(') > buf.count(')') or buf.count('[') > buf.count(']'): continue
                src, buf = buf, ''
                if not src.strip(): continue
                try: ip.run_source(src, '<repl>', ip.glob)
                except ExitProgram: break
                except (AsterSyntaxError, AsterError, AsterThrow, RecursionError) as ex: report(ip, ex)
    except ExitProgram as ex:
        code = ex.code if isinstance(ex.code, int) else 0
    except (AsterSyntaxError, AsterError, AsterThrow, RecursionError) as ex:
        sys.stdout.flush(); report(ip, ex); code = 1
    except FileNotFoundError as ex:
        sys.stderr.write('파일을 찾을 수 없습니다: %s\n' % ex.filename); code = 1
    sys.stdout.flush()
    try:
        ip.glob.vars.clear(); gc.collect()
        sys.stdout.flush()
    except Exception: pass
    result.append(code)


def main():
    sys.setrecursionlimit(400000)
    result = []
    for size in (512, 256, 64, 16):
        try:
            threading.stack_size(size * 1024 * 1024); break
        except (ValueError, RuntimeError): continue
    th = threading.Thread(target=run_main, args=(sys.argv[1:], result))
    th.start(); th.join()
    sys.exit(result[0] if result else 1)


if __name__ == '__main__':
    main()
