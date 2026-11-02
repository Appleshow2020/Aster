"""Python/state.py — 현재 인터프리터에 대한 전역 참조 (CPython 의 PyThreadState 에 해당)."""
class _State:
    interp = None


state = _State()
