from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class Config:
    """Centralized repository filter + artifact settings loaded from tools/truth_config.json.

    This is the single authority for:
    - repo walks (repo map, ai index, zip packaging)
    - common excludes
    - artifact roots
    """
    zip_root: str = "_truth"
    ai_index_root: str = "_ai_index"
    draft_root: str = "_truth_drafts"

    exclude_common_folders: List[str] = field(default_factory=lambda: [
        ".git",
        "__pycache__",
        "_logs",
        "_outputs",
        "_build",
        "_dist",
        ".venv",
        "venv",
        "env",
        "_truth",
        "_truth_backups",
        "_truth_drafts",
        "_ai_index",
    ])
    exclude_common_files: List[str] = field(default_factory=lambda: [
        ".env",
    ])

    slim_exclude_folders: List[str] = field(default_factory=list)
    slim_exclude_ext: List[str] = field(default_factory=list)
    slim_exclude_extra_folders: List[str] = field(default_factory=list)

    forbidden_marker_substrings: List[str] = field(default_factory=list)

    truth_phases_required: bool = True

    @staticmethod
    def load(path: Path) -> "Config":
        data = json.loads(path.read_text(encoding="utf-8"))

        def _get_list(k: str, default: List[str]) -> List[str]:
            v = data.get(k, default)
            if v is None:
                return list(default)
            if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
                raise RuntimeError(f"truth_config.json: '{k}' must be a list of strings")
            return v

        cfg = Config(
            zip_root=str(data.get("zip_root", "_truth")),
            ai_index_root=str(data.get("ai_index_root", "_ai_index")),
            draft_root=str(data.get("draft_root", "_truth_drafts")),
            exclude_common_folders=_get_list("exclude_common_folders", Config().exclude_common_folders),
            exclude_common_files=_get_list("exclude_common_files", Config().exclude_common_files),
            slim_exclude_folders=_get_list("slim_exclude_folders", []),
            slim_exclude_ext=_get_list("slim_exclude_ext", []),
            slim_exclude_extra_folders=_get_list("slim_exclude_extra_folders", []),
            forbidden_marker_substrings=_get_list("forbidden_marker_substrings", []),
            truth_phases_required=bool(data.get("truth_phases_required", True)),
        )

        # Ensure artifact roots are excluded from generic repo scans to prevent recursion.
        roots = {cfg.zip_root, cfg.ai_index_root, cfg.draft_root}
        merged = list(dict.fromkeys(cfg.exclude_common_folders + [r for r in roots if r]))
        object.__setattr__(cfg, "exclude_common_folders", merged)  # type: ignore[attr-defined]
        return cfg
