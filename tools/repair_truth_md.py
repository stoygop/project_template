# tools/repair_truth_md.py
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRUTH_MD = REPO_ROOT / "TRUTH.md"
VERSION_PY = REPO_ROOT / "app" / "version.py"

# Allow optional D type tag suffix: [CONFIRM|DREAM|DEBUG]
TRUTH_HEADER_RE = re.compile(
    r"^TRUTH\s*-\s*(.+)\s+\(TRUTH_V(\d+)\)\s*(?:\[(CONFIRM|DREAM|DEBUG)\])?\s*$"
)

def _normalize_newlines(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")

def repair_truth_md() -> int:
    if not TRUTH_MD.exists():
        raise SystemExit(f"missing {TRUTH_MD}")

    txt = _normalize_newlines(TRUTH_MD.read_text(encoding="utf-8", errors="replace"))
    lines = txt.split("\n")

    # find all truth header line indexes (0-based)
    starts = []
    versions = []
    for i, line in enumerate(lines):
        m = TRUTH_HEADER_RE.match(line.strip())
        if m:
            starts.append(i)
            versions.append(int(m.group(2)))

    if not starts:
        return 0

    # Check each entry for END; if the LAST entry is missing END, truncate from its start
    def entry_slice(si: int, sj: int | None) -> list[str]:
        return lines[si:(sj if sj is not None else len(lines))]

    truncated = 0
    for idx, si in enumerate(starts):
        sj = starts[idx + 1] if idx + 1 < len(starts) else None
        block = entry_slice(si, sj)
        has_end = any(l.strip() == "END" for l in block)
        if not has_end:
            # only safe to truncate if it's the last entry (otherwise file is corrupted midstream)
            if sj is not None:
                raise SystemExit(f"TRUTH.md corruption: TRUTH_V{versions[idx]} missing END but not last entry")
            lines = lines[:si]
            truncated = versions[idx]
            break

    out = "\n".join(lines).rstrip("\n") + "\n"
    TRUTH_MD.write_text(out, encoding="utf-8", newline="\n")

    # sync app/version.py to latest remaining truth
    remaining_versions = []
    for line in out.split("\n"):
        m = TRUTH_HEADER_RE.match(line.strip())
        if m:
            remaining_versions.append(int(m.group(2)))
    latest = max(remaining_versions) if remaining_versions else 0

    vtxt = _normalize_newlines(VERSION_PY.read_text(encoding="utf-8", errors="replace"))
    vtxt2 = re.sub(r"TRUTH_VERSION\s*=\s*\d+", f"TRUTH_VERSION = {latest}", vtxt)
    VERSION_PY.write_text(vtxt2, encoding="utf-8", newline="\n")

    return truncated

def main() -> None:
    truncated = repair_truth_md()
    if truncated:
        print(f"REPAIR: truncated incomplete TRUTH_V{truncated} entry (missing END)")
    else:
        print("REPAIR: no changes")

if __name__ == "__main__":
    main()
