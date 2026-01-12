from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_PY = REPO_ROOT / "app" / "version.py"


def read_project_name() -> str:
    txt = VERSION_PY.read_text(encoding="utf-8")
    m = re.search(r'PROJECT_NAME\s*=\s*"(.*?)"', txt)
    if not m:
        raise RuntimeError(f"PROJECT_NAME not found in {VERSION_PY}")
    return m.group(1)


def read_truth_version() -> int:
    txt = VERSION_PY.read_text(encoding="utf-8")
    m = re.search(r"TRUTH_VERSION\s*=\s*(\d+)", txt)
    if not m:
        raise RuntimeError(f"TRUTH_VERSION not found in {VERSION_PY}")
    return int(m.group(1))


def read_project_and_truth_version() -> Tuple[str, int]:
    return read_project_name(), read_truth_version()
