from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List

from tools.truth_config import Config
from tools.repo_walk import list_repo_files
from tools.project_meta import read_project_name

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "project_repo_map.json"
CONFIG_JSON = REPO_ROOT / "tools" / "truth_config.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_repo_map() -> Dict[str, object]:
    cfg = Config.load(CONFIG_JSON)
    project = read_project_name()
    walk = list_repo_files(cfg, slim=False)

    files: List[Dict[str, object]] = []
    for p in walk.files:
        rel = p.relative_to(REPO_ROOT).as_posix()
        files.append(
            {
                "path": rel,
                "sha256": _sha256_file(p),
                "size": p.stat().st_size,
            }
        )

    return {
        "meta": {"project": project},
        "files": files,
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
