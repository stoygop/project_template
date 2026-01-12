from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "tools" / "ai_index.py"

SNIPPET = """

# --- V9 TASK03: canonical enumerator shim (auto-inserted) ---
# Ensure ai_index uses the single authoritative repo walker (tools.repo_walk).
try:
    from tools.repo_walk import iter_repo_files as _canonical_iter_repo_files
except Exception:
    _canonical_iter_repo_files = None


def iter_repo_files(cfg, *args, **kwargs):
    """Iterate repo files via canonical enumerator.

    This wrapper keeps backward compatibility for existing ai_index internals
    that call iter_repo_files(cfg).
    """
    if _canonical_iter_repo_files is None:
        raise RuntimeError("tools.repo_walk.iter_repo_files is unavailable")
    return _canonical_iter_repo_files(cfg, slim=False, allow_top_level=set())
"""


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: missing {TARGET}", file=sys.stderr)
        return 2

    txt = TARGET.read_text(encoding="utf-8", errors="replace")

    # Already patched?
    if "canonical enumerator shim" in txt or "from tools.repo_walk import iter_repo_files" in txt:
        print("OK: ai_index already wired to tools.repo_walk")
        return 0

    # Append shim at end.
    out = txt.rstrip() + SNIPPET + "\n"
    TARGET.write_text(out, encoding="utf-8", newline="\n")
    print("OK: patched tools/ai_index.py to import/use tools.repo_walk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
