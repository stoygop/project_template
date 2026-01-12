"""Centralized repository exclusion rules.

Why this exists
--------------
The repository contains both authoritative source files and generated state
(truth artifacts, indexing outputs, backups, drafts, caches). If repo-walking
tools recursively ingest generated outputs as inputs, the system becomes
non-deterministic and can fail via recursive contamination.

All tools that walk the repo MUST consult this module.
"""

from __future__ import annotations

from pathlib import Path


# Generated/derived folders that must never be treated as authoritative input.
EXCLUDED_TOPLEVEL_DIRS = {
    "_truth",
    "_ai_index",
    "_truth_backups",
    "_truth_drafts",
}

# Exclude common cache dirs anywhere.
EXCLUDED_DIR_NAMES = {
    "__pycache__",
}

# Exclude compiled python files.
EXCLUDED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def is_excluded_path(path: Path, repo_root: Path) -> bool:
    """Return True if *path* should be excluded from repo walks.

    The check is conservative: any generated state is excluded.
    """
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except Exception:
        # If we can't relate it to repo_root, don't include it.
        return True

    parts = rel.parts
    if not parts:
        return False

    if parts[0] in EXCLUDED_TOPLEVEL_DIRS:
        return True

    if any(p in EXCLUDED_DIR_NAMES for p in parts):
        return True

    if path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return True

    return False
