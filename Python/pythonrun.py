"""Python/pythonrun.py — 인터프리터 조립과 최상위 실행 루프 (CPython 의 Python/pythonrun.c + Programs/python.c).

Interp 는 역할별 믹스인을 조립한 클래스다.
  Objects/typeobject.py   TypeMixin      타입 추론 · coerce · 제네릭 바인딩
  Objects/abstract.py     AbstractMixin  산술 · 비교 · 순회 · 문자열화
  Objects/classobject.py  ClassMixin     클래스 모델 (MRO, 접근 제한, 생성)
  Python/ceval.py         EvalMixin      식 평가 · 함수 호출
  Python/executor.py      ExecMixin      문장 실행 · 예외 처리
  Python/import.py        ImportMixin    네임스페이스 · 모듈 임포트
  Python/bltinmodule.py   BuiltinsMixin  내장 함수 · 내장 타입 메서드
"""
import sys, os, gc, threading
from Python.state import state
from Python.errors import *
from Objects.object import *
from Objects.funcobject import *
from Objects.frameobject import *
from Objects.classobject import *
from Objects.typeobject import TypeMixin
from Objects.abstract import AbstractMixin
from Python.ceval import EvalMixin
from Python.executor import ExecMixin
from Python.importer import ImportMixin
from Python.bltinmodule import BuiltinsMixin
from Parser.ast import *

VERSION = "0.4"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(ROOT, 'Lib')
PRELUDE_PATH = os.path.join(LIB_DIR, '_prelude.ast')


class Interp(TypeMixin, AbstractMixin, EvalMixin, ExecMixin, ClassMixin, ImportMixin, BuiltinsMixin):
    def __init__(s, argv=None, script=None):
        state.interp = s
        s.line = 0; s.depth = 0; s.ctx_cls = None; s.ctx_file = '<main>'; s.tv = {}
        s.root = Env(); s.glob = Env(s.root); s.imported = set(); s.repl = False
        s.argv = AList(list(argv or []), T_STRING); s.modules = {}
        s.path = AList([], T_STRING)
        if script: s.path.append(os.path.dirname(os.path.abspath(script)))
        s.path.append(LIB_DIR); s.path.append(os.getcwd())
        s.EV = {
            Lit: lambda n, e: n.v, Name: s.e_name, ListLit: s.e_list, MapLit: s.e_map, SetLit: s.e_set,
            TupleLit: s.e_tuple, Unary: s.e_unary, Binary: s.e_binary, Logic: s.e_logic, Coal: s.e_coal,
            Pipe: s.e_pipe, RangeN: s.e_range, IsN: s.e_is, InN: s.e_in, Assign: s.e_assign, Call: s.e_call,
            Member: s.e_member, Index: s.e_index, Chain: s.e_chain, NewN: s.e_new, CastN: s.e_cast,
            LambdaN: s.e_lambda, ThisN: s.e_this,
        }
        s.EX = {
            VarDecl: s.x_var, ExprStmt: s.x_expr, Block: s.x_block, IfN: s.x_if, WhileN: s.x_while, ForN: s.x_for,
            ForEachN: s.x_foreach, BreakN: lambda n, e: BRK, ContinueN: lambda n, e: CNT, ReturnN: s.x_return,
            ThrowN: s.x_throw, TryN: s.x_try, FuncDecl: s.x_func, ClassDecl: s.x_class,
            NamespaceN: s.x_namespace, ImportN: s.x_import,
        }
        s.install_builtins()
        with open(PRELUDE_PATH, encoding='utf-8') as fh:
            s.run_source(fh.read(), '<prelude>', s.root)

    def ev(s, n, env): return s.EV[n.__class__](n, env)

    def rt(s, kind, msg): return AsterError(kind, msg)


def report(ip, ex):
    if isinstance(ex, AsterSyntaxError):
        sys.stderr.write('구문 오류 (%s, 줄 %d): %s\n' % (ex.file, ex.line, ex.msg))
    elif isinstance(ex, AsterError):
        sys.stderr.write('오류 [%s] (%s, 줄 %d): %s\n' % (ex.kind, os.path.basename(str(ex.file)), ex.line, ex.msg))
    elif isinstance(ex, AsterThrow):
        try: m = ip.to_str(ex.value)
        except BaseException: m = '?'
        sys.stderr.write('처리되지 않은 예외 [%s] (줄 %d): %s\n' % (ex.value.cls.name, ex.line, m))
    elif isinstance(ex, RecursionError):
        sys.stderr.write('오류 [RuntimeError]: 재귀가 너무 깊습니다\n')


USAGE = """사용법: python run.py [옵션] [파일 [인자...]]
  파일            Aster 소스 실행
  -c 코드         코드 문자열 실행
  -m 모듈         Lib 의 모듈을 스크립트로 실행
  -i              (파일 실행 후 REPL 진입은 지원하지 않음) 인자 없이 실행하면 REPL
  --tokens 파일   토큰 덤프           --ast 파일   AST 덤프
  -V, --version   버전                -h, --help   도움말"""

ERRORS = (AsterSyntaxError, AsterError, AsterThrow, RecursionError)


def run_main(argv, result):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    code = 0; ip = None
    try:
        if argv and argv[0] in ('-V', '--version'):
            print('Aster ' + VERSION); result.append(0); return
        if argv and argv[0] in ('-h', '--help'):
            print(USAGE); result.append(0); return
        script = argv[0] if argv and not argv[0].startswith('-') else None
        ip = Interp(argv if script else (argv[:1] or ['']), script)
        if argv and argv[0] == '-c' and len(argv) > 1:
            ip.run_source(argv[1], '<cmd>', ip.glob)
        elif argv and argv[0] == '-m' and len(argv) > 1:
            path = ip.find_module_file(argv[1])
            if not path: raise AsterError('ImportError', '모듈을 찾을 수 없습니다: ' + argv[1])
            with open(path, encoding='utf-8') as fh: src = fh.read()
            ip.run_source(src, path, ip.glob)
        elif argv and argv[0] in ('--tokens', '--ast') and len(argv) > 1:
            from Parser.tokenizer import lex
            from Parser.parser import Parser
            with open(argv[1], encoding='utf-8') as fh: src = fh.read()
            if argv[0] == '--tokens':
                for t in lex(src, argv[1]): print('%4d  %-4s %r' % (t.line, t.type, t.value))
            else:
                from Tools.astdump import dump
                print(dump(Parser(lex(src, argv[1]), argv[1]).parse_program()))
        elif script:
            with open(script, encoding='utf-8') as fh: src = fh.read()
            ip.run_source(src, os.path.abspath(script), ip.glob)
        else:
            ip.repl = True
            print('Aster %s REPL — 종료: exit() 또는 Ctrl-D' % VERSION)
            buf = ''
            while True:
                try: line = input('... ' if buf else '>>> ')
                except EOFError: print(); break
                buf += line + '\n'
                if buf.count('{') > buf.count('}') or buf.count('(') > buf.count(')') or buf.count('[') > buf.count(']'): continue
                src, buf = buf, ''
                if not src.strip(): continue
                try: ip.run_source(src, '<repl>', ip.glob)
                except ExitProgram: break
                except ERRORS as ex: report(ip, ex)
    except ExitProgram as ex:
        code = ex.code if isinstance(ex.code, int) else 0
    except ERRORS as ex:
        sys.stdout.flush(); report(ip, ex); code = 1
    except FileNotFoundError as ex:
        sys.stderr.write('파일을 찾을 수 없습니다: %s\n' % ex.filename); code = 1
    sys.stdout.flush()
    try:
        if ip is not None: ip.glob.vars.clear()
        gc.collect(); sys.stdout.flush()
    except Exception: pass
    result.append(code)


def main():
    sys.setrecursionlimit(400000)
    result = []
    for size in (512, 256, 64, 16):
        try:
            threading.stack_size(size * 1024 * 1024); break
        except (ValueError, RuntimeError): continue
    th = threading.Thread(target=run_main, args=(sys.argv[1:], result))
    th.start(); th.join()
    sys.exit(result[0] if result else 1)
