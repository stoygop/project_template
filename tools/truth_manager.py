from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from tools.ai_index import build_ai_index
from tools.verify_ai_index import main as verify_ai_index_main


REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_PY = REPO_ROOT / "app" / "version.py"
TRUTH_MD = REPO_ROOT / "TRUTH.md"
CONFIG_JSON = REPO_ROOT / "tools" / "truth_config.json"


@dataclass
class TruthConfig:
    zip_root: str
    ai_index_root: str
    exclude_common_folders: List[str]
    exclude_common_files: List[str]
    slim_exclude_folders: List[str]
    slim_exclude_ext: List[str]
    slim_exclude_extra_folders: List[str]

    @staticmethod
    def load(path: Path) -> "TruthConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return TruthConfig(
            zip_root=data.get("zip_root", "_truth"),
            ai_index_root=data.get("ai_index_root", "_ai_index"),
            exclude_common_folders=list(data.get("exclude_common_folders", [])),
            exclude_common_files=list(data.get("exclude_common_files", [])),
            slim_exclude_folders=list(data.get("slim_exclude_folders", [])),
            slim_exclude_ext=[s.lower() for s in data.get("slim_exclude_ext", [])],
            slim_exclude_extra_folders=list(data.get("slim_exclude_extra_folders", [])),
        )


def read_project_and_truth_version() -> Tuple[str, int]:
    txt = VERSION_PY.read_text(encoding="utf-8")

    m1 = re.search(r'PROJECT_NAME\s*=\s*"(.*?)"', txt)
    if not m1:
        raise RuntimeError(f"PROJECT_NAME not found in {VERSION_PY}")
    project = m1.group(1)

    m2 = re.search(r"TRUTH_VERSION\s*=\s*(\d+)", txt)
    if not m2:
        raise RuntimeError(f"TRUTH_VERSION not found in {VERSION_PY}")
    ver = int(m2.group(1))

    return project, ver


def write_truth_version(new_ver: int) -> None:
    txt = VERSION_PY.read_text(encoding="utf-8")
    txt2 = re.sub(r"TRUTH_VERSION\s*=\s*\d+", f"TRUTH_VERSION = {new_ver}", txt)
    # Atomic write: temp file then replace
    tmp = VERSION_PY.with_suffix(".py.tmp")
    tmp.write_text(txt2, encoding="utf-8")
    tmp.replace(VERSION_PY)



def _truth_version_assignment_paths() -> List[Path]:
    pat = re.compile(r"^\s*TRUTH_VERSION\s*=\s*\d+\s*$", re.MULTILINE)
    hits: List[Path] = []
    for p in REPO_ROOT.rglob("*.py"):
        if "_truth" in p.parts or "_ai_index" in p.parts or "__pycache__" in p.parts:
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        if pat.search(txt):
            hits.append(p)
    return hits


def assert_single_truth_version_authority() -> None:
    hits = _truth_version_assignment_paths()
    expected = VERSION_PY.resolve()
    if len(hits) != 1 or hits[0].resolve() != expected:
        rels = [str(p.relative_to(REPO_ROOT)) for p in hits]
        raise RuntimeError(
            "TRUTH_VERSION authority violation: expected exactly one integer assignment in app/version.py; "
            f"found {len(hits)} in: {rels}"
        )


def append_truth_md(project: str, new_ver: int, statement_lines: List[str]) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    bullets: List[str] = []
    for s in statement_lines:
        s = s.rstrip()
        if not s.strip():
            continue
        bullets.append(s if s.lstrip().startswith("- ") else f"- {s.strip()}")

    if not bullets:
        raise RuntimeError("Empty TRUTH statement not allowed.")

    entry = (
        "\n"
        "==================================================\n"
        f"TRUTH - {project} (TRUTH_V{new_ver})\n"
        "==================================================\n\n"
        "LOCKED\n"
        f"- Version: {new_ver}\n"
        f"- Timestamp: {ts}\n\n"
        "STATEMENT\n"
        + "\n".join(bullets)
        + "\n\n"
    )

    # Atomic write: write full new content to temp then replace
    current = TRUTH_MD.read_text(encoding="utf-8")
    tmp = TRUTH_MD.with_suffix(".md.tmp")
    tmp.write_text(current + entry, encoding="utf-8")
    tmp.replace(TRUTH_MD)


def _parts(rel: Path) -> Tuple[str, ...]:
    if rel.parent == Path("."):
        return tuple()
    return tuple(rel.parent.parts)


def should_exclude_common(rel: Path, cfg: TruthConfig) -> bool:
    parts = _parts(rel)
    for p in parts:
        if p in cfg.exclude_common_folders:
            return True
    if rel.name in cfg.exclude_common_files:
        return True
    # never include truth output folder itself
    if cfg.zip_root in parts or rel.parts[0] == cfg.zip_root:
        return True
    return False


def should_exclude_slim(rel: Path, cfg: TruthConfig) -> bool:
    parts = _parts(rel)
    # default slim exclude folders
    for p in parts:
        if p in cfg.slim_exclude_folders:
            return True
        if p in cfg.slim_exclude_extra_folders:
            return True
    # exclude by extension
    if rel.suffix.lower() in cfg.slim_exclude_ext:
        return True
    return False


def iter_repo_files(cfg: TruthConfig) -> Iterable[Path]:
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO_ROOT)
        if should_exclude_common(rel, cfg):
            continue
        yield p


def make_zip(zip_path: Path, cfg: TruthConfig, slim: bool) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = zip_path.with_name(f"tmp_{zip_path.stem}{zip_path.suffix}")
    if tmp_path.exists():
        tmp_path.unlink()
    if zip_path.exists():
        zip_path.unlink()

    with ZipFile(tmp_path, "w", compression=ZIP_DEFLATED) as z:
        for p in iter_repo_files(cfg):
            rel = p.relative_to(REPO_ROOT)

            if slim and should_exclude_slim(rel, cfg):
                continue

            z.write(p, arcname=str(rel).replace("\\", "/"))

    tmp_path.replace(zip_path)


def mint_truth(statement_text: str) -> Tuple[int, Path, Path]:
    cfg = TruthConfig.load(CONFIG_JSON)

    # Auto-clean legacy duplicate root version.py (authoritative is app/version.py)
    legacy = REPO_ROOT / "version.py"
    if legacy.exists():
        legacy.unlink()

    # Auto-clean legacy duplicate root truth_config.json (authoritative is tools/truth_config.json)
    legacy_cfg = REPO_ROOT / "truth_config.json"
    if legacy_cfg.exists():
        legacy_cfg.unlink()

    # Preflight: enforce single TRUTH_VERSION authority BEFORE minting
    assert_single_truth_version_authority()

    project, cur = read_project_and_truth_version()
    new_ver = cur + 1

    # Authoritative state update (mechanical, no manual edits)
    write_truth_version(new_ver)
    append_truth_md(project, new_ver, statement_text.splitlines())

    # Build ai index AFTER version bump, then verify contracts
    build_ai_index()
    verify_ai_index_main()

    from tools import verify_truth  # local import to avoid cycles

    print("PHASE 1/2: Pre-artifact verification")
    verify_truth.main(["--phase", "pre"])

    zip_root = REPO_ROOT / cfg.zip_root
    full_zip = zip_root / f"{project}_TRUTH_V{new_ver}_FULL.zip"
    slim_zip = zip_root / f"{project}_TRUTH_V{new_ver}_SLIM.zip"

    make_zip(full_zip, cfg, slim=False)
    make_zip(slim_zip, cfg, slim=True)

    print("PHASE 2/2: Post-artifact verification")
    verify_truth.main(["--phase", "post"])

    return new_ver, full_zip, slim_zip


def main() -> int:

    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "mint"])
    ap.add_argument("--statement-file", default="", help="Path to a text file containing the statement")
    args = ap.parse_args()

    project, cur = read_project_and_truth_version()

    if args.cmd == "status":
        print(f"{project} TRUTH_V{cur}")
        return 0

    if args.cmd == "mint":
        if not args.statement_file:
            raise SystemExit("mint requires --statement-file")
        st = Path(args.statement_file).read_text(encoding="utf-8")
        new_ver, full_zip, slim_zip = mint_truth(st)
        print(f"OK: minted TRUTH_V{new_ver}")
        print(f"FULL: {full_zip}")
        print(f"SLIM: {slim_zip}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
