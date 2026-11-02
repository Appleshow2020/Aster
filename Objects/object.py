"""Objects/object.py — 기본 값 표현과 타입 서술자 (CPython 의 Objects/object.c + longobject/floatobject/listobject 등)."""
import math, struct
from decimal import Decimal


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

BRK = ('break',)
CNT = ('continue',)

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
