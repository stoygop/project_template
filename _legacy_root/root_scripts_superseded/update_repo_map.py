from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from tools.repo_excludes import is_excluded_path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "project_repo_map.json"

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv", "env", ".tox"}
EXCLUDE_TOP_LEVEL = {"_truth_backups"}  # kept for backward-compat, but central excludes also apply


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files() -> List[Path]:
    files: List[Path] = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(REPO_ROOT)
        parts = rel.parts
        if is_excluded_path(p, REPO_ROOT):
            continue
        if parts and parts[0] in EXCLUDE_TOP_LEVEL:
            continue
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        # skip obvious large/binary artifacts (but keep .json/.md/.py etc.)
        if p.suffix.lower() in {".zip", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".avi"}:
            continue
        files.append(p)
    files.sort(key=lambda x: str(x.relative_to(REPO_ROOT)).lower())
    return files


def build_repo_map() -> Dict:
    items = []
    for p in _iter_files():
        rel = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        items.append(
            {
                "path": rel,
                "size": p.stat().st_size,
                "sha256": _sha256_file(p),
            }
        )
    return {
        "meta": {
            "project": "project_template",
        },
        "files": items,
    }


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tools.update_repo_map")
    ap.add_argument("--out", default=str(OUT_PATH), help="output path (default: project_repo_map.json)")
    args = ap.parse_args(argv)

    out = Path(args.out)
    data = build_repo_map()
    write_atomic(out, json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"OK: wrote repo map: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
