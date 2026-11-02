"""Objects/abstract.py — 추상 객체 계층: 산술·비교·포함·순회·문자열화 (CPython 의 Objects/abstract.c)."""
import sys, os, math, struct, functools, operator, gc
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from Python.state import state
from Python.errors import *
from Objects.object import *
from Objects.funcobject import *
from Objects.frameobject import *
from Objects.classobject import *


class AbstractMixin:
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
