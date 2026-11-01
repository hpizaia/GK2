#!/usr/bin/env python3
"""Tests for scripts/build.py and scripts/validate.py.  Run:  python3 -I scripts/test_build.py

Runs every scripts/tests/test_*.py, one file per subject (shared helpers in scripts/tests/helpers.py). One file
alone:  python3 -I scripts/tests/test_page.py

Uses scripts/fixtures/* only (outputs go to temp dirs). Some tests read the real data/ and src/ (read-only); one
builds the real data/items.en.json + data/recipes.en.json when they exist (outputs to a temp dir).
"""
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__

TESTS = Path(__file__).resolve().parent / "tests"


def load_tests(loader, standard_tests, pattern):
    """unittest.main() asks this module for its tests: every test_*.py in scripts/tests/."""
    return loader.discover(str(TESTS), pattern="test_*.py", top_level_dir=str(TESTS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
