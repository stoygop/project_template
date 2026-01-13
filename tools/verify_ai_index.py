from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]


def ok(msg: str, out: List[Dict[str, Any]] | None = None) -> None:
    print(f"VERIFY OK: {msg}")
    if out is not None:
        out.append({"ok": True, "message": msg})


def fail(msg: str) -> None:
    raise SystemExit(f"VERIFY FAIL: {msg}")


def _load_json(path: Path) -> Any:
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
        if txt.startswith("\ufeff"):
            txt = txt.lstrip("\ufeff")
        return json.loads(txt)
    except Exception as e:
        fail(f"invalid json: {path.name}: {e!r}")


def verify_ai_index(strict: bool = True, json_out: List[Dict[str, Any]] | None = None) -> None:
    ai_dir = REPO_ROOT / "_ai_index"
    if not ai_dir.exists():
        if strict:
            fail("_ai_index folder missing")
        ok("_ai_index missing (non-strict)", json_out)
        return

    required = [
        "_file_map.json",
        "python_index.json",
        "entrypoints.json",
        "_ai_index_INDEX.txt",
    ]
    for r in required:
        if not (ai_dir / r).exists():
            fail(f"missing {r}")
    ok("_ai_index required files present", json_out)

    # Contract sanity: ensure _file_map.json is a dict
    fm = _load_json(ai_dir / "_file_map.json")
    if not isinstance(fm, dict):
        fail("_file_map.json must be a JSON object (dict)")

    # python_index.json should be list or dict (depends on generator version)
    pi = _load_json(ai_dir / "python_index.json")
    if not isinstance(pi, (list, dict)):
        fail("python_index.json must be list or dict")

    ep = _load_json(ai_dir / "entrypoints.json")
    if not isinstance(ep, (list, dict)):
        fail("entrypoints.json must be list or dict")

    ok("_ai_index integrity verified", json_out)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Emit stable JSON output to stdout")
    ap.add_argument("--non-strict", action="store_true", help="Do not fail if _ai_index is missing")
    ns = ap.parse_args(argv) if argv is not None else ap.parse_args()

    events: List[Dict[str, Any]] = []
    try:
        verify_ai_index(strict=not ns.non_strict, json_out=events if ns.json else None)
    except SystemExit as e:
        if ns.json:
            print(json.dumps({"ok": False, "events": events, "error": str(e)}, indent=2, sort_keys=True))
        raise
    if ns.json:
        print(json.dumps({"ok": True, "events": events}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
