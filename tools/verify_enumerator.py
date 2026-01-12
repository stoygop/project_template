from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    "tools/update_repo_map.py",
    "tools/ai_index.py",
    "tools/repo_backup.py",
    "tools/truth_manager.py",
]

ALLOWED_OS_WALK_FILES = {
    "tools/repo_walk.py",
    "tools/verify_truth.py",  # verify_truth may do a lightweight fallback in rare cases
}

def _read_text(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")

def _parse(rel: str) -> ast.AST:
    return ast.parse(_read_text(rel), filename=rel)

def _imports_repo_walk(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "tools.repo_walk" or a.name.endswith(".repo_walk"):
                    return True
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "tools.repo_walk" or mod.endswith(".repo_walk"):
                return True
    return False

def _find_os_walk_calls(tree: ast.AST) -> List[Tuple[int, str]]:
    hits: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                if fn.value.id == "os" and fn.attr == "walk":
                    hits.append((getattr(node, "lineno", -1), "os.walk"))
    return hits

def verify_canonical_enumerator_wiring(strict: bool = True) -> None:
    """
    Ensures all key enumerators are wired to tools.repo_walk (single source of truth)
    and do not reintroduce ad-hoc os.walk enumeration.
    """
    missing: List[str] = []
    oswalk: List[str] = []

    for rel in TARGETS:
        tree = _parse(rel)
        if not _imports_repo_walk(tree):
            missing.append(rel)
        if rel not in ALLOWED_OS_WALK_FILES:
            hits = _find_os_walk_calls(tree)
            if hits:
                oswalk.append(f"{rel}:{hits[0][0]}")

    if missing and strict:
        raise RuntimeError("canonical enumerator not wired (missing repo_walk import) in: " + ", ".join(missing))
    if oswalk and strict:
        raise RuntimeError("ad-hoc os.walk reintroduced outside repo_walk in: " + ", ".join(oswalk))

def verify_repo_map_matches_canonical(cfg) -> None:
    """
    Compares project_repo_map.json contents to canonical repo_walk listing.
    This is deterministic and should hold whenever the repo map is freshly generated.
    """
    from tools.repo_walk import list_repo_files

    repo_map_path = REPO_ROOT / "project_repo_map.json"
    if not repo_map_path.exists():
        return

    import json
    data = json.loads(repo_map_path.read_text(encoding="utf-8"))
    files = data.get("files", {})
    if not isinstance(files, dict):
        return

    map_set = {k.replace("\\", "/") for k in files.keys()}
    canon = {p.replace("\\", "/") for p in list_repo_files(cfg, slim=False, allow_top_level=set())}

    if map_set != canon:
        # Show small diff
        only_map = sorted(map_set - canon)[:10]
        only_canon = sorted(canon - map_set)[:10]
        raise RuntimeError(
            "project_repo_map.json not consistent with canonical enumerator "
            f"(map={len(map_set)} canonical={len(canon)}). "
            f"Only-in-map: {only_map} ; Only-in-canonical: {only_canon}"
        )
