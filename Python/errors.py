"""Python/errors.py — 언어 수준 예외와 내부 제어 신호 (CPython 의 Python/errors.c)."""
from Python.state import state

class AsterSyntaxError(Exception):
    def __init__(s, msg, line=0, file=''):
        Exception.__init__(s, msg); s.msg = msg; s.line = line; s.file = file

class AsterError(Exception):
    def __init__(s, kind, msg):
        Exception.__init__(s, msg); s.kind = kind; s.msg = msg
        s.line = state.interp.line if state.interp else 0
        s.file = state.interp.ctx_file if state.interp else ''

class AsterThrow(Exception):
    def __init__(s, value):
        Exception.__init__(s); s.value = value
        s.line = state.interp.line if state.interp else 0

class ShortCircuit(Exception):
    pass

class ExitProgram(Exception):
    def __init__(s, code=0):
        Exception.__init__(s); s.code = code
