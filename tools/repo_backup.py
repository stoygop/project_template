from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_JSON = REPO_ROOT / "tools" / "truth_config.json"

_MANIFEST_NAME = "BACKUP_MANIFEST.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_cfg() -> dict:
    return json.loads(CONFIG_JSON.read_text(encoding="utf-8"))


def _should_exclude(rel: Path, cfg: dict) -> bool:
    parts = rel.parts
    if not parts:
        return False

    # Always exclude git internals and python caches
    if ".git" in parts or "__pycache__" in parts:
        return True
    if rel.suffix.lower() == ".pyc":
        return True

    # Exclude configured common folders/files
    exclude_folders = set(cfg.get("exclude_common_folders", []))
    exclude_files = set(cfg.get("exclude_common_files", []))

    if parts[0] in exclude_folders:
        return True
    if rel.name in exclude_files:
        return True

    # Backups and draft roots should never enter a backup snapshot
    if parts[0] in {"_truth_backups", cfg.get("draft_root", "_truth_drafts")}:
        return True

    return False


def _iter_repo_files_for_backup(cfg: dict) -> List[Path]:
    files: List[Path] = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(REPO_ROOT)
        if _should_exclude(rel, cfg):
            continue
        files.append(p)
    files.sort(key=lambda x: x.as_posix().lower())
    return files


def build_repo_backup_zip(project: str, cfg: object, dest_dir: Path) -> Path:
    """
    Build a faithful, replayable snapshot of the repo into an external directory.

    The zip will be nested under <project>/ and will include a manifest at:
      <project>/BACKUP_MANIFEST.json

    Returns the created zip path.
    """
    # cfg is TruthConfig in caller; we reload JSON here to avoid import cycles.
    cfg_json = _load_cfg()

    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_zip = dest_dir / f"{project}_REPO_BACKUP_{stamp}.zip"
    tmp_zip = dest_dir / f"tmp_{project}_REPO_BACKUP_{stamp}.zip"
    if tmp_zip.exists():
        tmp_zip.unlink()
    if out_zip.exists():
        out_zip.unlink()

    files = _iter_repo_files_for_backup(cfg_json)

    manifest: Dict[str, object] = {
        "project": project,
        "created_at_local": stamp,
        "root": project,
        "file_count": len(files),
        "files": {}
    }

    with ZipFile(tmp_zip, "w", compression=ZIP_DEFLATED) as z:
        for p in files:
            rel = p.relative_to(REPO_ROOT).as_posix()
            arc = f"{project}/{rel}"
            z.write(p, arcname=arc)
            manifest["files"][rel] = {
                "sha256": _sha256_file(p),
                "bytes": p.stat().st_size,
            }

        z.writestr(f"{project}/{_MANIFEST_NAME}", json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    tmp_zip.replace(out_zip)
    print(f"OK: wrote repo backup: {out_zip}")
    return out_zip


def validate_repo_backup_zip(zip_path: Path) -> None:
    """
    Validate a repo backup zip created by build_repo_backup_zip.
    Raises RuntimeError on any failure.
    """
    if not zip_path.exists():
        raise RuntimeError(f"backup zip missing: {zip_path}")

    with ZipFile(zip_path, "r") as z:
        names = [n.replace("\\", "/") for n in z.namelist() if n.strip()]
        if not names:
            raise RuntimeError("backup zip is empty")

        # Must be nested under a single root folder
        roots = {n.split("/", 1)[0] for n in names if "/" in n}
        if len(roots) != 1:
            raise RuntimeError(f"backup zip must have exactly one root folder; found: {sorted(roots)}")
        root = next(iter(roots))

        manifest_path = f"{root}/{_MANIFEST_NAME}"
        if manifest_path not in names:
            raise RuntimeError(f"backup manifest missing: {manifest_path}")

        manifest = json.loads(z.read(manifest_path).decode("utf-8"))
        files = manifest.get("files", {})
        if not isinstance(files, dict) or not files:
            raise RuntimeError("backup manifest has no files")

        # Verify hashes
        for rel, info in files.items():
            arc = f"{root}/{rel}"
            if arc not in names:
                raise RuntimeError(f"backup missing file listed in manifest: {arc}")
            data = z.read(arc)
            h = hashlib.sha256(data).hexdigest()
            if h != info.get("sha256"):
                raise RuntimeError(f"hash mismatch for {arc}")

    print(f"OK: backup zip validated: {zip_path}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="tools.repo_backup")
    ap.add_argument("--validate", help="validate a backup zip path")
    args = ap.parse_args()
    if args.validate:
        validate_repo_backup_zip(Path(args.validate))
