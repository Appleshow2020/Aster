"""Tools/astdump.py — AST 를 들여쓰기 트리로 덤프 (CPython 의 ast.dump 에 해당). `python run.py --ast 파일`."""
from Parser.ast import Node
from Objects.object import TypeRef, fmt


def dump(node, indent=0):
    pad = '  ' * indent
    if isinstance(node, Node):
        fields = [f for f in node.__slots__ if f != 'line']
        head = '%s%s (줄 %d)' % (pad, type(node).__name__, node.line)
        parts = [head]
        for f in fields:
            v = getattr(node, f)
            if v is None or v == [] or v == set(): continue
            if isinstance(v, (Node, list, tuple)) and not isinstance(v, str):
                parts.append('%s  .%s:' % (pad, f)); parts.append(dump(v, indent + 2))
            else:
                parts.append('%s  .%s = %s' % (pad, f, _atom(v)))
        return '\n'.join(parts)
    if isinstance(node, (list, tuple)):
        return '\n'.join(dump(x, indent) for x in node) if node else pad + '[]'
    return pad + _atom(node)


def _atom(v):
    if isinstance(v, TypeRef): return fmt(v)
    return repr(v)
