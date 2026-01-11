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

# D (phased) format support
_SEPARATOR = "=" * 50

# Header supports optional D type tag: [CONFIRM|DREAM|DEBUG]
_TRUTH_HEADER_RE = re.compile(
    r"^TRUTH\s*-\s*(.+)\s+\(TRUTH_V(\d+)\)\s*(?:\[(CONFIRM|DREAM|DEBUG)\])?\s*$"
)


@dataclass
class TruthConfig:
    zip_root: str
    ai_index_root: str
    exclude_common_folders: List[str]
    exclude_common_files: List[str]
    slim_exclude_folders: List[str]
    slim_exclude_ext: List[str]
    slim_exclude_extra_folders: List[str]
    truth_phases_required: bool
    draft_root: str

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
            truth_phases_required=bool(data.get("truth_phases_required", False)),
            draft_root=data.get("draft_root", "_truth_drafts"),
        )


def _write_truth_config_truth_phases_required(required: bool) -> None:
    data = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    data["truth_phases_required"] = bool(required)
    CONFIG_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


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

    cfg = TruthConfig.load(CONFIG_JSON)

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
        raise RuntimeError(
            "TRUTH block missing header line: TRUTH - <project> (TRUTH_V#) optionally followed by [CONFIRM|DREAM|DEBUG]"
        )

    # Validate END terminator exists as standalone line
    if not any(_strip_bom(l).strip() == "END" for l in lines):
        raise RuntimeError("TRUTH block missing END terminator line")

    # If phased truths are required, enforce LOCKED PRE + LOCKED POST within the block.
    if cfg.truth_phases_required:
        has_pre = any(_strip_bom(l).strip() == "LOCKED PRE" for l in lines)
        has_post = any(_strip_bom(l).strip() == "LOCKED POST" for l in lines)
        has_legacy = any(_strip_bom(l).strip() == "LOCKED" for l in lines)
        if has_legacy:
            raise RuntimeError("TRUTH block contains legacy 'LOCKED' header (phases required). Use LOCKED PRE/LOCKED POST.")
        if not has_pre or not has_post:
            raise RuntimeError("TRUTH block missing required phased headers: LOCKED PRE and LOCKED POST")

    # Normalize existing TRUTH.md and ensure it ends with exactly one blank line
    cur = _norm_newlines(TRUTH_MD.read_text(encoding="utf-8"))
    cur = cur.rstrip("\n") + "\n\n"

    out = cur + block + "\n"
    TRUTH_MD.write_text(out, encoding="utf-8", newline="\n")



_DRAFT_FILE_RE = re.compile(r"^(?P<project>.+?)_TRUTH_V(?P<ver>\d+)_DRAFT\.txt$")


def get_draft_dir(cfg: TruthConfig) -> Path:
    return REPO_ROOT / cfg.draft_root


def get_draft_path(project: str, ver: int, cfg: TruthConfig) -> Path:
    return get_draft_dir(cfg) / f"{project}_TRUTH_V{ver}_DRAFT.txt"


def find_pending_draft(project: str, cfg: TruthConfig) -> Tuple[int, Path] | None:
    ddir = get_draft_dir(cfg)
    if not ddir.exists():
        return None
    best: Tuple[int, Path] | None = None
    for p in ddir.glob(f"{project}_TRUTH_V*_DRAFT.txt"):
        m = _DRAFT_FILE_RE.match(p.name)
        if not m:
            continue
        v = int(m.group("ver"))
        if best is None or v > best[0]:
            best = (v, p)
    return best


def write_draft(project: str, ver: int, statement_text: str, cfg: TruthConfig, overwrite: bool = False) -> Path:
    path = get_draft_path(project, ver, cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise RuntimeError(f"draft already exists: {path}")
    txt = _strip_bom(_norm_newlines(statement_text)).strip("\n") + "\n"
    path.write_text(txt, encoding="utf-8", newline="\n")
    return path


def delete_draft(path: Path) -> None:
    if path.exists():
        path.unlink()

def should_exclude_common(rel: Path, cfg: TruthConfig) -> bool:
    # Never package other zip files into truth zips.
    if rel.suffix.lower() == ".zip":
        return True
    # Never package transient statement files.
    if rel.name.startswith(".truth_statement_") and rel.suffix.lower() == ".txt":
        return True
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
    # Extensions in config are stored with the leading dot (e.g. ".png").
    if rel.suffix.lower() in {e.lower() for e in cfg.slim_exclude_ext}:
        return True
    return False


def _d_epoch_truth_v1(project: str) -> str:
    # Canonical phased truth seed.
    return "\n".join(
        [
            _SEPARATOR,
            f"TRUTH - {project} (TRUTH_V1)",
            _SEPARATOR,
            "",
            "LOCKED PRE",
            "- D epoch reset: TRUTH.md is reseeded under phased format",
            "- Prior truths are archived to TRUTH_LEGACY.md and are not enforced",
            "- truth_phases_required is enabled (LOCKED PRE/LOCKED POST required)",
            "- TRUTH_VERSION is reset to 1 in app/version.py",
            "",
            "LOCKED POST",
            "- TRUTH_LEGACY.md exists and contains the pre-D truth history",
            "- TRUTH.md is now the only authoritative truth log",
            "- Verification enforces phased truth format for all future entries",
            "",
            "END",
            "",
        ]
    )


def reseed_truth_epoch(force: bool = False) -> None:
    project, cur = read_project_and_truth_version()
    if not force:
        raise RuntimeError(f"reseed requires --force (current TRUTH_V{cur})")

    # Archive TRUTH.md -> TRUTH_LEGACY.md (overwrite if present)
    legacy = REPO_ROOT / "TRUTH_LEGACY.md"
    if TRUTH_MD.exists():
        legacy.write_text(_norm_newlines(TRUTH_MD.read_text(encoding="utf-8", errors="replace")), encoding="utf-8", newline="\n")
        TRUTH_MD.unlink()

    # Enable phased truths.
    _write_truth_config_truth_phases_required(True)

    # Reset version to 1.
    write_truth_version(1)

    # Create new TRUTH.md seeded with D epoch V1.
    TRUTH_MD.write_text(_d_epoch_truth_v1(project), encoding="utf-8", newline="\n")

    # Rebuild ai index and verify repo in pre phase (artifacts optional here).
    build_ai_index()
    verify_ai_index_main()

    from tools import verify_truth
    verify_truth.main(["--phase", "pre"])


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



def mint_draft(statement_text: str, overwrite: bool = False) -> Tuple[int, Path]:
    """
    Create/update a draft truth for TRUTH_V(cur+1) WITHOUT bumping TRUTH_VERSION and WITHOUT creating zips.
    Drafts live outside TRUTH.md and are not part of contiguity/validation.
    """
    cfg = TruthConfig.load(CONFIG_JSON)
    from tools import verify_truth  # local import to avoid cycles

    print("PHASE 0/1: Pre-draft verification")
    verify_truth.main(["--phase", "pre"])

    project, cur = read_project_and_truth_version()
    draft_ver = cur + 1
    draft_path = write_draft(project, draft_ver, statement_text, cfg, overwrite=overwrite)
    print(f"OK: drafted TRUTH_V{draft_ver}")
    print(f"DRAFT: {draft_path}")
    return draft_ver, draft_path


def confirm_draft() -> Tuple[int, Path, Path]:
    """
    Confirm the pending draft for TRUTH_V(cur+1):
      - Pre-verify (phase pre)
      - Append draft block into TRUTH.md
      - Bump TRUTH_VERSION
      - Rebuild/verify _ai_index
      - Create FULL+SLIM zips
      - Post-verify (phase post)
      - Delete the draft file
    """
    cfg = TruthConfig.load(CONFIG_JSON)
    from tools import verify_truth  # local import to avoid cycles

    print("PHASE 0/2: Pre-confirm verification")
    verify_truth.main(["--phase", "pre"])

    project, cur = read_project_and_truth_version()
    new_ver = cur + 1

    pending = find_pending_draft(project, cfg)
    if pending is None:
        raise RuntimeError(f"no pending draft found for project '{project}'")
    draft_ver, draft_path = pending
    if draft_ver != new_ver:
        raise RuntimeError(f"pending draft is TRUTH_V{draft_ver} but expected TRUTH_V{new_ver} (based on app/version.py)")

    statement_text = draft_path.read_text(encoding="utf-8")

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

    delete_draft(draft_path)
    print(f"OK: confirmed TRUTH_V{new_ver} (draft deleted)")

    return new_ver, full_zip, slim_zip

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

    ap_status = sub.add_parser("status", help="print current project and TRUTH version")
    ap_status.add_argument("--json", action="store_true", help="emit machine-readable json")

    ap_reseed = sub.add_parser("reseed", help="archive legacy TRUTH.md and reseed a new phased TRUTH epoch starting at V1")
    ap_reseed.add_argument("--force", action="store_true", help="required: perform destructive reseed")

    ap_mint = sub.add_parser("mint", help="mint next TRUTH (immediate confirm; legacy)")
    ap_mint.add_argument("--statement-file", required=True, help="path to statement text file")

    ap_draft = sub.add_parser("mint-draft", help="create/update draft for next TRUTH without version bump")
    ap_draft.add_argument("--statement-file", required=True, help="path to draft statement text file")
    ap_draft.add_argument("--overwrite", action="store_true", help="overwrite existing draft for the same version")

    sub.add_parser("confirm-draft", help="confirm pending draft for next TRUTH (bumps version + zips)")

    args = ap.parse_args(argv)

    project, cur = read_project_and_truth_version()
    if args.cmd == "status":
        cfg = TruthConfig.load(CONFIG_JSON)
        pending = find_pending_draft(project, cfg)
        payload = {
            "project": project,
            "confirmed": cur,
            "next": cur + 1,
            "draft_pending": None,
        }
        if pending is not None:
            dv, dp = pending
            payload["draft_pending"] = {"ver": dv, "path": str(dp)}
        if getattr(args, "json", False):
            print(json.dumps(payload))
        else:
            if pending is None:
                print(f"{project} TRUTH_V{cur} (no draft)")
            else:
                print(f"{project} TRUTH_V{cur} (draft pending TRUTH_V{pending[0]})")
        return 0
    if args.cmd == "reseed":
        reseed_truth_epoch(force=bool(args.force))
        print("OK: reseeded TRUTH epoch (TRUTH_V1) and enabled phased truths")
        return 0

    if args.cmd == "mint-draft":
        st = Path(args.statement_file).read_text(encoding="utf-8")
        dv, dp = mint_draft(st, overwrite=bool(args.overwrite))
        return 0

    if args.cmd == "confirm-draft":
        new_ver, full_zip, slim_zip = confirm_draft()
        print(f"OK: confirmed TRUTH_V{new_ver}")
        print(f"FULL: {full_zip}")
        print(f"SLIM: {slim_zip}")
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
