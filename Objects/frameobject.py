"""Objects/frameobject.py — 변수 스코프(프레임) 객체."""
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
