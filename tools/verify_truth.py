from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple
from zipfile import ZipFile

from tools.verify_ai_index import main as verify_ai_index_main

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
    """Return paths that contain a TRUTH_VERSION integer assignment."""
    hits: List[Path] = []
    pat = re.compile(r"^\s*TRUTH_VERSION\s*=\s*\d+\s*$", re.MULTILINE)
    for p in REPO_ROOT.rglob("*.py"):
        if "_truth" in p.parts or "_ai_index" in p.parts or "__pycache__" in p.parts:
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        if pat.search(txt):
            hits.append(p)
    return hits



def find_project_name_assignments() -> List[Tuple[Path, int, str]]:
    """Return list of (path, lineno, line) where PROJECT_NAME is assigned."""
    pat = re.compile(r'^\s*PROJECT_NAME\s*=\s*".*?"\s*$')
    out: List[Tuple[Path, int, str]] = []
    for p in _iter_text_files():
        if p.suffix.lower() != ".py":
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
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


TRUTH_HEADER_RE = re.compile(r"^TRUTH - (.+?) \(TRUTH_V(\d+)\)\s*$")


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
    # This scans the repo for "text" files that should never contain truncation markers.
    # Exclude generated/output directories.
    exclude_roots = {"_truth", "__pycache__", ".git", ".venv", "venv"}
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO_ROOT)
        if rel.parts and rel.parts[0] in exclude_roots:
            continue
        if "_ai_index" in rel.parts:
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
    markers = cfg.get("forbidden_marker_substrings") or []
    if not markers:
        ok("no forbidden marker substrings configured")
        return

    offenders = []
    for p in _iter_text_files():
        # Don't scan the authoritative config file itself; it is expected to
        # contain the marker strings as configuration values.
        if p.resolve() == CONFIG_JSON.resolve():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = p.read_text(encoding="utf-8", errors="replace")

        for marker in markers:
            if marker and marker in text:
                rel = p.relative_to(REPO_ROOT)
                offenders.append(f"{rel} (contains {marker!r})")
                break

    if offenders:
        fail("forbidden truncation markers found: " + "; ".join(offenders))
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



def load_config() -> dict:
    """Backward-compatible config loader for verification helpers."""
    return _load_truth_config()

def verify_slim_contents(slim_zip: Path) -> None:
    cfg = _load_truth_config()

    # Drive forbidden sets by config only.
    forbidden_folders = set(cfg.get("exclude_common_folders", []))
    forbidden_folders |= set(cfg.get("slim_exclude_folders", []))
    forbidden_folders |= set(cfg.get("slim_exclude_extra_folders", []))
    forbidden_exts = {str(x).lower() for x in cfg.get("slim_exclude_ext", [])}

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
    verify_single_project_name_authority()

    # Truncation/ellipsis guard (runs in both phases)
    verify_no_truncation_lines()
    verify_forbidden_marker_substrings()

    # Verify ai index contract/integrity
    verify_ai_index_main()
    ok("_ai_index contract/integrity verified")

    if phase == "post":
        _full, slim = verify_truth_zip_naming(project_py, ver_py)
        verify_slim_contents(slim)

    ok("Truth verification complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
