from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple
from zipfile import ZipFile

from tools.verify_ai_index import main as verify_ai_index_main
from tools.truth_config import Config

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_PY = REPO_ROOT / "app" / "version.py"
TRUTH_MD = REPO_ROOT / "TRUTH.md"
CONFIG_JSON = REPO_ROOT / "tools" / "truth_config.json"


TEXT_EXTS = {
    ".py",
    ".ps1",
    ".txt",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
}


def fail(msg: str) -> None:
    print(f"VERIFY FAIL: {msg}")
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"VERIFY OK: {msg}")


def find_truth_version_assignments() -> List[Path]:
    """Return paths that contain a TRUTH_VERSION integer assignment.

    In phased truth mode, TRUTH_VERSION has a single authority: app/version.py.
    We intentionally do NOT scan the repo, to prevent generated folders (backups, artifacts)
    from poisoning the authority check.
    """
    pat = re.compile(r"^\s*TRUTH_VERSION\s*=\s*\d+\s*$", re.MULTILINE)
    p = VERSION_PY
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf-8", errors="replace")
    return [p] if pat.search(txt) else []
def find_project_name_assignments() -> List[Tuple[Path, int, str]]:
    """Return list of (path, lineno, line) where PROJECT_NAME is assigned.

    PROJECT_NAME authority is app/version.py only. Do not scan the repo.
    """
    pat = re.compile(r'^\s*PROJECT_NAME\s*=\s*".*?"\s*$')
    out: List[Tuple[Path, int, str]] = []
    p = VERSION_PY
    if not p.exists():
        return out
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return out
    for idx, ln in enumerate(lines, start=1):
        if pat.match(ln):
            out.append((p, idx, ln))
    return out
def verify_single_project_name_authority() -> None:
    assigns = find_project_name_assignments()
    allowed = REPO_ROOT / "app" / "version.py"

    # Must be exactly one, and it must be in app/version.py
    if len(assigns) != 1:
        details = []
        for p, idx, ln in assigns:
            rel = p.relative_to(REPO_ROOT)
            details.append(f"{rel} L{idx}: {ln.strip()}")
        fail("PROJECT_NAME authority violation (expected exactly 1 assignment in app/version.py): " + "; ".join(details) if details else "PROJECT_NAME assignment not found")
    p, idx, ln = assigns[0]
    if p.resolve() != allowed.resolve():
        rel = p.relative_to(REPO_ROOT)
        fail(f"PROJECT_NAME authority violation: found in {rel} L{idx} (must be app/version.py)")
    ok("single PROJECT_NAME authority verified (app/version.py)")


def verify_single_truth_version_authority() -> None:
    hits = find_truth_version_assignments()
    expected = VERSION_PY.resolve()
    if len(hits) != 1 or hits[0].resolve() != expected:
        rels = [str(p.relative_to(REPO_ROOT)) for p in hits]
        fail(
            "TRUTH_VERSION authority violation: expected exactly one integer assignment in app/version.py; "
            f"found {len(hits)} in: {rels}"
        )
    ok("single TRUTH_VERSION authority verified (app/version.py)")


def verify_main_imports_version() -> None:
    main_py = REPO_ROOT / "app" / "main.py"
    if not main_py.exists():
        fail("missing app/main.py")
    txt = main_py.read_text(encoding="utf-8", errors="replace")

    if re.search(r"^\s*TRUTH_VERSION\s*=\s*\d+\s*$", txt, flags=re.MULTILINE):
        fail("app/main.py must not define TRUTH_VERSION directly (must import from app/version.py)")

    if not re.search(r"^\s*from\s+app\.version\s+import\s+.*\bTRUTH_VERSION\b", txt, flags=re.MULTILINE):
        fail("app/main.py must import TRUTH_VERSION from app.version")

    ok("app/main.py imports TRUTH_VERSION from app.version")


def read_version_py() -> Tuple[str, int]:
    if not VERSION_PY.exists():
        fail(f"missing {VERSION_PY}")
    txt = VERSION_PY.read_text(encoding="utf-8", errors="replace")

    m1 = re.search(r'PROJECT_NAME\s*=\s*"(.*?)"', txt)
    if not m1:
        fail("PROJECT_NAME not found in app/version.py")
    project = m1.group(1)

    m2 = re.search(r"TRUTH_VERSION\s*=\s*(\d+)", txt)
    if not m2:
        fail("TRUTH_VERSION not found in app/version.py")
    ver = int(m2.group(1))

    return project, ver


@dataclass
class TruthEntry:
    project: str
    version: int
    start_line: int


# Allow optional D type tag suffix: [CONFIRM|DREAM|DEBUG]
TRUTH_HEADER_RE = re.compile(r"^TRUTH - (.+?) \(TRUTH_V(\d+)\)\s*(?:\[(CONFIRM|DREAM|DEBUG)\])?\s*$")


def parse_truth_md() -> Tuple[str, List[TruthEntry]]:
    if not TRUTH_MD.exists():
        fail(f"missing {TRUTH_MD}")

    lines = TRUTH_MD.read_text(encoding="utf-8", errors="replace").splitlines()

    entries: List[TruthEntry] = []
    for i, ln in enumerate(lines, start=1):
        m = TRUTH_HEADER_RE.match(ln.strip())
        if m:
            entries.append(TruthEntry(project=m.group(1), version=int(m.group(2)), start_line=i))

    if not entries:
        fail("TRUTH.md has no Truth entries (no 'TRUTH - <project> (TRUTH_V#)' headers found)")

    project = entries[0].project
    for e in entries:
        if e.project != project:
            fail(f"TRUTH.md project name mismatch at line {e.start_line}: {e.project} != {project}")

    return project, entries



SECTION_HEADERS_ALLOWED = {"LOCKED", "LOCKED PRE", "LOCKED POST", "NOTES", "END"}

def _iter_truth_entry_blocks(lines: List[str], entry: TruthEntry, next_start_line: int | None) -> List[Tuple[int, str]]:
    """Return list of (lineno, line_stripped) for lines in this entry, excluding the header itself."""
    start_idx = entry.start_line  # 1-based; header line itself at start_line
    end_line = (next_start_line - 1) if next_start_line else len(lines)
    out: List[Tuple[int, str]] = []
    for lineno in range(start_idx + 1, end_line + 1):
        out.append((lineno, lines[lineno - 1].rstrip("\n")))
    return out


def verify_truth_md_format(phases_required: bool) -> None:
    """Validate TRUTH.md entry structure for legacy or phased formats.

    Legacy: entry contains a single 'LOCKED' section and ends with 'END'.
    Phased: entry contains 'LOCKED PRE' then 'LOCKED POST' (both required), optional 'NOTES', ends with 'END'.
    If phases_required is True, legacy 'LOCKED' is forbidden.
    """
    raw_lines = TRUTH_MD.read_text(encoding="utf-8", errors="replace").splitlines()
    _project, entries = parse_truth_md()

    for idx, entry in enumerate(entries):
        next_start = entries[idx + 1].start_line if idx + 1 < len(entries) else None
        block = _iter_truth_entry_blocks(raw_lines, entry, next_start)

        # Find section headers inside this entry (line stripped, uppercase-ish)
        headers: List[Tuple[int, str]] = []
        for lineno, line in block:
            s = line.strip()
            if not s:
                continue
            # Allow separator lines of '='
            if set(s) <= {"="}:
                continue
            # We only care about exact section header lines
            if s in ("LOCKED", "LOCKED PRE", "LOCKED POST", "NOTES", "END", "PHASE PRE", "PHASE POST"):
                headers.append((lineno, s))

        # Explicitly forbid old PHASE headers (reserved)
        for lineno, h in headers:
            if h in ("PHASE PRE", "PHASE POST"):
                fail(f"TRUTH.md unsupported legacy phase header at line {lineno}: {h} (use LOCKED PRE/LOCKED POST)")

        # Must have END
        end_lines = [lineno for lineno, h in headers if h == "END"]
        if not end_lines:
            fail(f"TRUTH.md entry missing END terminator (TRUTH_V{entry.version})")
        if len(end_lines) > 1:
            fail(f"TRUTH.md entry has multiple END terminators (TRUTH_V{entry.version})")

        has_locked_pre = any(h == "LOCKED PRE" for _, h in headers)
        has_locked_post = any(h == "LOCKED POST" for _, h in headers)
        has_locked_legacy = any(h == "LOCKED" for _, h in headers)

        if has_locked_pre or has_locked_post:
            # Phased entry: require both, forbid legacy LOCKED
            if has_locked_legacy:
                ln = next(lineno for lineno, h in headers if h == "LOCKED")
                fail(f"TRUTH.md phased entry contains legacy LOCKED at line {ln} (TRUTH_V{entry.version})")
            if not has_locked_pre:
                fail(f"TRUTH.md phased entry missing LOCKED PRE (TRUTH_V{entry.version})")
            if not has_locked_post:
                fail(f"TRUTH.md phased entry missing LOCKED POST (TRUTH_V{entry.version})")

            # Ordering: LOCKED PRE < LOCKED POST < (NOTES?) < END
            pos = {h: lineno for lineno, h in headers if h in ("LOCKED PRE", "LOCKED POST", "NOTES", "END")}
            if pos["LOCKED PRE"] > pos["LOCKED POST"]:
                fail(f"TRUTH.md phased entry ordering invalid: LOCKED PRE after LOCKED POST (TRUTH_V{entry.version})")
            if pos["LOCKED POST"] > pos["END"]:
                fail(f"TRUTH.md phased entry ordering invalid: LOCKED POST after END (TRUTH_V{entry.version})")
            if "NOTES" in pos and pos["NOTES"] > pos["END"]:
                fail(f"TRUTH.md phased entry ordering invalid: NOTES after END (TRUTH_V{entry.version})")
        else:
            # Legacy entry
            if phases_required:
                fail(f"TRUTH.md legacy LOCKED entries are forbidden (phases required). First offending entry: TRUTH_V{entry.version}")
            if not has_locked_legacy:
                fail(f"TRUTH.md entry missing LOCKED section header (TRUTH_V{entry.version})")
            # Legacy ordering: LOCKED must appear before END
            llock = next(lineno for lineno, h in headers if h == "LOCKED")
            lend = end_lines[0]
            if llock > lend:
                fail(f"TRUTH.md legacy entry ordering invalid: LOCKED after END (TRUTH_V{entry.version})")

    ok("TRUTH.md format verified (legacy/phased)" + (" [phases required]" if phases_required else ""))

def verify_truth_sequence(entries: List[TruthEntry]) -> None:
    versions = [e.version for e in entries]
    if versions[0] != 1:
        fail(f"TRUTH.md first version must be 1 (found {versions[0]})")

    for a, b in zip(versions, versions[1:]):
        if b != a + 1:
            fail(f"TRUTH.md version sequence broken: {a} -> {b} (expected {a+1})")

    ok(f"TRUTH.md versions contiguous: 1..{versions[-1]}")


def verify_version_matches_latest(project_py: str, ver_py: int, project_md: str, latest_ver: int) -> None:
    if project_py != project_md:
        fail(f"PROJECT_NAME mismatch: app/version.py='{project_py}' vs TRUTH.md='{project_md}'")
    if ver_py != latest_ver:
        fail(f"TRUTH_VERSION mismatch: app/version.py={ver_py} vs TRUTH.md latest={latest_ver}")
    ok("app/version.py matches TRUTH.md latest entry")


def verify_config_present() -> None:
    # Single authoritative config is tools/truth_config.json
    if not CONFIG_JSON.exists():
        fail("missing tools/truth_config.json")
    ok("tools/truth_config.json present")

    # Enforce single config authority: root truth_config.json must not exist.
    legacy = REPO_ROOT / "truth_config.json"
    if legacy.exists():
        fail("legacy duplicate config present at truth_config.json (authoritative is tools/truth_config.json)")


def _iter_text_files() -> Iterable[Path]:
    # Scan repo "text" files that should never contain truncation markers.
    # This MUST use the canonical enumerator (repo_walk) so filtering is single-source.
    cfg = load_config()

    # Keep this conservative: only scan common text-like source files.
    exclude_roots = {
        "_truth",
        "_truth_backups",
        "_truth_drafts",
        "_ai_index",
        "_outputs",
        "_legacy_root",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
    }

    try:
        from tools.repo_walk import list_repo_files
        rels = list_repo_files(cfg, slim=False, allow_top_level=set())
        for rel in rels:
            rp = Path(rel)
            if rp.parts and rp.parts[0] in exclude_roots:
                continue
            if rp.suffix.lower() not in TEXT_EXTS:
                continue
            p = (REPO_ROOT / rp)
            if p.is_file():
                yield p
    except Exception:
        # Fallback: should be rare, but never crash. Keep same exclusions.
        for p in REPO_ROOT.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(REPO_ROOT)
            if rel.parts and rel.parts[0] in exclude_roots:
                continue
            if p.suffix.lower() not in TEXT_EXTS:
                continue
            yield p

def verify_no_truncation_lines() -> None:
    # Standalone ellipsis line is the safe, low false-positive detection.
    pat = re.compile(r"^\s*\.\.\.\s*$")
    for p in _iter_text_files():
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, ln in enumerate(lines, start=1):
            if pat.match(ln):
                rel = p.relative_to(REPO_ROOT)
                fail(f"truncation/ellipsis line found: {rel} L{idx}: {ln!r}")
    ok("no standalone truncation ellipsis lines")



def verify_forbidden_marker_substrings() -> None:
    cfg = load_config()
    markers = list(getattr(cfg, "forbidden_marker_substrings", []) or [])

    # If config does not specify markers, fall back to a strict, unambiguous default set.
    if not markers:
        markers = [
            "<<<TRUNCATED>>>",
            "<<<TRUNCATION>>>",
            "<<TRUNCATED>>",
            "[TRUNCATED]",
            "…TRUNCATED…",
        ]

    offenders = []
    for p in _iter_text_files():
        # Never scan the authoritative config file or this verifier; otherwise the scan
        # can self-trigger due to policy text.
        if p.resolve() == CONFIG_JSON.resolve():
            continue
        if p.resolve() == Path(__file__).resolve():
            continue
        try:
            s = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            s = p.read_text(encoding="utf-8", errors="replace")
        for m in markers:
            if m and (m in s):
                rel = p.relative_to(REPO_ROOT)
                # report line if possible
                try:
                    for i, line in enumerate(s.splitlines(), start=1):
                        if m in line:
                            offenders.append(f"{rel}:{i}:{m}")
                            break
                    else:
                        offenders.append(f"{rel}:{m}")
                except Exception:
                    offenders.append(f"{rel}:{m}")
                if len(offenders) >= 5:
                    break
        if len(offenders) >= 5:
            break

    if offenders:
        fail("forbidden truncation marker substrings found (e.g. " + ", ".join(offenders[:5]) + ")")
    ok("no forbidden truncation marker substrings")


def verify_truth_zip_naming(project: str, ver: int) -> Tuple[Path, Path]:
    truth_dir = REPO_ROOT / "_truth"
    if not truth_dir.exists():
        fail("_truth folder missing (expected artifacts in post phase)")

    full = truth_dir / f"{project}_TRUTH_V{ver}_FULL.zip"
    slim = truth_dir / f"{project}_TRUTH_V{ver}_SLIM.zip"

    if not full.exists():
        fail(f"missing FULL artifact: {full}")
    if not slim.exists():
        fail(f"missing SLIM artifact: {slim}")

    ok("Truth artifacts present (FULL + SLIM)")
    return full, slim


def _load_truth_config() -> dict:
    import json

    return json.loads(CONFIG_JSON.read_text(encoding="utf-8"))



def load_config() -> Config:
    return Config.load(CONFIG_JSON)

def verify_slim_contents(slim_zip: Path) -> None:
    cfg = _load_truth_config()

    # Drive forbidden sets by config only.
    forbidden_folders = set(getattr(cfg, "exclude_common_folders", []) or [])
    forbidden_folders |= set(getattr(cfg, "slim_exclude_folders", []) or [])
    forbidden_folders |= set(getattr(cfg, "slim_exclude_extra_folders", []) or [])
    forbidden_exts = {str(x).lower() for x in (getattr(cfg, "slim_exclude_ext", []) or [])}

    offenders: List[str] = []
    with ZipFile(slim_zip, "r") as z:
        for name in z.namelist():
            # Normalize
            norm = name.replace("\\", "/")
            parts = [p for p in norm.split("/") if p]
            if not parts:
                continue

            # Folder-based checks (anywhere in path)
            for token in parts[:-1]:
                if token in forbidden_folders:
                    offenders.append(f"{norm} (folder '{token}')")
                    break
            else:
                # Extension-based check
                suffix = Path(parts[-1]).suffix.lower()
                if suffix and suffix in forbidden_exts:
                    offenders.append(f"{norm} (ext '{suffix}')")

    if offenders:
        sample = "\n".join(offenders[:25])
        more = "" if len(offenders) <= 25 else f"\n... and {len(offenders)-25} more"
        fail(f"SLIM zip contains forbidden content:\n{sample}{more}")

    ok("SLIM zip contents verified against config")




def verify_last_before_confirm_backup_if_present() -> None:
    """Validate the most recent before_confirm backup zip if a marker exists.

    confirm-draft writes: _truth/last_before_confirm_backup.json
    containing { "backup_zip": "<absolute path>", ... }.

    If marker is absent: skip (OK).
    If marker is present but invalid: FAIL.
    """
    cfg = load_config()
    marker = REPO_ROOT / cfg.zip_root / "last_before_confirm_backup.json"
    if not marker.exists():
        ok("No before_confirm backup marker present")
        return

    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"backup marker is not valid JSON: {marker} ({e})")

    backup_zip = str(payload.get("backup_zip") or "").strip()
    if not backup_zip:
        fail(f"backup marker missing 'backup_zip': {marker}")

    zpath = Path(backup_zip)
    from tools.validate_backup_zip import validate_backup_zip
    try:
        validate_backup_zip(zpath)
    except Exception as e:
        fail(f"backup zip validation failed: {zpath} ({e})")

    ok(f"before_confirm backup validated: {zpath}")


def main(argv: List[str] | None = None) -> int:
    """Verify repo truth invariants.

    This verifier is phase-aware:
    - --phase pre: verify everything except artifact existence/contents
    - --phase post: verify everything including artifact existence and SLIM contents

    Legacy flag --skip-artifacts is accepted for backward compatibility and maps to --phase pre.
    """

    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["pre", "post"], default="post")
    ap.add_argument("--skip-artifacts", action="store_true", help="DEPRECATED: use --phase pre")
    ns = ap.parse_args(argv or [])

    phase = "pre" if ns.skip_artifacts else ns.phase

    project_py, ver_py = read_version_py()
    verify_single_truth_version_authority()
    verify_main_imports_version()
    project_md, entries = parse_truth_md()
    verify_truth_sequence(entries)

    latest = entries[-1].version
    verify_version_matches_latest(project_py, ver_py, project_md, latest)
    verify_config_present()
    cfg = load_config()
    phases_required = bool(getattr(cfg, "truth_phases_required", False))
    verify_truth_md_format(phases_required)
    verify_single_project_name_authority()

    # Truncation/ellipsis guard (runs in both phases)
    verify_no_truncation_lines()
    verify_forbidden_marker_substrings()

    # Verify ai index contract/integrity
    verify_ai_index_main()
    ok("_ai_index contract/integrity verified")

    if phase == "post":
        _full, slim = verify_truth_zip_naming(project_py, ver_py)

        from tools.validate_truth_zip import validate_truth_zip
        validate_truth_zip(_full)
        validate_truth_zip(slim)
        verify_slim_contents(slim)

        verify_last_before_confirm_backup_if_present()

    ok("Truth verification complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
