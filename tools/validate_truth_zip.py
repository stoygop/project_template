from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List
from zipfile import ZipFile


@dataclass
class ValidationResult:
    ok: bool
    zip_path: str
    project: str | None = None
    prefix: str | None = None
    entry_count: int | None = None
    errors: List[str] | None = None


def _infer_project_from_filename(zip_path: Path) -> str:
    # Expected: <project>_TRUTH_V#.zip (or similar)
    name = zip_path.name
    if "_TRUTH_" not in name:
        raise RuntimeError(f"cannot infer project from truth zip filename: {name}")
    return name.split("_TRUTH_", 1)[0]


def validate_truth_zip(zip_path: Path) -> None:
    """
    Enforce truth zip structure contract:

      - All entries are nested under exactly one top-level folder: <project>/
      - <project> is inferred from zip filename prefix "<project>_TRUTH_..."
      - No duplicate archive paths (after normalizing path separators)
      - Sanity: contains at least one file under <project>/app/ or <project>/tools/

    Raises RuntimeError on failure.
    Prints nothing on success (use CLI for user-facing output).
    """
    if not zip_path.exists():
        raise RuntimeError(f"truth zip missing: {zip_path}")

    project = _infer_project_from_filename(zip_path)

    with ZipFile(zip_path, "r") as z:
        # normalize to forward slashes so behavior is consistent across platforms
        names = [n.replace("\\", "/") for n in z.namelist() if n.strip()]
        if not names:
            raise RuntimeError("truth zip is empty")

        # duplicates
        if len(set(names)) != len(names):
            raise RuntimeError("truth zip contains duplicate archive paths")

        prefix = project + "/"
        bad = [n for n in names if not n.startswith(prefix)]
        if bad:
            raise RuntimeError(f"truth zip entries not nested under '{prefix}': {bad[:10]}")

        has_core = any(
            n.startswith(prefix + "app/") or n.startswith(prefix + "tools/")
            for n in names
        )
        if not has_core:
            raise RuntimeError("truth zip missing expected core folders (app/ or tools/)")


def validate_truth_zip_result(zip_path: Path) -> ValidationResult:
    """Non-throwing wrapper suitable for JSON output."""
    try:
        project = _infer_project_from_filename(zip_path) if zip_path.exists() else None
        prefix = (project + "/") if project else None

        with ZipFile(zip_path, "r") as z:
            names = [n.replace("\\", "/") for n in z.namelist() if n.strip()]
        # Do full validation (will raise if bad)
        validate_truth_zip(zip_path)
        return ValidationResult(
            ok=True,
            zip_path=str(zip_path),
            project=project,
            prefix=prefix,
            entry_count=len(names),
            errors=[],
        )
    except Exception as e:
        return ValidationResult(
            ok=False,
            zip_path=str(zip_path),
            errors=[str(e)],
        )


def _print_ok_human(res: ValidationResult) -> None:
    suffix = ""
    if res.entry_count is not None:
        suffix = f" ({res.entry_count} entries)"
    print(f"OK: truth zip structure validated: {res.zip_path}{suffix}")


def _print_err_human(res: ValidationResult) -> None:
    err = (res.errors or ["validation failed"])[0]
    print(f"ERROR: {err}", file=sys.stderr)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate truth zip structure contract.")
    ap.add_argument("zip", help="Path to <project>_TRUTH_*.zip")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = ap.parse_args(argv)

    zip_path = Path(args.zip)

    res = validate_truth_zip_result(zip_path)

    if args.json:
        print(json.dumps(asdict(res), indent=2, sort_keys=True))
    else:
        if res.ok:
            _print_ok_human(res)
        else:
            _print_err_human(res)

    return 0 if res.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
