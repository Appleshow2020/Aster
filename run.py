#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Programs/python.c 에 해당하는 최상위 실행기. 사용법은 `python run.py -h`."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Python.pythonrun import main

if __name__ == '__main__':
    main()
