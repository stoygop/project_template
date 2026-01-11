# tools/normalize_truth_md.py
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRUTH_MD = REPO_ROOT / "TRUTH.md"

def main() -> None:
    if not TRUTH_MD.exists():
        raise SystemExit(f"missing {TRUTH_MD}")

    raw = TRUTH_MD.read_bytes()

    # Normalize CRLF/CR to LF
    txt = raw.decode("utf-8", errors="strict")
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")

    # Ensure file ends with newline
    if not txt.endswith("\n"):
        txt += "\n"

    TRUTH_MD.write_text(txt, encoding="utf-8", newline="\n")

if __name__ == "__main__":
    main()
