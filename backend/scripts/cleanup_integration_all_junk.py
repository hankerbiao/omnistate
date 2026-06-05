#!/usr/bin/env python3
"""Backward-compatible wrapper — use cleanup_test_data.py instead.

Usage:
  cd backend
  python scripts/cleanup_integration_all_junk.py
  python scripts/cleanup_integration_all_junk.py --dry-run
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "cleanup_test_data.py"
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
