# app/main.py
from __future__ import annotations

from app.version import PROJECT_NAME, TRUTH_VERSION


def main() -> int:
    print(f"{PROJECT_NAME} — TRUTH_V{TRUTH_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
