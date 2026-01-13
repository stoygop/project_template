from __future__ import annotations

import argparse
import subprocess
import sys


def _run(cmd: list[str]) -> int:
    print(f"DOCTOR: running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Non-destructive repo health check.")
    ap.add_argument("--json", action="store_true", help="Emit stable JSON output to stdout")

    ap.add_argument(
        "--phase",
        choices=["pre", "post"],
        default="post",
        help="Truth verification phase to run (default: post). Use pre for CI where artifacts may not exist.",
    )
    args = ap.parse_args(argv)

    # 1) Phase-aware verification
    rc = _run([sys.executable, "-m", "tools.verify_truth", "--phase", args.phase])
    if rc != 0:
        return rc

    # 2) Smoke run (should be cheap and deterministic)
    rc = _run([sys.executable, "-m", "app.main"])
    _event(rc == 0, f"DOCTOR: app.main rc={rc}")
    if rc != 0:
        return rc

    if ns.json:
        import json as _json
        print(_json.dumps({"ok": True, "phase": ns.phase, "events": events}, indent=2, sort_keys=True))
    print("DOCTOR OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
