from __future__ import annotations

import sys
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(ai_dir: Path) -> None:
    manifest = ai_dir / "_ai_index_INDEX.txt"
    if not manifest.exists():
        raise SystemExit(f"VERIFY FAIL: missing {manifest}")

    lines = manifest.read_text(encoding="utf-8").splitlines()
    # skip header lines until blank line
    try:
        blank = lines.index("")
        body = lines[blank + 1 :]
    except ValueError:
        body = [ln for ln in lines if "\t" in ln]

    if not body:
        raise SystemExit("VERIFY FAIL: manifest has no entries")

    for ln in body:
        if "\t" not in ln:
            continue
        name, size_s, sha = ln.split("\t")
        p = ai_dir / name
        if not p.exists():
            raise SystemExit(f"VERIFY FAIL: missing indexed file {name}")
        size = p.stat().st_size
        if str(size) != size_s:
            raise SystemExit(f"VERIFY FAIL: size mismatch for {name} (manifest {size_s} != actual {size})")
        sha2 = sha256_file(p)
        if sha2 != sha:
            raise SystemExit(f"VERIFY FAIL: sha256 mismatch for {name}")

    print("VERIFY OK: _ai_index integrity verified")


def main() -> int:
    ai_dir = REPO_ROOT / "_ai_index"
    if not ai_dir.exists():
        raise SystemExit("VERIFY FAIL: _ai_index folder missing (run python -m tools.ai_index build)")

    # Contract: these must exist
    required = [
        "_ai_index_README.txt",
        "_file_map.json",
        "python_index.json",
        "entrypoints.json",
        "_ai_index_INDEX.txt",
    ]
    for r in required:
        if not (ai_dir / r).exists():
            raise SystemExit(f"VERIFY FAIL: missing {r}")

    verify_manifest(ai_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
