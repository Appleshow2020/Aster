"""Parser/ast.py — 추상 구문 트리 노드 정의 (CPython 의 Parser/Python.asdl 에 해당)."""
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
NamespaceN = mk('NamespaceN', 'path', 'body'); ImportN = mk('ImportN', 'target', 'isfile', 'alias', 'names')
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
