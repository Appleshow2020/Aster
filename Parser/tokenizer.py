"""Parser/tokenizer.py — 소스 텍스트를 토큰으로 변환 (CPython 의 Parser/tokenizer.c)."""
from Objects.object import *
from Python.errors import *
from decimal import Decimal, InvalidOperation


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
