"""Make local packages importable."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGES = REPO_ROOT / "packages"


def ensure_packages_on_path() -> None:
    """Add the packages directory and individual package roots to sys.path.

    Idempotent. Each package contains a plain `__init__.py` so importing as a
    top-level module works once the package root is on sys.path.
    """
    for pkg in ("aviation-units", "aviation-geometry", "shared-types"):
        path = str(PACKAGES / pkg)
        if path not in sys.path:
            sys.path.insert(0, path)


ensure_packages_on_path()
