==================================================
TRUTH - project_template (TRUTH_V1)
==================================================

LOCKED PRE
- D epoch reset: TRUTH.md is reseeded under phased format
- Prior truths are archived to TRUTH_LEGACY.md and are not enforced
- truth_phases_required is enabled (LOCKED PRE/LOCKED POST required)
- TRUTH_VERSION is reset to 1 in app/version.py

LOCKED POST
- TRUTH_LEGACY.md exists and contains the pre-D truth history
- TRUTH.md is now the only authoritative truth log
- Verification enforces phased truth format for all future entries

END

TRUTH - project_template (TRUTH_V2) [CONFIRM]
=============================================

LOCKED PRE
- D-epoch is active; TRUTH.md uses phased truths with explicit type tags
- Truth header MAY include exactly one type tag: [CONFIRM|DREAM|DEBUG]
- Header parsing MUST accept optional type tags without breaking contiguity or validation
- Truth minting MUST accept and preserve the declared type verbatim
- Legacy truths are quarantined and excluded from all validation and contiguity logic

LOCKED POST
- tools/truth_manager accepts headers of the form:
  TRUTH - <project> (TRUTH_V#) [TYPE]
- tools/verify_truth validates presence and correctness of TYPE when phases are required
- Truth minting for V2 succeeds without header-regex failure
- FULL and SLIM artifacts are generated only after successful header + phase validation

END

TRUTH - project_template (TRUTH_V3) [CONFIRM]
=============================================

LOCKED PRE
- All truth header parsers MUST accept optional type tags: [CONFIRM|DREAM|DEBUG]
- tools/ai_index.py MUST parse TRUTH.md latest TRUTH_V# correctly when type tags are present
- AI index version consistency checks MUST compare against the true latest TRUTH_V# (not misparsed legacy headers)
- Minting MUST fail fast if ai_index cannot determine the correct latest truth version

LOCKED POST
- tools/ai_index.py recognizes headers of the form:
  TRUTH - <project> (TRUTH_V#) [TYPE]
- ai_index precheck no longer falsely reports TRUTH.md latest as V1 when V2/V3 headers include [TYPE]
- Minting proceeds without AI index version mismatch caused by header parsing

END

TRUTH - project_template (TRUTH_V4)
==================================================

LOCKED PRE
- Implement Stoplight Phase GUI with phases: Draft (🔴), Editing (🟡), Debug (🟠), Confirm (🟢)
- GUI displays TRUTH_V#, draft path, last verification summary
- Buttons: Refresh Phase, Open Draft, Confirm Draft, Append Debug Truths, Revert Draft/Repo, Generate Debug ZIP, Doctor PRE/POST, Open Folders
- Logging: live subprocess output
- Draft template auto-insert: header, LOCKED PRE/POST, END
- Read-only safety: GUI does not modify TRUTH.md directly

LOCKED POST
- Draft stored at _truth_drafts/<project>_TRUTH_V{next}_DRAFT.txt
- Append debug truths safely in Debug phase
- Revert restores draft text or full repo snapshot
- Debug ZIP includes full repo + draft + _ai_index/ for sharing
- Pre-flight / phase rules disable invalid actions
- Preserve original draft copy

END

TRUTH - project_template (TRUTH_V5)
==================================================

LOCKED PRE
- Stoplight Phase GUI fully interactive, thread-safe Confirm Draft
- FULL zip ~50 KB (explicit files only)
- Debug ZIP ~14 KB
- Phase defaults to Debug (🟠) if any appended truth exists
- Logging live, Draft backup preserved
- Missing 'os' import fixed for Confirm Draft

LOCKED POST
- Draft stored at _truth_drafts/<project>_TRUTH_V{next}_DRAFT.txt
- Append debug truths safely during Debug phase
- Revert restores draft or full repo snapshot
- Confirm Draft fully locks TRUTH_V5
- GUI fully interactive, no auto-clicking
END

TRUTH - project_template (TRUTH_V6)
==================================================

LOCKED PRE
- Confirm Draft must automatically refresh repo metadata that other tools depend on (no manual steps)
- “Update Map” is authoritative and must be regenerated on every Confirm Draft:
  - project_repo_map.json (repo structure + key files + tool entrypoints + invariants)
- AI indexing must also regenerate on every Confirm Draft:
  - _ai_index/_file_map.json
  - _ai_index/python_index.json
  - _ai_index/entrypoints.json
- Confirm Draft must create local backups before mutating TRUTH.md/version:
  - _truth_backups/before_confirm_<timestamp>/TRUTH.md
  - _truth_backups/before_confirm_<timestamp>/version.py

LOCKED POST
- Confirm Draft pipeline order is standardized:
  1) pre-verify
  2) backup TRUTH.md + version.py
  3) append truth + bump TRUTH_VERSION
  4) regenerate project_repo_map.json
  5) regenerate _ai_index outputs
  6) create FULL + SLIM zips
  7) post-verify
- Draft detection is version-aware (TRUTH_V(next)) and does not hardcode filenames.
END

TRUTH - project_template (TRUTH_V7) [CONFIRM]
==================================================

LOCKED PRE
- End recursive contamination of Truth tooling:
  - Introduce a central exclude fence used by all repo walks
  - TRUTH_VERSION authority checks must only read app/version.py (no repo-wide scans)
  - confirm-draft must be atomic: any failure triggers rollback (TRUTH.md + app/version.py) and preserves draft
- Prevent backups/drafts/artifacts from poisoning scans:
  - _truth_backups, _truth_drafts, _truth, _ai_index, __pycache__, *.pyc must be excluded consistently

LOCKED POST
- confirm-draft is safe to run repeatedly:
  - No half-confirmed states
  - On failure: restore TRUTH.md and app/version.py, keep draft, delete partial artifacts
- Authority scanners do not recurse:
  - Only app/version.py is used for TRUTH_VERSION and PROJECT_NAME authority
END

TRUTH - project_template (TRUTH_V8) [CONFIRM]

LOCKED PRE

- Artifact pipeline filtering must be centralized and deterministic:

  - A single exclude/allow policy (TruthConfig) is the only authority for *all* repo walks:

    - zip packaging (FULL/SLIM)
    - repo map generation (project_repo_map.json)
    - ai_index generation (_ai_index)
    - any verification that enumerates files
  - Generated/ephemeral roots must never poison scans:

    - Exclude (at minimum): _truth, _truth_backups, _truth_drafts, _ai_index, **pycache**, *.pyc
- Artifact outputs must still be includable intentionally:

  - Introduce an explicit allowlist for "artifact outputs to include" (e.g., project_repo_map.json and _ai_index.zip) even if their parent folders are excluded
  - No implicit inclusion of entire artifact folders

LOCKED POST

- confirm-draft rebuilds and includes map/index correctly and safely:

  - On confirm-draft, after TRUTH_VERSION bump:

    - Rebuild project_repo_map.json using the centralized filter policy
    - Rebuild ai_index using the centralized filter policy
    - Package FULL+SLIM using the same policy + slim extras
  - Post-verify asserts:

    - repo map + ai_index exist, are regenerated for the confirmed version, and contain no excluded-root paths
    - repeated confirm-draft runs do not drift (idempotent outputs given unchanged repo)
      END

TRUTH - project_template (TRUTH_V9)

LOCKED PRE

- Artifact zip contracts are explicit and enforced:

  - "Artifact zips" (Truth FULL/SLIM, Repo Backups) MUST be nested:

    - Exactly one top-level folder named `project_template/`
    - All contents are stored as `project_template/<repo-relative-path>`
    - No flattening is permitted; duplicate archive paths are forbidden
  - "Patch zips" (applied into an existing repo) MUST be repo-relative (not nested):

    - No `project_template/` root folder
    - Safe to `Expand-Archive ... .` from repo root
- Deterministic enumeration is single-source:

  - A single canonical enumerator/filter policy is the only authority for all repo walks:

    - repo map generation
    - ai_index generation
    - Truth FULL/SLIM packaging
    - backup packaging
    - any verification that enumerates repo files
  - Excludes/Includes are centralized (TruthConfig) and must be identical across tools
- Validation is first-class (no "silent success"):

  - Validators MUST print explicit "OK:" lines on success (no empty output on pass)
  - Validators MUST support `--json` for machine-readable diagnostics

LOCKED POST

- confirm-draft pipeline order and regeneration rules are deterministic:

  - On confirm-draft:

    1. Create and validate a "before_confirm" repo backup (artifact zip, nested)
    2. Regenerate `project_repo_map.json` using the canonical enumerator
    3. Regenerate `_ai_index` using the canonical enumerator
    4. Build Truth FULL/SLIM zips (artifact zips, nested)
    5. Validate Truth FULL/SLIM zips (structure + config contents)
    6. Post-verify (`verify_truth --phase post`)
  - repo map and ai_index MUST be regenerated on confirm-draft (not on pre-verify)
- Rollback integrity is non-negotiable:

  - confirm-draft rollback MUST never crash
  - If confirm-draft fails after any mutation, it MUST restore:

    - `TRUTH.md`
    - `app/version.py`
    - any partially written artifacts (delete or restore to last known-good)
  - Rollback MUST end in a verifiable state (pre/post as appropriate) or hard-fail with a clear error
- Doctor enforcement:

  - `python -m tools.doctor --phase post` MUST validate:

    - Truth FULL/SLIM zips (artifact contract + contents contract)
    - the latest "before_confirm" backup zip produced by confirm-draft in that run
      END

