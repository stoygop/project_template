from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile


def validate_truth_zip(zip_path: Path) -> None:
    """
    Enforce zip structure contract:
      - All entries are nested under exactly one top-level folder
      - The folder name must match the project name inferred from the zip filename prefix "<project>_TRUTH_..."
      - No duplicate archive paths
    """
    if not zip_path.exists():
        raise RuntimeError(f"truth zip missing: {zip_path}")

    name = zip_path.name
    if "_TRUTH_V" not in name:
        raise RuntimeError(f"truth zip name not recognized: {name}")
    project = name.split("_TRUTH_V", 1)[0]

    with ZipFile(zip_path, "r") as z:
        names = [n.replace("\\", "/") for n in z.namelist() if n.strip()]
        if not names:
            raise RuntimeError("truth zip is empty")

        # duplicates
        if len(set(names)) != len(names):
            raise RuntimeError("truth zip contains duplicate archive paths")

        # must all start with "project/"
        prefix = project + "/"
        bad = [n for n in names if not n.startswith(prefix)]
        if bad:
            raise RuntimeError(f"truth zip entries not nested under '{prefix}': {bad[:10]}")

        # ensure there is at least one file under app/ or tools/ (sanity)
        has_core = any(n.startswith(prefix + "app/") or n.startswith(prefix + "tools/") for n in names)
        if not has_core:
            raise RuntimeError("truth zip missing expected core folders (app/ or tools/)")

    print(f"OK: truth zip structure validated: {zip_path}")
