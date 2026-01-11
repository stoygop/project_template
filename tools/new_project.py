# tools/new_project.py
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _write_text_atomic(p: Path, text: str) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def _safe_project_name(name: str) -> str:
    name = name.strip()
    if not name:
        _die("Project name is empty.")
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", name):
        _die("Project name must match: [A-Za-z0-9_-]+")
    return name


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        _die(f"Destination already exists: {dst}")
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(
            ".git",
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".venv",
            "venv",
            "_truth",
            "_ai_index",
        ),
    )


def _iter_text_files(repo_root: Path) -> list[Path]:
    # Conservative: scan typical text files; skip likely binaries.
    exts = {
        ".py", ".ps1", ".txt", ".md", ".json", ".yml", ".yaml",
        ".toml", ".ini", ".cfg", ".gitignore",
    }
    out: list[Path] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root)
        # Skip generated/large/binary dirs
        if any(part in {"_truth", "_ai_index", "__pycache__", ".git"} for part in rel.parts):
            continue
        if p.suffix.lower() in exts or p.name in {"README", "README.txt", "TRUTH.md", ".gitignore"}:
            out.append(p)
    return out


def _replace_project_name(repo_root: Path, old: str, new: str) -> None:
    # Replace only the exact token string occurrences (safe, explicit).
    files = _iter_text_files(repo_root)
    for p in files:
        try:
            text = _read_text(p)
        except UnicodeDecodeError:
            continue
        if old not in text:
            continue
        _write_text_atomic(p, text.replace(old, new))


def _reset_dirs(repo_root: Path) -> None:
    for d in (repo_root / "_truth", repo_root / "_ai_index"):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    # Remove legacy duplicate config if present (authoritative is tools/truth_config.json)
    legacy_cfg = repo_root / "truth_config.json"
    if legacy_cfg.exists():
        legacy_cfg.unlink()


def _set_version_and_project(repo_root: Path, project_name: str) -> None:
    vfile = repo_root / "app" / "version.py"
    if not vfile.exists():
        _die(f"Missing expected file: {vfile}")

    text = _read_text(vfile)

    # Force authoritative values.
    text = re.sub(r'^\s*PROJECT_NAME\s*=\s*.*$', f'PROJECT_NAME = "{project_name}"', text, flags=re.M)
    text = re.sub(r'^\s*TRUTH_VERSION\s*=\s*\d+\s*$', "TRUTH_VERSION = 1", text, flags=re.M)

    # If either line was missing, append them.
    if "PROJECT_NAME" not in text:
        text = text.rstrip() + f'\nPROJECT_NAME = "{project_name}"\n'
    if "TRUTH_VERSION" not in text:
        text = text.rstrip() + "\nTRUTH_VERSION = 1\n"

    _write_text_atomic(vfile, text)


def _seed_truth_md(repo_root: Path, project_name: str) -> None:
    truth = repo_root / "TRUTH.md"
    content = (
        "==================================================\n"
        f"TRUTH - {project_name} (TRUTH_V1)\n"
        "==================================================\n\n"
        "LOCKED\n"
        "- Initial project seed from project_template\n\n"
        "STATE\n"
        "- Repo created via tools/new_project\n"
        "- TRUTH_VERSION set to 1\n"
        "- _truth and _ai_index reset\n\n"
        "NOTES\n"
        "- Mint the next truth to begin work\n"
        "\n"
    )
    _write_text_atomic(truth, content)



def _run_ai_index_build(repo_root: Path) -> None:
    cmd = [sys.executable, "-m", "tools.ai_index", "build"]
    print("NEW_PROJECT: running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(repo_root))
    if proc.returncode != 0:
        _die("AI index build failed in new project.", code=proc.returncode)


def _run_verify_pre(repo_root: Path) -> None:
    cmd = [sys.executable, "-m", "tools.verify_truth", "--phase", "pre"]
    print("NEW_PROJECT: running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(repo_root))
    if proc.returncode != 0:
        _die("Verification failed in new project (phase pre).", code=proc.returncode)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Create a new project from the template with truth reseed.")
    ap.add_argument("--name", required=True, help="New project name (token-safe: letters/numbers/_/-)")
    ap.add_argument("--dest", required=True, help="Destination directory path for the new project folder")
    args = ap.parse_args(argv)

    new_name = _safe_project_name(args.name)

    src_root = Path(__file__).resolve().parents[1]
    dest_root = Path(args.dest).expanduser().resolve()
    dst = dest_root / new_name

    # Determine old name from app/version.py (authoritative)
    src_vfile = src_root / "app" / "version.py"
    if not src_vfile.exists():
        _die(f"Missing expected file in template: {src_vfile}")
    src_vtext = _read_text(src_vfile)
    m = re.search(r'^\s*PROJECT_NAME\s*=\s*"([^"]+)"\s*$', src_vtext, flags=re.M)
    old_name = m.group(1) if m else "project_template"

    print(f"NEW_PROJECT: src={src_root}")
    print(f"NEW_PROJECT: dst={dst}")
    print(f"NEW_PROJECT: old_name={old_name} new_name={new_name}")

    _copy_tree(src_root, dst)
    _reset_dirs(dst)
    _replace_project_name(dst, old_name, new_name)
    _set_version_and_project(dst, new_name)
    _seed_truth_md(dst, new_name)
    _run_ai_index_build(dst)
    _run_verify_pre(dst)

    print("NEW_PROJECT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
