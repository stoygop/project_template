from __future__ import annotations

import argparse
import sys
import os
import json
import shutil
import datetime
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from tools.ai_index import build_ai_index
from tools.make_truth_zip import make_zip
from tools.truth_config import Config
from tools.verify_ai_index import main as verify_ai_index_main

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_PY = REPO_ROOT / "app" / "version.py"
def _backup_root_external(project: str) -> Path:
    """Return backup root directory for confirm-draft snapshots.

    Default behavior stores backups OUTSIDE the repo to prevent recursive contamination.
    Override with env var TRUTH_BACKUP_DIR to choose a base directory.
    """
    base = os.environ.get("TRUTH_BACKUP_DIR", "").strip()
    if base:
        base_dir = Path(base).expanduser()
    else:
        base_dir = Path.home() / "Documents" / "Programming" / f"{project}_backups"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_dir / f"before_confirm_{stamp}"
TRUTH_MD = REPO_ROOT / "TRUTH.md"
CONFIG_JSON = REPO_ROOT / "tools" / "truth_config.json"


def _write_last_backup_marker(cfg: "TruthConfig", backup_zip: Path) -> Path:
    """Write a marker that identifies the before_confirm backup zip produced by confirm-draft.

    Stored at: <zip_root>/last_before_confirm_backup.json
      - zip_root is typically "_truth"
    Not included in truth zips because _truth is excluded from enumeration.

    Returns the marker path.
    """
    marker_dir = REPO_ROOT / cfg.zip_root
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / "last_before_confirm_backup.json"

    payload = {
        "backup_zip": str(backup_zip),
        "written_at_local": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
    }

    tmp = marker.with_suffix(marker.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(marker)
    return marker


# D (phased) format support
_SEPARATOR = "=" * 50

# Header supports optional D type tag: [CONFIRM|DREAM|DEBUG]
# Tolerate unicode dash variants (en/em dashes) that users sometimes paste.
_TRUTH_HEADER_RE = re.compile(
    r"^TRUTH\s*[-\u2013\u2014]\s*(.+)\s+\(TRUTH_V(\d+)\)\s*(?:\[(CONFIRM|DREAM|DEBUG)\])?\s*$"
)

# Draft filename: <project>_TRUTH_V<ver>_DRAFT.txt
_DRAFT_FILE_RE = re.compile(r"^(?P<project>.+)_TRUTH_V(?P<ver>\d+)_DRAFT\.txt$", re.IGNORECASE)


def _normalize_truth_candidate(line: str) -> str:
    """Normalize a single line for truth parsing (tolerate markdown/BOM)."""
    s = _strip_bom(line).rstrip("\r\n")
    indent = re.match(r"^\s*", s).group(0)
    core = s.strip()
    if core.startswith("#"):
        stripped = core.lstrip("#").strip()
        if _TRUTH_HEADER_RE.match(stripped) or stripped in {"LOCKED", "LOCKED PRE", "LOCKED POST", "END"}:
            return indent + stripped
    if core.startswith("* "):
        return indent + "- " + core[2:]
    return s

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


def read_truth_md_latest() -> Tuple[str, int, str | None]:
    """Return (project, ver, type_tag) for the latest TRUTH entry in TRUTH.md."""
    if not TRUTH_MD.exists():
        raise RuntimeError(f"missing {TRUTH_MD}")

    txt = _strip_bom(_norm_newlines(TRUTH_MD.read_text(encoding="utf-8")))
    latest: Tuple[str, int, str | None] | None = None
    for raw in txt.split("\n"):
        line = _strip_bom(raw).strip()
        m = _TRUTH_HEADER_RE.match(line)
        if not m:
            continue
        proj = m.group(1).strip()
        ver = int(m.group(2))
        tag = m.group(3)
        if latest is None or ver > latest[1]:
            latest = (proj, ver, tag)

    if latest is None:
        raise RuntimeError("no TRUTH headers found in TRUTH.md")
    return latest


def set_truth_type_tag(ver: int, type_tag: str | None) -> None:
    """Set (or clear) the optional [CONFIRM|DREAM|DEBUG] tag on a specific TRUTH header."""
    if type_tag is not None and type_tag not in ("CONFIRM", "DREAM", "DEBUG"):
        raise RuntimeError("type_tag must be one of CONFIRM, DREAM, DEBUG, or None")

    txt = _strip_bom(_norm_newlines(TRUTH_MD.read_text(encoding="utf-8")))
    out_lines: List[str] = []
    changed = False
    for raw in txt.split("\n"):
        line = _strip_bom(raw).rstrip("\r")
        m = _TRUTH_HEADER_RE.match(line.strip())
        if m and int(m.group(2)) == ver:
            proj = m.group(1).strip()
            base = f"TRUTH - {proj} (TRUTH_V{ver})"
            if type_tag:
                base += f" [{type_tag}]"
            out_lines.append(base)
            changed = True
        else:
            out_lines.append(line)

    if not changed:
        raise RuntimeError(f"TRUTH_V{ver} header not found in TRUTH.md")

    TRUTH_MD.write_text("\n".join(out_lines).rstrip("\n") + "\n", encoding="utf-8", newline="\n")


def write_truth_version(new_ver: int) -> None:
    txt = _norm_newlines(VERSION_PY.read_text(encoding="utf-8"))
    if re.search(r"TRUTH_VERSION\s*=\s*\d+", txt) is None:
        raise RuntimeError("TRUTH_VERSION assignment not found")
    txt = re.sub(r"TRUTH_VERSION\s*=\s*\d+", f"TRUTH_VERSION = {new_ver}", txt)
    VERSION_PY.write_text(txt, encoding="utf-8", newline="\n")


def append_truth_md_verbatim(project: str, new_ver: int, block_text: str) -> None:
    """
    Append the provided TRUTH block verbatim into TRUTH.md.

    Tolerances:
      - leading/trailing whitespace and UTF-8 BOM
      - markdown heading prefix '# ' on control lines (header / LOCKED PRE/POST / END)
      - markdown bullet prefix '* ' (converted to '- ')

    Requirements:
      - must contain header line 'TRUTH - <project> (TRUTH_V<new_ver>)' (optionally [CONFIRM|DREAM|DEBUG])
      - must contain standalone 'END' line
      - if phases are required, must contain LOCKED PRE and LOCKED POST (and must NOT contain legacy LOCKED)
    """
    if not TRUTH_MD.exists():
        raise RuntimeError(f"missing {TRUTH_MD}")

    cfg = TruthConfig.load(CONFIG_JSON)

    block_raw = _strip_bom(_norm_newlines(block_text)).strip("\n") + "\n"
    raw_lines = block_raw.split("\n")
    lines = [_normalize_truth_candidate(l) for l in raw_lines]

    # Validate header/version and locate header index
    header_idx = None
    for i, line in enumerate(lines):
        candidate = _strip_bom(line).strip()
        m = _TRUTH_HEADER_RE.match(candidate)
        if m:
            header_idx = i
            got_project = m.group(1).strip()
            got_ver = int(m.group(2))
            if got_project != project:
                raise RuntimeError(f"TRUTH project mismatch: got '{got_project}' expected '{project}'")
            if got_ver != new_ver:
                raise RuntimeError(f"TRUTH version mismatch: got TRUTH_V{got_ver} expected TRUTH_V{new_ver}")
            break
    if header_idx is None:
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
            raise RuntimeError(
                "TRUTH block contains legacy 'LOCKED' header (phases required). Use LOCKED PRE/LOCKED POST."
            )
        if not has_pre or not has_post:
            raise RuntimeError("TRUTH block missing required phased headers: LOCKED PRE and LOCKED POST")

    # Trim any preamble before the header and anything after END.
    lines = lines[header_idx:]
    end_idx = None
    for i, l in enumerate(lines):
        if _strip_bom(l).strip() == "END":
            end_idx = i
            break
    if end_idx is not None:
        lines = lines[: end_idx + 1]

    block = "\n".join(lines).strip("\n") + "\n"

    # Normalize existing TRUTH.md and ensure it ends with exactly one blank line
    cur = _norm_newlines(TRUTH_MD.read_text(encoding="utf-8"))
    cur = cur.rstrip("\n") + "\n\n"

    out = cur + block + "\n"
    TRUTH_MD.write_text(out, encoding="utf-8", newline="\n")


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
    verify_ai_index_main([])

    from tools import verify_truth
    verify_truth.main(["--phase", "pre"])


def iter_repo_files(cfg: TruthConfig) -> Iterable[Path]:
    # Back-compat wrapper: authoritative walk is tools.repo_walk
    cfg_obj = Config.load(CONFIG_JSON)
    allow_top = {cfg_obj.ai_index_root} if cfg_obj.ai_index_root else set()
    from tools.repo_walk import iter_repo_files as _iter
    yield from _iter(cfg_obj, slim=False, allow_top_level=allow_top)

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

    # Backup key files before modifying anything (so we can go back without Git)
    # Create a rollback snapshot BEFORE mutation (backups stored outside repo by default)
    backup_root = _backup_root_external(project)
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TRUTH_MD, backup_root / "TRUTH.md")
    shutil.copy2(VERSION_PY, backup_root / "version.py")

    # Create a faithful repo snapshot backup (nested zip + manifest)
    from tools.repo_backup import build_repo_backup_zip, validate_repo_backup_zip
    backup_zip = build_repo_backup_zip(project=project, cfg=cfg, dest_dir=backup_root)
    validate_repo_backup_zip(backup_zip)
    marker_path = _write_last_backup_marker(cfg, backup_zip)
    print(f"OK: wrote before_confirm marker: {marker_path}")

    truth_md_before = None
    version_py_before = None

    # Read originals so we can rollback atomically on any failure
    truth_md_before = TRUTH_MD.read_text(encoding="utf-8", errors="replace")
    version_py_before = VERSION_PY.read_text(encoding="utf-8", errors="replace")

    # Compute artifact paths up-front so rollback can delete partial zips
    zip_root = REPO_ROOT / cfg.zip_root
    full_zip = zip_root / f"{project}_TRUTH_V{new_ver}_FULL.zip"
    slim_zip = zip_root / f"{project}_TRUTH_V{new_ver}_SLIM.zip"

    try:
        # Append truth then bump version (keeps TRUTH.md as primary log)
        append_truth_md_verbatim(project, new_ver, statement_text)
        write_truth_version(new_ver)
        # Update repo map BEFORE ai_index so indexing can include it
        from tools.update_repo_map import main as update_repo_map_main
        update_repo_map_main([])

        # Build ai index AFTER version bump, then verify contracts
        build_ai_index()
        verify_ai_index_main([])

        make_zip(full_zip, cfg, slim=False, project=project)
        make_zip(slim_zip, cfg, slim=True, project=project)

        # Validate truth zip structure (must be nested under <project>/)
        from tools.validate_truth_zip import validate_truth_zip
        validate_truth_zip(full_zip)
        validate_truth_zip(slim_zip)

        print("PHASE 2/2: Post-artifact verification")
        verify_truth.main(["--phase", "post"])

        # Delete the draft only after a fully successful confirm
        try:
            draft_path.unlink()
        except FileNotFoundError:
            pass

        return new_ver, full_zip, slim_zip

    except Exception as e:
        # Atomic rollback: restore authoritative files and delete any partial artifacts.
        # Rollback must be crash-proof and must not reference undefined symbols.
        summary: list[str] = []
        rollback_failed: list[str] = []

        def _rb_ok(msg: str) -> None:
            summary.append(f"OK: {msg}")

        def _rb_fail(msg: str) -> None:
            rollback_failed.append(f"FAIL: {msg}")

        # Restore authoritative files (best effort, but report results deterministically)
        try:
            if truth_md_before is not None:
                TRUTH_MD.write_text(truth_md_before, encoding="utf-8")
                _rb_ok("restored TRUTH.md")
            else:
                _rb_ok("TRUTH.md restore skipped (no snapshot)")
        except Exception as ex:
            _rb_fail(f"restore TRUTH.md: {ex!r}")

        try:
            if version_py_before is not None:
                VERSION_PY.write_text(version_py_before, encoding="utf-8")
                _rb_ok("restored app/version.py")
            else:
                _rb_ok("app/version.py restore skipped (no snapshot)")
        except Exception as ex:
            _rb_fail(f"restore app/version.py: {ex!r}")

        # Delete any partially created artifacts
        for z in (full_zip, slim_zip):
            try:
                if z is not None and isinstance(z, Path) and z.exists():
                    z.unlink()
                    _rb_ok(f"deleted partial artifact: {z.name}")
            except Exception as ex:
                _rb_fail(f"delete partial artifact {z}: {ex!r}")

        # We do NOT attempt to rollback external backups (they are append-only).
        print("ROLLBACK SUMMARY:", file=sys.stderr)
        for line in summary:
            print("  " + line, file=sys.stderr)
        for line in rollback_failed:
            print("  " + line, file=sys.stderr)

        if rollback_failed:
            raise RuntimeError(
                "ROLLBACK HARD-FAIL (rollback itself encountered errors). "
                f"original_error={e!r} ; rollback_errors={rollback_failed}"
            ) from e

        print(f"ROLLBACK COMPLETE: {e}", file=sys.stderr)
        raise

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

    # Backup key files before modifying anything (so we can go back without Git)
    # Create a rollback snapshot BEFORE mutation (backups stored outside repo by default)
    backup_root = _backup_root_external(project)
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TRUTH_MD, backup_root / "TRUTH.md")
    shutil.copy2(VERSION_PY, backup_root / "version.py")

    # Create a faithful repo snapshot backup (nested zip + manifest)
    from tools.repo_backup import build_repo_backup_zip, validate_repo_backup_zip
    backup_zip = build_repo_backup_zip(project=project, cfg=cfg, dest_dir=backup_root)
    validate_repo_backup_zip(backup_zip)
    marker_path = _write_last_backup_marker(cfg, backup_zip)
    print(f"OK: wrote before_confirm marker: {marker_path}")

    # Append truth then bump version (keeps TRUTH.md as primary log)
    append_truth_md_verbatim(project, new_ver, statement_text)
    write_truth_version(new_ver)

    # Update repo map BEFORE ai_index so indexing can include it
    try:
        from tools.update_repo_map import main as update_repo_map_main
        update_repo_map_main([])
    except Exception as e:
        raise RuntimeError(f"update_repo_map failed: {e}")

    # Build ai index AFTER version bump, then verify contracts
    build_ai_index()
    verify_ai_index_main([])

    zip_root = REPO_ROOT / cfg.zip_root
    full_zip = zip_root / f"{project}_TRUTH_V{new_ver}_FULL.zip"
    slim_zip = zip_root / f"{project}_TRUTH_V{new_ver}_SLIM.zip"

    make_zip(full_zip, cfg, slim=False, project=project)
    make_zip(slim_zip, cfg, slim=True, project=project)

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

    ap_set_type = sub.add_parser("set-type", help="set/clear the optional type tag [CONFIRM|DREAM|DEBUG] on an existing TRUTH header")
    ap_set_type.add_argument("--ver", required=True, help="version number (e.g. 3) or 'latest'")
    ap_set_type.add_argument("--type", default="CONFIRM", help="CONFIRM|DREAM|DEBUG|NONE (default: CONFIRM)")

    sub.add_parser("confirm-draft", help="confirm pending draft for next TRUTH (bumps version + zips)")

    args = ap.parse_args(argv)

    project, cur = read_project_and_truth_version()
    if args.cmd == "status":
        cfg = TruthConfig.load(CONFIG_JSON)
        pending = find_pending_draft(project, cfg)
        md_proj, md_ver, md_tag = read_truth_md_latest()
        payload = {
            "project": project,
            "confirmed": cur,
            "next": cur + 1,
            "draft_pending": None,
            "latest_header_type": md_tag,
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

    if args.cmd == "set-type":
        ver_arg = str(args.ver).strip().lower()
        if ver_arg == "latest":
            _, v_latest, _ = read_truth_md_latest()
            target_ver = v_latest
        else:
            target_ver = int(ver_arg)

        t = str(args.type).strip().upper()
        if t in ("NONE", "", "NULL"):
            tag: str | None = None
        elif t in ("CONFIRM", "DREAM", "DEBUG"):
            tag = t
        else:
            raise RuntimeError("--type must be CONFIRM, DREAM, DEBUG, or NONE")

        set_truth_type_tag(target_ver, tag)
        print(f"OK: set TRUTH_V{target_ver} header type to {tag or 'NONE'}")
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