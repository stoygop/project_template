from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from tools.truth_config import Config
from tools.repo_walk import list_repo_files


def make_zip(zip_path: Path | str, cfg: Config, *, slim: bool, project: str) -> Path:
    """Build a truth artifact zip (FULL/SLIM) with required nesting.

    Contract:
    - Exactly one top-level folder named '<project>/'.
    - All archive members are stored as '<project>/<repo-relative-path>' (posix).
    - Duplicate archive paths are forbidden (case-insensitive safety).
    - Deterministic ordering (sorted canonical enumerator).
    """
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = zip_path.with_name(f"tmp_{zip_path.stem}{zip_path.suffix}")
    if tmp_path.exists():
        tmp_path.unlink()
    if zip_path.exists():
        zip_path.unlink()

    project_prefix = project.strip().strip("/").strip("\\")
    if not project_prefix:
        raise RuntimeError("project name is empty")

    repo_root = Path.cwd().resolve()
    wr = list_repo_files(cfg, slim=slim)
    seen_lower: set[str] = set()

    with ZipFile(tmp_path, "w", compression=ZIP_DEFLATED) as z:
        for p in wr.files:
            # p is absolute path under repo root
            rel = p.relative_to(repo_root)
            rel_posix = rel.as_posix()
            arc = f"{project_prefix}/{rel_posix}"

            key = arc.lower()
            if key in seen_lower:
                raise RuntimeError(f"truth zip contains duplicate archive path: {arc}")
            seen_lower.add(key)

            z.write(p, arcname=arc)

    tmp_path.replace(zip_path)
    return zip_path
