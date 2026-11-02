# Aster 인터프리터 내부 구조 (CPython 대응표)

```
Aster/
├─ run.py                   Programs/python.c      최상위 실행기 (-c -m --tokens --ast REPL)
├─ Grammar/Grammar.txt      Grammar/Grammar        EBNF 문법
├─ Parser/
│   ├─ tokenizer.py         Parser/tokenizer.c     소스 → 토큰 (줄 잇기 규칙 포함)
│   ├─ ast.py               Parser/Python.asdl     AST 노드 정의
│   └─ parser.py            Parser/parser.c        재귀 하강 파서
├─ Objects/
│   ├─ object.py            Objects/object.c       Char, F32, list/map/set/array, TypeRef
│   ├─ funcobject.py        Objects/funcobject.c   Function, BoundMethod, Builtin
│   ├─ frameobject.py       Objects/frameobject.c  Env (스코프 체인)
│   ├─ classobject.py       Objects/classobject.c  ClassObj/Instance + ClassMixin (MRO, 접근 제한, 생성)
│   ├─ moduleobject.py      Objects/moduleobject.c 모듈 객체, 네이티브 모듈 정의 도우미
│   ├─ typeobject.py        Objects/typeobject.c   타입 추론·coerce·제네릭 바인딩
│   └─ abstract.py          Objects/abstract.c     산술·비교·포함·순회·문자열화
├─ Python/
│   ├─ ceval.py             Python/ceval.c         식 평가, 함수 호출
│   ├─ executor.py          (compile/ceval 문장부)  제어 흐름, 선언, try/catch
│   ├─ importer.py          Python/import.c        namespace, 모듈 탐색·캐시
│   ├─ bltinmodule.py       Python/bltinmodule.c   내장 함수, 내장 타입 메서드
│   ├─ errors.py            Python/errors.c        AsterError / AsterThrow / 제어 신호
│   ├─ state.py             PyThreadState          현재 인터프리터 포인터
│   └─ pythonrun.py         Python/pythonrun.c     Interp 조립, report, main
├─ Modules/                 Modules/               네이티브 모듈 + config 표(__init__.py)
├─ Lib/                     Lib/                   Aster 로 쓴 표준 라이브러리, _prelude.ast, test/
├─ Tools/                   Tools/                 runtests.py, astdump.py
└─ Doc/                     Doc/
```

## 설계 원칙 (CPython 에서 가져온 것)
1. **작은 코어 + 두터운 라이브러리.** 코어는 타입·클래스·호출·예외만 안다. `Stack`, `Counter` 같은 것은 `Lib/*.ast` 에서 언어 자신으로 구현한다.
2. **내장 예외 계층도 언어로 정의.** `Lib/_prelude.ast` 가 시작 시 읽혀 `Error` 계열을 만든다. 인터프리터는 `AsterError(kind, msg)` 를 던지고, `catch` 시점에 같은 이름의 클래스 인스턴스로 변환한다.
3. **네이티브 모듈은 표(PyMethodDef)로.** `ModuleDef` 에 `@mod.fn(argc=...)` 로 함수를 등록하고 `init(ip)` 가 멤버 사전을 돌려준다. 새 모듈은 파일 하나 + `Modules/__init__.py` 의 한 줄이면 된다.
4. **탐색 경로는 데이터.** `sys.path` 는 실제 `list<string>` 이라 `sys.path.add(dir)` 로 런타임에 바꿀 수 있다.
5. **믹스인으로 나눈 평가기.** `Interp` 는 역할별 믹스인의 조립물이다. 각 파일은 헤더의 상위 계층만 import 하므로 순환 import 가 없다
   (`Objects` ← `Python`, `Parser` 는 `Objects`/`Python.errors` 에만 의존).
6. **실행 단위가 파일.** 모듈은 자기 전역 스코프(부모는 내장 스코프)를 가진다. 같은 모듈은 한 번만 실행되고 `ip.modules` 에 캐시된다.

## 새 네이티브 모듈 추가 예
```python
# Modules/hellomodule.py
from Objects.moduleobject import ModuleDef, string
mod = ModuleDef('hello')

@mod.fn(argc=1)
def greet(ip, args): return 'hi ' + string(ip, args[0], 'hello.greet')

def init(ip): return mod.members
```
`Modules/__init__.py` 의 `NATIVE` 에 `'hello': 'Modules.hellomodule'` 를 추가하면 `import hello;` 가 동작한다.
