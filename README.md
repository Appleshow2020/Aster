# Aster 0.4

Python 의 간결함, C# 의 객체·타입 시스템, Java 의 명시적 구조를 섞은 정적 타입 범용 언어와 그 인터프리터(Python 3.8+, 외부 의존성 없음).
CPython 저장소 구조를 따라 `Parser/ Objects/ Python/ Modules/ Lib/` 로 나뉘어 있고, 표준 라이브러리 일부는 Aster 자신으로 작성되어 있다.

```
python run.py hello.ast         # 파일 실행
python run.py -c 'print(1+2)'   # 코드 실행
python run.py -m statistics     # Lib 모듈 실행
python run.py --tokens f.ast    # 토큰 덤프          python run.py --ast f.ast   # AST 덤프
python run.py                   # REPL
python Tools/runtests.py        # 회귀 테스트 (또는 make test)
python run.py Lib/test/demo.ast # 데모
```

```
import math
from collections import Stack

class Shape { public fn area() -> double { return 0.0 } }
class Circle extends Shape {
    private double r
    constructor(double r) { this.r = r }
    public fn area() -> double { return math.pi * this.r ** 2.0 }
}

var s = new Stack<Shape>()
s.push(new Circle(2.0))
print(s.pop().area() |> math.floor)
```

* 언어 정의: `Doc/reference.md`, 문법: `Grammar/Grammar.txt`, 내부 구조와 확장법: `Doc/internals.md`
* 타입 검사는 별도 컴파일 단계가 아니라 **문장이 실행될 때** 수행됩니다.
