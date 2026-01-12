from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Tuple

from tools.truth_config import Config

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class WalkResult:
    files: List[Path]
    excluded: int = 0


def _has_any_part(rel: Path, names: Set[str]) -> bool:
    return any(part in names for part in rel.parts)


def should_exclude(rel: Path, cfg: Config, *, slim: bool = False, allow_top_level: Set[str] | None = None) -> bool:
    # Never include anything inside .git
    if ".git" in rel.parts:
        return True

    allow_top_level = allow_top_level or set()

    # Common excludes (optionally allow certain top-level roots, e.g. _ai_index for packaging)
    exclude_folders = set(cfg.exclude_common_folders)
    if rel.parts and rel.parts[0] in allow_top_level:
        exclude_folders = {x for x in exclude_folders if x != rel.parts[0]}

    if _has_any_part(rel, exclude_folders):
        return True

    # Exclude common files by basename
    if rel.name in set(cfg.exclude_common_files):
        return True

    # Slim-only excludes
    if slim:
        if _has_any_part(rel, set(cfg.slim_exclude_folders) | set(cfg.slim_exclude_extra_folders)):
            return True
        if rel.suffix.lower() in set(x.lower() for x in cfg.slim_exclude_ext):
            return True

    return False


def iter_repo_files(cfg: Config, *, slim: bool = False, allow_top_level: Set[str] | None = None) -> Iterable[Path]:
    """Yield absolute file paths under REPO_ROOT included by cfg rules.

    NOTE: This iterator intentionally excludes artifact roots (zip_root, ai_index_root, draft_root)
    because Config.load() merges these roots into exclude_common_folders.
    """
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO_ROOT)
        if should_exclude(rel, cfg, slim=slim, allow_top_level=allow_top_level):
            continue
        yield p


def list_repo_files(cfg: Config, *, slim: bool = False, allow_top_level: Set[str] | None = None) -> WalkResult:
    files: List[Path] = []
    excluded = 0
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO_ROOT)
        if should_exclude(rel, cfg, slim=slim, allow_top_level=allow_top_level):
            excluded += 1
            continue
        files.append(p)
    files.sort(key=lambda x: x.as_posix().lower())
    return WalkResult(files=files, excluded=excluded)
