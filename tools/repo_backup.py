from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from tools.project_meta import read_project_name
from tools.repo_walk import list_repo_files
from tools.truth_config import Config

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_JSON = REPO_ROOT / "tools" / "truth_config.json"

_MANIFEST_NAME = "BACKUP_MANIFEST.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_repo_files_for_backup(cfg: Config) -> List[Path]:
    # Single authoritative repo walk lives in tools.repo_walk
    return list_repo_files(cfg, slim=False).files


def build_repo_backup_zip(project: str, cfg: object, dest_dir: Path) -> Path:
    """Build a faithful, replayable snapshot of the repo into an external directory.

    Backup zips are ALWAYS nested under <project>/ to support safe extraction anywhere.
    A BACKUP_MANIFEST.json is written inside the zip with sha256 checksums.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_zip = dest_dir / f"{project}_REPO_BACKUP_{stamp}.zip"
    tmp_zip = out_zip.with_suffix(out_zip.suffix + ".tmp")

    cfg_obj = Config.load(CONFIG_JSON)
    files = _iter_repo_files_for_backup(cfg_obj)

    manifest: Dict[str, object] = {
        "project": project,
        "created_at_local": stamp,
        "root": project,
        "file_count": len(files),
        "files": {},
    }

    with ZipFile(tmp_zip, "w", compression=ZIP_DEFLATED) as z:
        # Write repo files
        for p in files:
            rel = p.relative_to(REPO_ROOT).as_posix()
            arc = f"{project}/{rel}"
            z.write(p, arcname=arc)
            manifest["files"][rel] = {
                "sha256": _sha256_file(p),
                "size": p.stat().st_size,
            }

        # Write manifest last
        z.writestr(f"{project}/{_MANIFEST_NAME}", json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    tmp_zip.replace(out_zip)
    print(f"OK: wrote repo backup: {out_zip}")
    return out_zip


def validate_repo_backup_zip(zip_path: Path) -> None:
    """Validate a repo backup zip created by build_repo_backup_zip.

    Raises RuntimeError on any failure.
    """
    from tools.validate_backup_zip import validate_backup_zip

    validate_backup_zip(str(zip_path))


def main() -> int:
    project = read_project_name()
    dest = Path.home() / "Documents" / "Programming" / f"{project}_backups" / f"before_confirm_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    build_repo_backup_zip(project, Config.load(CONFIG_JSON), dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
