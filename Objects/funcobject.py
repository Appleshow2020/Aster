"""Objects/funcobject.py — 함수·바운드 메서드·내장 함수 객체."""
class Function:
    inferred = None; is_lambda = False; initlist = None; is_ctor = False
    static = False; node = None; tv = None; tparams = ()
    def __init__(s, **kw): s.__dict__.update(kw)

class BoundMethod:
    __slots__ = ('func', 'this')
    def __init__(s, func, this): s.func = func; s.this = this

class Builtin:
    def __init__(s, name, fn): s.name = name; s.fn = fn

CALLABLES = (Function, BoundMethod, Builtin)
