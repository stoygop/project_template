from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from tools.ai_index import build_ai_index
from tools.verify_ai_index import main as verify_ai_index_main

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_PY = REPO_ROOT / "app" / "version.py"
TRUTH_MD = REPO_ROOT / "TRUTH.md"
CONFIG_JSON = REPO_ROOT / "tools" / "truth_config.json"

_TRUTH_HEADER_RE = re.compile(r"^TRUTH\s*-\s*(.+)\s+\(TRUTH_V(\d+)\)\s*$")


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
            exclude_common_folders=data.get("exclude_common_folders", []),
            exclude_common_files=data.get("exclude_common_files", []),
            slim_exclude_folders=data.get("slim_exclude_folders", []),
            slim_exclude_ext=data.get("slim_exclude_ext", []),
            slim_exclude_extra_folders=data.get("slim_exclude_extra_folders", []),
        )


def _norm_newlines(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")


def _strip_bom(s: str) -> str:
    # Guard against UTF-8 BOM appearing as U+FEFF at the start of a line.
    # This commonly happens when text is written by PowerShell with a BOM.
    return s.lstrip("\ufeff")


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
    txt = _norm_newlines(VERSION_PY.read_text(encoding="utf-8"))
    if re.search(r"TRUTH_VERSION\s*=\s*\d+", txt) is None:
        raise RuntimeError("TRUTH_VERSION assignment not found")
    txt = re.sub(r"TRUTH_VERSION\s*=\s*\d+", f"TRUTH_VERSION = {new_ver}", txt)
    VERSION_PY.write_text(txt, encoding="utf-8", newline="\n")


def append_truth_md_verbatim(project: str, new_ver: int, block_text: str) -> None:
    """
    Append the provided TRUTH block verbatim into TRUTH.md.
    Requirements:
      - block must contain header line 'TRUTH - <project> (TRUTH_V<new_ver>)'
      - block must contain a standalone 'END' line
      - TRUTH.md is normalized to LF and we always separate entries with a blank line
    """
    if not TRUTH_MD.exists():
        raise RuntimeError(f"missing {TRUTH_MD}")

    block = _strip_bom(_norm_newlines(block_text)).strip("\n") + "\n"
    lines = block.split("\n")

    # Validate header/version
    header_line = None
    for line in lines:
        candidate = _strip_bom(line).strip()
        m = _TRUTH_HEADER_RE.match(candidate)
        if m:
            header_line = candidate
            got_project = m.group(1).strip()
            got_ver = int(m.group(2))
            if got_project != project:
                raise RuntimeError(f"TRUTH project mismatch: got '{got_project}' expected '{project}'")
            if got_ver != new_ver:
                raise RuntimeError(f"TRUTH version mismatch: got TRUTH_V{got_ver} expected TRUTH_V{new_ver}")
            break
    if header_line is None:
        raise RuntimeError("TRUTH block missing header line: TRUTH - <project> (TRUTH_V#)")

    # Validate END terminator exists as standalone line
    if not any(_strip_bom(l).strip() == "END" for l in lines):
        raise RuntimeError("TRUTH block missing END terminator line")

    # Normalize existing TRUTH.md and ensure it ends with exactly one blank line
    cur = _norm_newlines(TRUTH_MD.read_text(encoding="utf-8"))
    cur = cur.rstrip("\n") + "\n\n"

    out = cur + block + "\n"
    TRUTH_MD.write_text(out, encoding="utf-8", newline="\n")


def should_exclude_common(rel: Path, cfg: TruthConfig) -> bool:
    if rel.name in cfg.exclude_common_files:
        return True
    for part in rel.parts:
        if part in cfg.exclude_common_folders:
            return True
    return False


def should_exclude_slim(rel: Path, cfg: TruthConfig) -> bool:
    for part in rel.parts:
        if part in cfg.slim_exclude_folders:
            return True
        if part in cfg.slim_exclude_extra_folders:
            return True
    if rel.suffix.lower().lstrip(".") in cfg.slim_exclude_ext:
        return True
    return False


def iter_repo_files(cfg: TruthConfig) -> Iterable[Path]:
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO_ROOT)

        # Never include .git
        if ".git" in rel.parts:
            continue

        # Exclude common
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
    """
    Mint next truth:
      - Pre-verify (phase pre)
      - Append verbatim TRUTH block
      - Bump TRUTH_VERSION
      - Rebuild/verify _ai_index
      - Create FULL+SLIM zips
      - Post-verify (phase post)
    """
    cfg = TruthConfig.load(CONFIG_JSON)

    from tools import verify_truth  # local import to avoid cycles

    print("PHASE 0/2: Pre-mint verification")
    verify_truth.main(["--phase", "pre"])

    project, cur = read_project_and_truth_version()
    new_ver = cur + 1

    # Append truth then bump version (keeps TRUTH.md as primary log)
    append_truth_md_verbatim(project, new_ver, statement_text)
    write_truth_version(new_ver)

    # Build ai index AFTER version bump, then verify contracts
    build_ai_index()
    verify_ai_index_main()

    zip_root = REPO_ROOT / cfg.zip_root
    full_zip = zip_root / f"{project}_TRUTH_V{new_ver}_FULL.zip"
    slim_zip = zip_root / f"{project}_TRUTH_V{new_ver}_SLIM.zip"

    make_zip(full_zip, cfg, slim=False)
    make_zip(slim_zip, cfg, slim=True)

    print("PHASE 2/2: Post-artifact verification")
    verify_truth.main(["--phase", "post"])

    return new_ver, full_zip, slim_zip


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tools.truth_manager")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="print current project and TRUTH version")

    ap_mint = sub.add_parser("mint", help="mint next TRUTH")
    ap_mint.add_argument("--statement-file", required=True, help="path to statement text file")

    args = ap.parse_args(argv)

    project, cur = read_project_and_truth_version()

    if args.cmd == "status":
        print(f"{project} TRUTH_V{cur}")
        return 0

    if args.cmd == "mint":
        st = Path(args.statement_file).read_text(encoding="utf-8")
        new_ver, full_zip, slim_zip = mint_truth(st)
        print(f"OK: minted TRUTH_V{new_ver}")
        print(f"FULL: {full_zip}")
        print(f"SLIM: {slim_zip}")
        return 0

    raise SystemExit("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())