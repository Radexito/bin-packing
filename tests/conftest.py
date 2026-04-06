"""Shared pytest configuration.

Ensures src/ takes precedence over the repo root in sys.path so that
src/visualizer.py is imported instead of the legacy root-level visualizer.py.
"""
import sys
from pathlib import Path


def pytest_configure(config):
    """Move src/ to the front of sys.path before any test modules are imported."""
    src = str(Path(__file__).parent.parent / "src")
    if src in sys.path:
        sys.path.remove(src)
    sys.path.insert(0, src)
