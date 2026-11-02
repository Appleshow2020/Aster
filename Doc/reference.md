# Aster 0.4 언어 레퍼런스

0.3 설계 정리본의 미정·제안 항목을 모두 확정한 명세다. 문법의 정식 정의는 `Grammar/Grammar.txt`.

## 1. 기본
| 항목 | 확정 내용 |
|---|---|
| 패러다임 | 객체지향 + 절차적 + 함수형 요소, 인터프리터(Python 구현) |
| 블록 | 중괄호. 들여쓰기는 의미 없음. 한 문장 본문은 중괄호 생략 가능 |
| 문장 끝 | 줄바꿈 또는 `;`. 같은 줄에 여러 문장이면 `;` 필요 |
| 줄 잇기 | 줄이 이항 연산자·`,`·`.`·`(` 로 끝나거나, 다음 줄이 `\|>` `.` `?.` `&&` `\|\|` `??` `and` `or` 로 시작하면 이어짐. `()` `[]` 안은 줄바꿈 무시 |
| 주석 | `# 한 줄`, `/* 여러 줄 */` (`//` 는 정수 나눗셈) |
| 타입 검사 | 엄격한 정적 타입 의미론. **실행 시점에** 해당 문장에서 검사(별도 컴파일 단계 없음) |

## 2. 타입
`bool byte int long float double decimal char string void object` + `list<T> map<K,V> set<T> array<T> tuple<...> fn(A,B) -> R`.
* 리터럴: `1`(정수) `1.5`(double) `1.5f`(float) `10.5m`(decimal) `'A'`(char) `"s"`(string) `0xFF` `1_000`
* 정수는 `byte`(0~255) `int`(32비트) `long`(64비트) 범위를 값으로 검사한다.
* 암시적 변환 없음: `double d = 10;` 는 오류, `cast<double>(10)` 사용. 서로 다른 숫자 타입끼리의 산술·비교도 오류.
* `/` 는 `int / int` 도 `double`, `//` 는 정수 나눗셈, `%` 는 피제수 부호가 아닌 Python 규칙, `**` 는 우결합.
* `cast<T>(v)` 실패 시 `ValueError`. 대상이 nullable(`cast<int?>("x")`)이면 `null`.
* `var` 는 초기값으로 타입을 고정(동적 타입 아님). `null`·빈 컬렉션은 추론 불가.
* nullable `T?` 만 `null` 허용. `??` `?.`(체인 전체 단락) `??=` 지원. 조건식은 반드시 `bool`.
* `is`: `x is int`, `x is Shape`, `x is null`, `x is not T`. `in`: 리스트·집합·맵 키·문자열·범위 포함 검사.
* 범위 `a..b` 는 `[a, b)`. 순회·`in`·슬라이스(`xs[1..3]`)에 사용. 음수 인덱스는 허용하지 않음.

## 3. 연산자 우선순위 (낮음 → 높음)
대입 < `\|>` < `??` < `or \|\|` < `and &&` < `not !` < 비교(`== != < > <= >= is in`) < `..` < `+ -` < `* / // %` < 단항 `+ -` < `**` < 후위(`()` `.` `?.` `::` `[]`)

* 파이프: `x |> f` = `f(x)`, `x |> f(a)` = `f(x, a)`.
* 람다: `x => x*2`, `(a, b) => a+b`, `fn(int x) => x*2`, `fn(x) { return x }`. 클로저는 정의 시점의 스코프를 참조한다.
* 연산자 오버로딩: 클래스 안에서 `fn operator+(Vec o) -> Vec`, `fn operator-() -> Vec`(단항), `operator== < > <= >=` 등. `toString()` 은 출력·`str()` 에 사용.

## 4. 함수
```
fn add(int a, int b = 1) -> int { return a + b }
fn sq(int x) => x * x                       # 식 본문
fn pick<T: Shape>(T a, T b) -> T { ... }    # 제네릭, 제약
```
* 반환 타입을 생략하면 첫 반환 타입으로 고정, 이후 다른 타입을 반환하면 `TypeError`. 값 없이 끝나면 `void`.
* 제네릭 타입 인자는 `f<int>(1)` 로 명시하거나 인자로부터 추론한다. `fn` 선언은 같은 블록 안에서 호이스팅된다.
* 재귀 깊이 제한 2500.

## 5. 클래스
* 접근 제한자: `public protected private internal file`. **멤버 기본값 private**, 최상위 기본값 internal, 인터페이스 멤버는 public. `file` 은 같은 소스 파일에서만.
* 필드·`static`·`const`, 메서드, 프로퍼티, 생성자 `constructor`, 소멸자 `destructor`(객체 해제 시, 상속 체인 전체 호출).
* 필드 기본값: 수치 0, bool false, string "", nullable null. 그 외 타입은 초기화 전 읽으면 `NullError`.
* 프로퍼티: `property int X { get; set; }`, `{ get => expr; private set; }`, `get { ... } set { ... }`(암묵 변수 `value`), `= 초기값`.
* 상속: `class D extends B, C implements I, J`. **C3 MRO**. `super.m()` 은 MRO 의 다음 클래스, `super<P>.m()` 은 지정 부모.
* 생성자 체인: `constructor(...) : super<P>(args), super<Q>() { }`. 부모가 하나면 `super(args)`. 명시하지 않은 부모는 인자 없이 자동 호출되고, 다이아몬드에서도 각 클래스는 객체당 한 번만 초기화된다. 생성자를 선언하지 않은 클래스는 첫 부모의 생성자를 상속한다.
* 인터페이스: 메서드(본문이 있으면 기본 구현)와 프로퍼티 요구. 다중 구현, `interface A extends B, C`. 구현 누락은 클래스 정의 시점에 `TypeError`.
* 제네릭 클래스: `class Box<T>`, 생성 시 `new Box<int>(1)` 또는 생성자 인자로 추론.
* 오버로딩(이름 같은 메서드 여러 개)은 없다. 기본 매개변수를 사용한다.

## 6. 예외
`throw "msg"` 는 `throw new Error("msg")`. `throw` 대상은 `Error` 계열 또는 `string`.
`catch (Type e)` 를 여러 개 둘 수 있고, `catch (e)` 는 `Error` 전체. `finally` 의 `return` 은 결과를 덮어쓴다.
내장 계층(`Lib/_prelude.ast`): `Error` ← `RuntimeError TypeError ValueError NullError IndexError KeyError ZeroDivisionError NameError AccessError ImportError IOError`.
처리되지 않은 예외는 stderr 에 줄 번호와 함께 출력되고 종료 코드 1.

## 7. 모듈
```
namespace Aster.Math { public fn add(int a, int b) -> int { return a + b } }
import Aster.Math;              # 프로그램 내부 namespace 를 현재 스코프로 가져옴
import math;                    # 모듈 바인딩:  math.sqrt(2.0)
import collections as c;        # 별칭
from collections import Stack, Queue as Q;
import "other.ast";             # 경로로 파일 실행
```
탐색 순서: 로드된 모듈 → 네이티브(`Modules/`) → `sys.path`(스크립트 폴더, `Lib/`, 현재 폴더)의 `이름.ast` 또는 `이름/__init__.ast`. `private`/`file` 멤버는 가져올 수 없다.

## 8. 내장
함수: `print input str len typeof abs min max sqrt floor ceil round exit assert`.
메서드(요약): string `upper lower trim split contains startsWith endsWith replace indexOf substring join chars`;
list `add insert remove removeAt pop contains indexOf clear sort reverse join copy map filter reduce forEach any all`;
set `add has remove clear toList`; map `has containsKey get keys values items remove clear`; 공통 `length`, `toString`.

## 9. 표준 라이브러리
네이티브(`Modules/`): `math sys os time random io json`. Aster 로 작성(`Lib/`): `collections`(Stack, Queue, Counter) `itertools` `functools` `statistics` `text` `unittest`.
