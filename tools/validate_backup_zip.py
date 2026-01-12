from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any
from zipfile import ZipFile
import hashlib


_MANIFEST_NAME = "BACKUP_MANIFEST.json"


@dataclass
class ValidationResult:
    ok: bool
    zip_path: str
    project: str | None = None
    root: str | None = None
    entry_count: int | None = None
    file_count: int | None = None
    errors: List[str] | None = None


def _normalize_names(z: ZipFile) -> List[str]:
    return [n.replace("\\", "/") for n in z.namelist() if n and n.strip()]


def validate_backup_zip(zip_path: Path) -> None:
    """
    Validate a repo backup zip contract.

    Contract:
      - Zip exists and is non-empty
      - Exactly one top-level folder <root>/
      - Contains <root>/BACKUP_MANIFEST.json
      - Manifest contains a non-empty files mapping
      - Every file listed in manifest exists in zip and SHA256 matches manifest

    Raises RuntimeError on failure.
    Prints nothing on success (use CLI for user-facing output).
    """
    if not zip_path.exists():
        raise RuntimeError(f"backup zip missing: {zip_path}")

    with ZipFile(zip_path, "r") as z:
        names = _normalize_names(z)
        if not names:
            raise RuntimeError("backup zip is empty")

        roots = {n.split("/", 1)[0] for n in names if "/" in n}
        if len(roots) != 1:
            raise RuntimeError(f"backup zip must have exactly one root folder; found: {sorted(roots)}")
        root = next(iter(roots))

        manifest_path = f"{root}/{_MANIFEST_NAME}"
        if manifest_path not in names:
            raise RuntimeError(f"backup manifest missing: {manifest_path}")

        try:
            manifest = json.loads(z.read(manifest_path).decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"backup manifest is not valid JSON: {e}")

        files = manifest.get("files", None)
        if not isinstance(files, dict) or not files:
            raise RuntimeError("backup manifest has no files mapping")

        # Verify hashes for each listed file
        for rel, info in files.items():
            arc = f"{root}/{rel}"
            if arc not in names:
                raise RuntimeError(f"backup missing file listed in manifest: {arc}")
            data = z.read(arc)
            h = hashlib.sha256(data).hexdigest()
            expected = (info or {}).get("sha256")
            if not expected or h != expected:
                raise RuntimeError(f"hash mismatch for {arc}")


def validate_backup_zip_result(zip_path: Path) -> ValidationResult:
    """Non-throwing wrapper suitable for JSON output."""
    try:
        project = None
        root = None
        entry_count = None
        file_count = None

        with ZipFile(zip_path, "r") as z:
            names = _normalize_names(z)
            entry_count = len(names)
            roots = {n.split("/", 1)[0] for n in names if "/" in n}
            if len(roots) == 1:
                root = next(iter(roots))
            if root:
                manifest_path = f"{root}/{_MANIFEST_NAME}"
                if manifest_path in names:
                    try:
                        manifest = json.loads(z.read(manifest_path).decode("utf-8"))
                        project = manifest.get("project") or root
                        files = manifest.get("files")
                        if isinstance(files, dict):
                            file_count = len(files)
                    except Exception:
                        pass

        validate_backup_zip(zip_path)
        return ValidationResult(
            ok=True,
            zip_path=str(zip_path),
            project=project,
            root=root,
            entry_count=entry_count,
            file_count=file_count,
            errors=[],
        )
    except Exception as e:
        return ValidationResult(
            ok=False,
            zip_path=str(zip_path),
            errors=[str(e)],
        )


def _print_ok_human(res: ValidationResult) -> None:
    extras = []
    if res.entry_count is not None:
        extras.append(f"{res.entry_count} entries")
    if res.file_count is not None:
        extras.append(f"{res.file_count} files")
    suffix = "" if not extras else f" ({', '.join(extras)})"
    print(f"OK: backup zip validated: {res.zip_path}{suffix}")


def _print_err_human(res: ValidationResult) -> None:
    err = (res.errors or ["validation failed"])[0]
    print(f"ERROR: {err}", file=sys.stderr)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate repo backup zip (nested root + manifest + sha256).")
    ap.add_argument("zip", help="Path to <project>_REPO_BACKUP_*.zip")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = ap.parse_args(argv)

    zip_path = Path(args.zip)

    res = validate_backup_zip_result(zip_path)

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
