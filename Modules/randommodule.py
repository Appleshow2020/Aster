"""Modules/randommodule.py — random 모듈 (CPython 의 Modules/_randommodule.c)."""
import random as _r
from Objects.object import *
from Objects.moduleobject import ModuleDef, number, integer

mod = ModuleDef('random')
_rng = _r.Random()


@mod.fn(argc=1)
def seed(ip, args): _rng.seed(integer(ip, args[0], 'random.seed'))


@mod.fn(argc=0)
def random(ip, args): return _rng.random()


@mod.fn(argc=2)
def randint(ip, args):
    a = integer(ip, args[0], 'random.randint'); b = integer(ip, args[1], 'random.randint')
    if a > b: raise ip.rt('ValueError', 'random.randint: 범위가 비어 있습니다')
    return _rng.randint(a, b)


@mod.fn(argc=2)
def uniform(ip, args): return _rng.uniform(float(number(ip, args[0], 'random.uniform')), float(number(ip, args[1], 'random.uniform')))


@mod.fn(argc=1)
def choice(ip, args):
    seq = ip.iter_values(args[0])
    if not seq: raise ip.rt('IndexError', 'random.choice: 빈 시퀀스입니다')
    return _rng.choice(seq)


@mod.fn(argc=1)
def shuffle(ip, args):
    if type(args[0]) not in (AList, AArray): raise ip.rt('TypeError', 'random.shuffle: list/array 가 필요합니다')
    _rng.shuffle(args[0])


def init(ip): return mod.members
