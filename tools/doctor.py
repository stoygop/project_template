from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any, List, Dict


def _run(cmd: list[str]) -> int:
    print(f"DOCTOR: running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Non-destructive repo health check.")
    ap.add_argument(
        "--phase",
        choices=["pre", "post"],
        default="post",
        help="Verification phase. 'pre' is repo-only checks; 'post' additionally requires local artifacts.",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit stable JSON describing the checks performed and their outcomes.",
    )
    args = ap.parse_args(argv)

    events: List[Dict[str, Any]] = []

    def _event(ok: bool, message: str) -> None:
        events.append({"message": message, "ok": bool(ok)})
        if ok:
            print(f"DOCTOR OK: {message}")
        else:
            print(f"DOCTOR FAIL: {message}")

    # 1) Verify truth for requested phase
    rc = _run([sys.executable, "-m", "tools.verify_truth", "--phase", args.phase])
    _event(rc == 0, f"verify_truth rc={rc} phase={args.phase}")
    if rc != 0:
        if args.json:
            print(json.dumps({"ok": False, "phase": args.phase, "events": events}, indent=2))
        return rc

    # 2) Smoke run (should be cheap and deterministic)
    rc = _run([sys.executable, "-m", "app.main"])
    _event(rc == 0, f"app.main rc={rc}")
    if rc != 0:
        if args.json:
            print(json.dumps({"ok": False, "phase": args.phase, "events": events}, indent=2))
        return rc

    _event(True, "doctor complete")
    if args.json:
        print(json.dumps({"ok": True, "phase": args.phase, "events": events}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
