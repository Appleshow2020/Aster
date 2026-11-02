#!/usr/bin/env python3
"""Tools/runtests.py — Lib/test/test_*.ast 를 각각 별도 프로세스로 실행하는 회귀 테스트 러너 (CPython 의 regrtest 에 해당)."""
import glob, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else 'test_*.ast'
    files = sorted(glob.glob(os.path.join(ROOT, 'Lib', 'test', pattern)))
    bad = []
    t0 = time.time()
    for f in files:
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'run.py'), f], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        name = os.path.basename(f)
        if r.returncode == 0:
            print('PASS', name)
        else:
            bad.append(name); print('FAIL', name); print(r.stdout); print(r.stderr)
    print('\n%d 파일 중 %d 실패 (%.1fs)' % (len(files), len(bad), time.time() - t0))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
