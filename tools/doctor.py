from __future__ import annotations

import subprocess
import sys


def _run(cmd: list[str]) -> int:
    print(f"DOCTOR: running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    # Non-destructive health check.
    # 1) Full post-phase verification (includes artifacts + SLIM content checks)
    rc = _run([sys.executable, "-m", "tools.verify_truth", "--phase", "post"])
    if rc != 0:
        return rc

    # 2) Smoke run
    rc = _run([sys.executable, "-m", "app.main"])
    if rc != 0:
        return rc

    print("DOCTOR OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
