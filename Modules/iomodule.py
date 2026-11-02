"""Modules/iomodule.py — io 모듈: 텍스트 파일 읽기/쓰기 (CPython 의 Modules/_io/)."""
from Objects.object import *
from Objects.moduleobject import ModuleDef, string

mod = ModuleDef('io')


def _wrap(ip, ex): return ip.rt('IOError', '%s: %s' % (ex.strerror or ex, getattr(ex, 'filename', '') or ''))


@mod.fn(argc=1)
def read_file(ip, args):
    try:
        with open(string(ip, args[0], 'io.read_file'), encoding='utf-8') as f: return f.read()
    except OSError as ex: raise _wrap(ip, ex)


@mod.fn(argc=1)
def read_lines(ip, args):
    try:
        with open(string(ip, args[0], 'io.read_lines'), encoding='utf-8') as f: return AList(f.read().splitlines(), T_STRING)
    except OSError as ex: raise _wrap(ip, ex)


@mod.fn(argc=2)
def write_file(ip, args):
    try:
        with open(string(ip, args[0], 'io.write_file'), 'w', encoding='utf-8') as f: f.write(string(ip, args[1], 'io.write_file'))
    except OSError as ex: raise _wrap(ip, ex)


@mod.fn(argc=2)
def append_file(ip, args):
    try:
        with open(string(ip, args[0], 'io.append_file'), 'a', encoding='utf-8') as f: f.write(string(ip, args[1], 'io.append_file'))
    except OSError as ex: raise _wrap(ip, ex)


def init(ip): return mod.members
