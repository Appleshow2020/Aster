"""Modules/ — 네이티브(파이썬으로 구현한) 모듈 레지스트리 (CPython 의 Modules/config.c 에 해당).

`import <이름>` 이 Lib/<이름>.ast 보다 먼저 이 표를 조회한다.
"""
NATIVE = {
    'math': 'Modules.mathmodule',
    'sys': 'Modules.sysmodule',
    'os': 'Modules.posixmodule',
    'time': 'Modules.timemodule',
    'random': 'Modules.randommodule',
    'io': 'Modules.iomodule',
    'json': 'Modules.jsonmodule',
}
