"""
validate_backup_zip.py

Validates "repo backup" artifact zips.

Contract (high level):
- Zip must contain exactly one top-level folder named <project>/
- Must include BACKUP_MANIFEST.json at root/<project>/BACKUP_MANIFEST.json (when present)
- No duplicate archive paths
- Optional sha256 verification against manifest entries

CLI:
  python -m tools.validate_backup_zip <zip_path> [--json]

This module is intentionally tolerant about zip_path type (str or PathLike).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zipfile import ZipFile


@dataclass
class BackupZipReport:
    ok: bool
    zip_path: str
    root: Optional[str] = None
    project: Optional[str] = None
    entry_count: Optional[int] = None
    file_count: Optional[int] = None
    errors: Optional[List[str]] = None


def _read_manifest(zf: ZipFile, root: str) -> Optional[Dict[str, Any]]:
    # Manifest is optional for legacy backups; required for new ones.
    # We validate if present.
    cand = f"{root}/BACKUP_MANIFEST.json"
    try:
        with zf.open(cand) as f:
            return json.loads(f.read().decode("utf-8"))
    except KeyError:
        return None


def _sha256_bytes(data: bytes) -> str:
    h = sha256()
    h.update(data)
    return h.hexdigest()


def validate_backup_zip(zip_path: str | os.PathLike, json_mode: bool = False) -> BackupZipReport:
    # IMPORTANT: callers may pass str; normalize immediately.
    zip_path = Path(zip_path)

    report = BackupZipReport(ok=False, zip_path=str(zip_path), errors=[])

    try:
        if not zip_path.exists():
            report.errors.append(f"[Errno 2] No such file or directory: '{zip_path}'")
            return report

        with ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            report.entry_count = len(names)

            # duplicate archive paths (exact duplicates in central directory)
            if len(names) != len(set(names)):
                report.errors.append("backup zip contains duplicate archive paths")
                return report

            # Determine single top-level folder root
            roots = set()
            for n in names:
                if not n or n.endswith("/"):
                    continue
                parts = n.split("/")
                if parts:
                    roots.add(parts[0])

            if len(roots) != 1:
                report.errors.append("backup zip must contain exactly one top-level folder")
                return report

            root = next(iter(roots))
            report.root = root
            report.project = root  # project name == root folder name by contract

            # Count files (exclude dirs)
            report.file_count = sum(1 for n in names if n and not n.endswith("/"))

            manifest = _read_manifest(zf, root)
            if manifest is not None:
                # Validate manifest shape
                files = manifest.get("files")
                if not isinstance(files, list):
                    report.errors.append("BACKUP_MANIFEST.json invalid: missing 'files' list")
                    return report

                # verify each file hash if provided
                for entry in files:
                    if not isinstance(entry, dict):
                        report.errors.append("BACKUP_MANIFEST.json invalid: file entry not an object")
                        return report
                    rel = entry.get("path")
                    exp = entry.get("sha256")
                    if not isinstance(rel, str):
                        report.errors.append("BACKUP_MANIFEST.json invalid: entry.path not a string")
                        return report
                    if exp is None:
                        continue
                    if not isinstance(exp, str):
                        report.errors.append("BACKUP_MANIFEST.json invalid: entry.sha256 not a string")
                        return report
                    arc = f"{root}/{rel}".replace("\\", "/")
                    try:
                        with zf.open(arc) as f:
                            got = _sha256_bytes(f.read())
                    except KeyError:
                        report.errors.append(f"manifest file missing in zip: {arc}")
                        return report
                    if got.lower() != exp.lower():
                        report.errors.append(f"sha256 mismatch: {arc}")
                        return report

        report.ok = True
        return report

    except Exception as e:
        report.errors.append(str(e))
        return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip_path")
    ap.add_argument("--json", action="store_true", dest="json_mode")
    args = ap.parse_args(argv)

    rep = validate_backup_zip(args.zip_path, json_mode=args.json_mode)

    if args.json_mode:
        print(json.dumps(asdict(rep), indent=2, sort_keys=True))
    else:
        if rep.ok:
            print(f"OK: backup zip validated: {rep.zip_path} ({rep.entry_count} entries, {rep.file_count} files)")
        else:
            # Keep same style as other tools
            if rep.errors:
                print("ERROR: " + rep.errors[0], file=sys.stderr)
            else:
                print("ERROR: backup zip validation failed", file=sys.stderr)

    return 0 if rep.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
