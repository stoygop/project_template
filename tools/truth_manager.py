from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from tools.ai_index import build_ai_index
from tools.verify_ai_index import main as verify_ai_index_main

REPO_ROOT = Path(__file__).resolve().parents[1]
TRUTH_MD = REPO_ROOT / "TRUTH.md"
VERSION_PY = REPO_ROOT / "app" / "version.py"
CONFIG_JSON = REPO_ROOT / "tools" / "truth_config.json"

# ... unchanged imports / config helpers ...

def append_truth_md_verbatim(block: str) -> None:
    txt = TRUTH_MD.read_text(encoding="utf-8")
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    block = block.replace("\r\n", "\n").replace("\r", "\n")

    if not block.strip().endswith("END"):
        raise RuntimeError("TRUTH block must end with END")

    if not txt.endswith("\n"):
        txt += "\n"
    if not txt.endswith("\n\n"):
        txt += "\n"

    if not block.endswith("\n"):
        block += "\n"

    TRUTH_MD.write_text(txt + block + "\n", encoding="utf-8", newline="\n")

# PATCH: mint_truth now uses verbatim append
def mint_truth(statement_text: str) -> Tuple[int, Path, Path]:
    from tools import verify_truth

    print("PHASE 0/2: Pre-mint verification")
    verify_truth.main(["--phase", "pre"])

    block = statement_text.strip() + "\n"
    append_truth_md_verbatim(block)

    # bump version AFTER append
    txt = VERSION_PY.read_text(encoding="utf-8")
    m = re.search(r"TRUTH_VERSION\s*=\s*(\d+)", txt)
    if not m:
        raise RuntimeError("TRUTH_VERSION not found")
    new_ver = int(m.group(1)) + 1
    txt = re.sub(r"TRUTH_VERSION\s*=\s*\d+", f"TRUTH_VERSION = {new_ver}", txt)
    VERSION_PY.write_text(txt, encoding="utf-8", newline="\n")

    build_ai_index()
    verify_ai_index_main([])

    print("PHASE 2/2: Post-artifact verification")
    verify_truth.main(["--phase", "post"])

    return new_ver, None, None
