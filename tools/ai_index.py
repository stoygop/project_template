from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from tools.truth_config import Config

# This script generates a NON-AUTHORITATIVE repository index intended for AI + humans.
# Output goes to <repo>/_ai_index/

GENERATOR_VERSION = "AI_INDEX_V1"

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
CONFIG_JSON = TOOLS_DIR / "truth_config.json"

VERSION_PY = REPO_ROOT / "app" / "version.py"
TRUTH_MD = REPO_ROOT / "TRUTH.md"


def _write_text_lf(path: Path, text: str) -> None:
    """Write UTF-8 text with LF newlines on all platforms.

    _ai_index integrity checks use raw byte sizes + sha256.
    If index artifacts are written with CRLF on Windows but verified with LF on
    GitHub Actions (Linux), the manifest will fail (size mismatch).
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _precheck_truth_contract() -> None:
    """Fast contract check that must never recurse into generated state.

    Enforce single TRUTH_VERSION authority (app/version.py only).
    """
    pat = re.compile(r"^\s*TRUTH_VERSION\s*=\s*\d+\s*$", re.MULTILINE)
    txt = VERSION_PY.read_text(encoding="utf-8", errors="replace") if VERSION_PY.exists() else ""
    hits = [VERSION_PY] if pat.search(txt) else []

    if len(hits) != 1:
        rels = [str(p.relative_to(REPO_ROOT)) for p in hits] if hits else []
        raise RuntimeError(
            "AI_INDEX precheck failed: TRUTH_VERSION authority violation. "
            "Expected exactly one assignment in app/version.py; "
            f"found {len(hits)} in {rels}"
        )
def _norm_rel(p: Path) -> str:
    return str(p).replace("\\", "/")


def _should_skip(rel: Path, cfg: Config) -> bool:
    # skip common folders anywhere in path
    parts = rel.parts
    for token in parts[:-1]:
        if token in cfg.exclude_common_folders:
            return True
    if rel.name in cfg.exclude_common_files:
        return True
    # always skip truth output + ai index output when *scanning repo* (to avoid recursion)
    if parts and parts[0] in (cfg.zip_root, cfg.ai_index_root):
        return True
    return False


def iter_repo_files(cfg: Config) -> Iterable[Path]:
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO_ROOT)
        if _should_skip(rel, cfg):
            continue
        yield p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_file_map(cfg: Config) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "generator": GENERATOR_VERSION,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "repo_root": str(REPO_ROOT),
        "files": [],
    }

    for p in iter_repo_files(cfg):
        rel = p.relative_to(REPO_ROOT)
        out["files"].append(
            {
                "path": _norm_rel(rel),
                "size": p.stat().st_size,
                "sha256": sha256_file(p),
            }
        )

    # stable ordering
    out["files"].sort(key=lambda x: x["path"])
    return out


class PyVisitor(ast.NodeVisitor):
    def __init__(self, module_path: str) -> None:
        self.module_path = module_path
        self.imports: List[Dict[str, Any]] = []
        self.defs: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []

        self._class_stack: List[str] = []

    def visit_Import(self, node: ast.Import) -> Any:
        for a in node.names:
            self.imports.append(
                {"kind": "import", "name": a.name, "asname": a.asname, "lineno": getattr(node, "lineno", None)}
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        mod = node.module or ""
        for a in node.names:
            self.imports.append(
                {
                    "kind": "from",
                    "module": mod,
                    "name": a.name,
                    "asname": a.asname,
                    "level": node.level,
                    "lineno": getattr(node, "lineno", None),
                }
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        entry = {
            "name": node.name,
            "lineno": getattr(node, "lineno", None),
            "end_lineno": getattr(node, "end_lineno", None),
            "is_method": bool(self._class_stack),
            "class": self._class_stack[-1] if self._class_stack else None,
        }
        if entry["is_method"]:
            self.defs.append({"kind": "method", **entry})
        else:
            self.functions.append(entry)
            self.defs.append({"kind": "function", **entry})
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        entry = {
            "name": node.name,
            "lineno": getattr(node, "lineno", None),
            "end_lineno": getattr(node, "end_lineno", None),
            "is_method": bool(self._class_stack),
            "class": self._class_stack[-1] if self._class_stack else None,
            "async": True,
        }
        if entry["is_method"]:
            self.defs.append({"kind": "async_method", **entry})
        else:
            self.functions.append(entry)
            self.defs.append({"kind": "async_function", **entry})
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        bases = []
        for b in node.bases:
            try:
                bases.append(ast.unparse(b))  # py3.9+
            except Exception:
                bases.append(getattr(b, "id", "<?>"))
        entry = {
            "name": node.name,
            "lineno": getattr(node, "lineno", None),
            "end_lineno": getattr(node, "end_lineno", None),
            "bases": bases,
        }
        self.classes.append(entry)
        self.defs.append({"kind": "class", **entry})

        self._class_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._class_stack.pop()


def module_name_from_path(rel_py: Path) -> str:
    # convert path like tools/foo.py -> tools.foo
    parts = list(rel_py.parts)
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    # drop __init__ module suffix
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([p for p in parts if p])


def parse_python_file(abs_path: Path, rel_path: Path) -> Dict[str, Any]:
    txt = abs_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(txt)
    vis = PyVisitor(module_path=_norm_rel(rel_path))
    vis.visit(tree)

    mod = module_name_from_path(rel_path)
    return {
        "path": _norm_rel(rel_path),
        "module": mod,
        "imports": vis.imports,
        "classes": vis.classes,
        "functions": vis.functions,
        "defs": vis.defs,
    }


def build_python_index(cfg: Config) -> Dict[str, Any]:
    modules: List[Dict[str, Any]] = []
    mod_to_imports: Dict[str, List[str]] = {}

    for p in iter_repo_files(cfg):
        rel = p.relative_to(REPO_ROOT)
        if rel.suffix.lower() != ".py":
            continue
        try:
            rec = parse_python_file(p, rel)
        except Exception as e:
            rec = {
                "path": _norm_rel(rel),
                "module": module_name_from_path(rel),
                "parse_error": str(e),
                "imports": [],
                "classes": [],
                "functions": [],
                "defs": [],
            }
        modules.append(rec)

        imports_flat: List[str] = []
        for imp in rec.get("imports", []):
            if imp.get("kind") == "import":
                imports_flat.append(imp.get("name", ""))
            elif imp.get("kind") == "from":
                mod = imp.get("module", "")
                if mod:
                    imports_flat.append(mod)
        mod_to_imports[rec["module"]] = sorted({x for x in imports_flat if x})

    # Code graph
    edges: List[Dict[str, str]] = []
    imported_by: Dict[str, List[str]] = {}
    for src, imps in mod_to_imports.items():
        for dst in imps:
            edges.append({"from": src, "to": dst})
            imported_by.setdefault(dst, []).append(src)

    for k in imported_by:
        imported_by[k] = sorted(set(imported_by[k]))

    edges.sort(key=lambda e: (e["from"], e["to"]))
    modules.sort(key=lambda m: m.get("module", ""))

    return {
        "generator": GENERATOR_VERSION,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modules": modules,
        "code_graph": {
            "edges": edges,                # import edges (module -> imported module)
            "imported_by": imported_by,    # reverse index
        },
    }


def build_entrypoints(cfg: Config) -> Dict[str, Any]:
    # Heuristics + explicit known entrypoints for this template style.
    candidates = [
        ("app/main.py", "python -m app.main"),
        ("tools/truth_gui.py", "python -m tools.truth_gui"),
        ("tools/truth_manager.py", "python -m tools.truth_manager status|mint"),
        ("tools/ai_index.py", "python -m tools.ai_index build|verify"),
        ("tools/verify_ai_index.py", "python -m tools.verify_ai_index"),
        ("tools/mint_truth.ps1", "powershell -ExecutionPolicy Bypass -File .\\tools\\mint_truth.ps1"),
        ("tools/new_project.ps1", "powershell -ExecutionPolicy Bypass -File .\\tools\\new_project.ps1 -NewName <name>"),
    ]

    found: List[Dict[str, str]] = []
    for rel_str, cmd in candidates:
        rel = Path(rel_str)
        if (REPO_ROOT / rel).exists():
            found.append({"path": rel_str.replace("\\", "/"), "how_to_run": cmd})

    return {
        "generator": GENERATOR_VERSION,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "entrypoints": found,
    }


def write_index_manifest(ai_dir: Path, files_written: List[Path]) -> None:
    # _ai_index_INDEX.txt contains hashes for integrity
    lines: List[str] = []
    lines.append(f"AI_INDEX_MANIFEST {GENERATOR_VERSION}")
    lines.append(f"generated_at={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    for p in sorted(files_written, key=lambda x: x.name):
        h = sha256_file(p)
        size = p.stat().st_size
        lines.append(f"{p.name}\t{size}\t{h}")
    _write_text_lf(ai_dir / "_ai_index_INDEX.txt", "\n".join(lines) + "\n")


def write_readme(ai_dir: Path) -> None:
    txt = (
        "_ai_index\n"
        "=========\n\n"
        "NON-AUTHORITATIVE helper artifacts for fast navigation (AI + human).\n"
        "These files are generated. Source of truth remains the repository itself.\n\n"
        "Contents:\n"
        "- _file_map.json: file list + size + sha256\n"
        "- python_index.json: python symbols/imports + code graph\n"
        "- entrypoints.json: semantic entrypoints (how to run / where to start)\n"
        "- _ai_index_INDEX.txt: integrity manifest (sha256 of index outputs)\n"
    )
    _write_text_lf(ai_dir / "_ai_index_README.txt", txt)


def write_why(ai_dir: Path) -> None:
    txt = (
        "WHY THIS INDEX EXISTS\n"
        "====================\n\n"
        "_ai_index exists to reduce re-analysis cost for humans and AI.\n\n"
        "It is:\n"
        "- deterministic\n"
        "- non-authoritative\n"
        "- regenerated during Truth minting\n\n"
        "It should never be treated as the source of truth.\n"
    )
    _write_text_lf(ai_dir / "_WHY.txt", txt)


def build_ai_index() -> Path:
    _precheck_truth_contract()
    cfg = Config.load(CONFIG_JSON)
    ai_dir = REPO_ROOT / cfg.ai_index_root

    # Atomic rebuild: build into a temp dir then swap into place.
    tmp_parent = ai_dir.parent
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{cfg.ai_index_root}_tmp_", dir=str(tmp_parent)))

    files_written: List[Path] = []

    # Generate
    file_map = build_file_map(cfg)
    p_file_map = tmp_dir / "_file_map.json"
    _write_text_lf(p_file_map, json.dumps(file_map, indent=2) + "\n")
    files_written.append(p_file_map)

    py_index = build_python_index(cfg)
    p_py = tmp_dir / "python_index.json"
    _write_text_lf(p_py, json.dumps(py_index, indent=2) + "\n")
    files_written.append(p_py)

    entrypoints = build_entrypoints(cfg)
    p_ep = tmp_dir / "entrypoints.json"
    _write_text_lf(p_ep, json.dumps(entrypoints, indent=2) + "\n")
    files_written.append(p_ep)

    write_readme(tmp_dir)
    files_written.append(tmp_dir / "_ai_index_README.txt")

    write_why(tmp_dir)
    files_written.append(tmp_dir / "_WHY.txt")

    write_index_manifest(tmp_dir, files_written)
    files_written.append(tmp_dir / "_ai_index_INDEX.txt")

    # Swap into place
    backup_dir = None
    try:
        if ai_dir.exists():
            backup_dir = ai_dir.with_name(f"{ai_dir.name}_old")
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            ai_dir.replace(backup_dir)
        tmp_dir.replace(ai_dir)
    finally:
        # Cleanup backup and any leftover temp dir
        if backup_dir and backup_dir.exists():
            shutil.rmtree(backup_dir)
        if tmp_dir.exists() and tmp_dir != ai_dir:
            shutil.rmtree(tmp_dir)

    return ai_dir


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    args = ap.parse_args()

    if args.cmd == "build":
        ai_dir = build_ai_index()
        print(f"OK: built ai index at {ai_dir}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
