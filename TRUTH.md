==================================================
TRUTH - project_template (TRUTH_V1)
==================================================

LOCKED
- Version: 1

STATEMENT
- Initial project template skeleton.

NOTES
- Mint new Truth via tools\mint_truth.ps1
==================================================
TRUTH - project_template (TRUTH_V2)
==================================================

LOCKED
- Version: 2
- Timestamp: 2026-01-02 09:41:16

STATEMENT
- STATEMENT
- Establishes project_template as a minimal, reusable project skeleton
- Defines PROJECT_NAME as a single replacement token applied at project creation
- Defines TRUTH_VERSION as an integer stored authoritatively in app/version.py
- Introduces a deterministic, user-driven Truth minting process
- Requires explicit user confirmation to mint each new Truth version
- Captures multi-line Truth statements verbatim, without interpretation or inference
- Enforces append-only Truth history in TRUTH.md
- Produces reproducible Truth zips with explicit exclusions
- Prohibits timestamps or external state from influencing version logic
- Establishes this repository as immutable except via the Truth minting process

==================================================
TRUTH - project_template (TRUTH_V3)
==================================================

LOCKED
- Version: 3
- Timestamp: 2026-01-02 09:58:20

STATEMENT
- Zip creation validated using .NET ZipArchive (no Compress-Archive)
- Truth zips are written to a temp file then atomically renamed to avoid file locks
- _truth is excluded from zip inputs

==================================================
TRUTH - project_template (TRUTH_V4)
==================================================

LOCKED
- Version: 4
- Timestamp: 2026-01-02 11:14:08

STATEMENT
- Dual Truth artifacts per mint: FULL and SLIM
- FULL zip includes all assets (images/videos/binaries) except common build/env/caches
- SLIM zip excludes media/large extensions plus user-configurable exception folders
- Exception folders are configurable and persisted (template-level config)
- Add a small GUI to show current TRUTH_VERSION, mint next Truth (prompt for text), and manage exception folders
- Truth zips written to _truth with deterministic naming and atomic write semantics


==================================================
TRUTH - project_template (TRUTH_V5)
==================================================

LOCKED
- Version: 5
- Timestamp: 2026-01-02 11:20:25

STATEMENT
- Implement dual Truth zips per mint: FULL and SLIM
- FULL includes all assets except common build/env/caches
- SLIM excludes media extensions and user-configurable exception folders
- Exception folders persisted in tools/truth_config.json and editable via GUI
- Minting produces deterministic names and writes zips atomically


==================================================
TRUTH - project_template (TRUTH_V6)
==================================================

LOCKED
- Version: 6
- Timestamp: 2026-01-02 16:03:18

STATEMENT
- ﻿Introduce Truth-coupled AI indexing that generates a non-authoritative _ai_index folder (no ai zip artifacts)
- _ai_index contains _file_map.json, python_index.json, entrypoints.json, _ai_index_README.txt, and _ai_index_INDEX.txt
- Add semantic entrypoints index for “how to run / where to start” across app and tools
- Add richer Python code graph: import edges (module → module) and reverse “imported_by” mapping
- Add integrity/contract verification for _ai_index via tools/verify_ai_index.py and sha256 manifest checks
- Truth minting runs ai_index build + verify before producing FULL and SLIM Truth zips, ensuring the index is captured in the snapshot
- _ai_index is excluded from self-scanning during generation to avoid recursive indexing, but is included in Truth zips as generated output


==================================================
TRUTH - project_template (TRUTH_V7)
==================================================

LOCKED
- Version: 7
- Timestamp: 2026-01-02 16:09:22

STATEMENT
- ﻿Add template-owned bootstrap orientation files to guide AI and human readers
- Introduce _BOOTSTRAP.txt as the required first-read file defining authority, rules, and orientation order
- Introduce _CONTRACTS.txt to explicitly codify repository invariants and Truth system rules
- Bootstrap files are copied into all cloned projects and are not generated artifacts
- Bootstrap files are manually maintained and changes are governed via Truth minting
- No runtime behavior changes; this Truth establishes orientation and governance only


==================================================
TRUTH - project_template (TRUTH_V8)
==================================================

LOCKED
- Version: 8
- Timestamp: 2026-01-02 16:13:36

STATEMENT
- ﻿Document the Truth minting GUI as a supported interface in README.txt
- Explicitly describe how to launch tools.truth_gui and its supported functions
- Clarify that the GUI is a convenience layer and does not supersede Truth rules or invariants
- Affirm that PowerShell and Python minting logic remain authoritative if behavior diverges
- No changes to Truth semantics, versioning rules, or artifact generation behavior


==================================================
TRUTH - project_template (TRUTH_V9)
==================================================

LOCKED
- Version: 9
- Timestamp: 2026-01-02 16:18:18

STATEMENT
- ﻿Add tools/doctor.ps1 as a one-command preflight to validate repository health and invariants
- Doctor verifies required files exist, builds and verifies _ai_index, verifies Truth contracts, and smoke-runs python -m app.main
- Add tools/verify_truth.py to enforce Truth system contracts and detect mismatches early
- verify_truth enforces contiguous Truth version history in TRUTH.md and confirms TRUTH_VERSION and PROJECT_NAME match app/version.py
- verify_truth verifies truth_config.json presence, _ai_index integrity via verify_ai_index, and FULL/SLIM artifacts when _truth exists
- These additions are guardrails only and do not change minting semantics, versioning rules, or artifact generation behavior


==================================================
TRUTH - project_template (TRUTH_V10)
==================================================

LOCKED
- Version: 10
- Timestamp: 2026-01-11 05:46:47

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V10)
- LOCKED
- Version: 10
- STATEMENT
- Harmonize project_template with proven tooling and structure from qnmrcalc_app while keeping project_template minimal and reusable
- Template-owned contract hardening:
- Add an explicit “ASSISTANT RESPONSE CONTRACT” section to _CONTRACTS.txt that is non-optional and must be followed in all future work on this repo and any cloned projects
- Contract requires:
- Always mint a new Truth before any coding changes (unless explicitly instructed “inspect-only”)
- Deliver changes as zip artifacts plus PowerShell extract commands and a run command
- Include Truth entries in the exact repository Truth format (header + LOCKED + STATEMENT + NOTES as applicable)
- No partial code snippets for modified files; full-file output discipline when code is provided in-chat
- Template bootstrap hardening:
- Update _BOOTSTRAP.txt (and/or add _ASSISTANT_CONTRACT.txt) to orient an assistant receiving any Truth zip:
- where TRUTH_VERSION is authoritative
- how to run verify_truth / verify_ai_index
- where to mint Truth
- expected deliverable format (zip + PS commands)
- Tooling harmonization (template-owned):
- Bring forward the minimum required subset of qnmrcalc_app’s template-usable tools and patterns (truth manager/gui, verify scripts, ai_index generation and integrity checks, deterministic outputs)
- Preserve the existing FULL/SLIM Truth artifact behavior and config-driven exclusions
- No behavioral regression:
- new_project must continue to create a clean project at C:\Users\stoyg\Documents\Programming<NewName>
- cloned projects start at TRUTH_V1 and do not inherit template _truth history
- NOTES
- This Truth is explicitly about standardizing project_template contracts + bootstrap orientation + tool harmonization.
- Subsequent Truths may extend AI index richness (code graph, semantic entrypoints, contract verification) if not completed here.


==================================================
TRUTH - project_template (TRUTH_V11)
==================================================

LOCKED
- Version: 11
- Timestamp: 2026-01-11 05:53:54

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V11)
- ==================================================
- LOCKED
- STATEMENT
- This Truth is additive to all prior Truths, including TRUTH_V10, which remains fully authoritative and in force.
- TRUTH.md is strictly append-only. No prior Truth may be edited, reordered, summarized, or removed unless explicitly revoked in a future Truth.
- PROCESS / DISCIPLINE (NON-NEGOTIABLE)
- Full-file inspection rule:
  - Whenever files are opened for inspection, reasoning, or implementation planning, the FULL file contents must be opened and examined.
  - Truncated views, ellipses, summaries, partial snippets, or inferred structure are explicitly forbidden.
  - If a full file is not available, work must STOP and this must be stated explicitly.
- Truth-first workflow:
  - A new TRUTH must be minted and accepted BEFORE any coding, patching, or refactoring is performed.
  - No implementation work may proceed without an active Truth covering that scope.
- Response contract (binding):
  - When delivering code changes, responses MUST include, in this order:
- 1) Patch or FULL zip artifact
- 2) PowerShell commands to extract and run
- 3) Modified-files list
- 4) Brief acceptance checklist
  - No alternative response formats are permitted unless explicitly requested.
- Hallucination guardrail:
  - No claims of inspection, fixes, patches, or behavior changes may be made unless they are verified against FULL files.
  - If uncertainty exists, the correct action is to stop and request the required artifact.
- TEMPLATE OWNERSHIP / PORTABILITY
- project_template is the authoritative source of:
  - Truth minting process
  - Folder structure
  - Tooling conventions
  - Response and delivery expectations
- Any project created from this template inherits these rules unless a later project-specific Truth explicitly overrides them.
- ENFORCEMENT
- Violations of this Truth invalidate the response.
- The correct recovery from a violation is:
  - Stop
  - Acknowledge
  - Realign to the last locked Truth
  - Proceed only after confirmation


==================================================
TRUTH - project_template (TRUTH_V12)
==================================================

LOCKED
- Version: 12
- Timestamp: 2026-01-11 06:03:50

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V12)
- LOCKED
- Version: 12
- STATEMENT
- Template-owned orientation files are now authoritative inputs for all future work:
- README.txt (user-facing operations)
- _BOOTSTRAP.txt (zip-first workflow + execution commands)
- _CONTRACTS.txt (assistant response contract + enforcement rules)
- README.txt must explicitly document:
- Truth minting (CLI + GUI)
- FULL vs SLIM Truth artifacts
- AI index build/verify commands (no zip requirement)
- Expected output locations (_truth, _outputs, _ai_index)
- _BOOTSTRAP.txt must explicitly require:
- Always open and inspect FULL file contents (no truncated/ellipsis inspection)
- Zip-first workflow as the source of truth for analysis and patches
- Terse PowerShell commands for extract/apply/run
- _CONTRACTS.txt must explicitly require, and treat as non-optional:
- Mint a new Truth before any coding changes
- Deliverables include: patch zip + PowerShell extract/apply/run commands
- Full-file discipline: open FULL files before reasoning or edits
- No hallucinated patches or claims of inspection/testing
- This Truth is documentation + workflow enforcement only:
- no changes to versioning logic
- no changes to minting mechanics beyond documentation and contracts
- no changes to application code outside these orientation/contract files
- NOTES
- This Truth exists to prevent time loss due to truncated file inspection and non-compliant response formatting.


==================================================
TRUTH - project_template (TRUTH_V13)
==================================================

LOCKED
- Version: 13
- Timestamp: 2026-01-11 06:06:55

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V13)
- ====================================
- LOCKED
- * There MUST be exactly ONE authoritative TRUTH_VERSION source in the repo
- * `TRUTH_VERSION` MUST match the active TRUTH number (e.g., TRUTH_V13 => TRUTH_VERSION = 13)
- * Truth-mint tooling MUST fail fast if:
- * multiple `TRUTH_VERSION` definitions exist, or
- * the authoritative `TRUTH_VERSION` does not equal the new truth number
- * AI index generation MUST validate version consistency and MUST fail if invalid
- * Bootstrap guidance and contracts MUST explicitly define the authoritative version file path
- STATE
- * Remove/disable duplicate version authority (no root/app divergence)
- * All code/tools import/read `TRUTH_VERSION` from the single authoritative file only
- * Mint truth script updates the authoritative `TRUTH_VERSION` automatically as part of mint
- * `_ai_index` generation asserts:
- * exactly one `TRUTH_VERSION` definition exists
- * its value equals the current TRUTH number being minted/locked
- NOTES
- * Current violation observed: `version.py` (root) = 2 while `app/version.py` = 12
- * This truth exists to restore mechanical trust: version must be unambiguous, enforced, and indexed as valid


==================================================
TRUTH - project_template (TRUTH_V14)
==================================================

LOCKED
- Version: 14
- Timestamp: 2026-01-11 06:16:34

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V13)
- ====================================
- LOCKED
- * Minting a new TRUTH MUST require ZERO manual version edits
- * When the user answers “y” to mint, the repo MUST auto-harmonize to the new TRUTH number:
- * `app/version.py` MUST be updated to the new integer (e.g., TRUTH_V13 => TRUTH_VERSION = 13)
- * `app/main.py` MUST import/use that authoritative `TRUTH_VERSION` (no hardcoded/duplicated version values)
- * There MUST be exactly ONE authoritative `TRUTH_VERSION` definition in the repo
- * If a legacy duplicate exists (e.g., root `version.py`), minting MUST remove/disable it automatically
- * Minting MUST fail fast if, after harmonization:
- * more than one `TRUTH_VERSION` definition exists, or
- * the authoritative `TRUTH_VERSION` does not equal the new TRUTH number
- * AI index generation MUST validate version consistency and MUST fail if invalid
- STATE
- * Single source of truth: `app/version.py` defines `TRUTH_VERSION`
- * `app/main.py` imports `TRUTH_VERSION` from `app.version`
- * `tools/mint_truth.ps1` workflow (via tools) performs, in order:
- 1. determine next truth number
- 2. if user says “y”, auto-update authoritative version + remove duplicates
- 3. verify version + contract invariants
- 4. generate AI index
- 5. write/lock TRUTH entry and emit FULL/SLIM zips
- NOTES
- * Fixed prior violation: root `version.py` drifted (e.g., 2) while `app/version.py` was correct (e.g., 12)
- * This truth exists to restore mechanical trust: version is unambiguous, enforced, and automatically updated during mint


==================================================
TRUTH - project_template (TRUTH_V15)
==================================================

LOCKED
- Version: 15
- Timestamp: 2026-01-11 06:18:34

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V15)
- ====================================
- LOCKED
- * Minting MUST NOT verify artifacts that have not yet been created
- * Verification MUST be split into two explicit phases:
- * Pre-artifact verification (during mint)
- * Post-artifact verification (after zip creation)
- * Artifact existence checks (FULL/SLIM zips) MUST occur only after those artifacts are written
- * Minting MUST NOT fail due to missing artifacts that are expected to be produced later in the same mint operation
- STATE
- * Mint pipeline order is defined and enforced as:
- 1. determine next TRUTH number
- 2. user confirms mint (“y”)
- 3. auto-harmonize version (`app/version.py`, remove duplicates)
- 4. pre-artifact verification:
- * TRUTH.md syntax and contiguity
- * single TRUTH_VERSION authority
- * TRUTH_VERSION equals new TRUTH number
- * `app/main.py` imports `TRUTH_VERSION`
- * AI index internal integrity
- 5. generate FULL and SLIM artifacts
- 6. post-artifact verification:
- * FULL zip exists
- * SLIM zip exists
- * artifact naming matches TRUTH number
- * AI index included as required
- 7. finalize and lock TRUTH
- NOTES
- * Prior failure in V14 identified an ordering bug: artifact verification executed before artifact creation
- * This truth restores mechanical correctness to the mint pipeline by enforcing phase separation
- * No behavioral ambiguity remains: artifacts may only be verified after they exist


==================================================
TRUTH - project_template (TRUTH_V16)
==================================================

LOCKED
- Version: 16
- Timestamp: 2026-01-11 06:26:00

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V16)
- ====================================
- LOCKED
- * Minting MUST be mechanically correct and non-speculative
- * Verification MUST be phase-aware and context-correct
- * No verification step may assert the existence of artifacts that are produced later in the same mint operation
- * Versioning MUST remain ZERO-manual:
- * Answering “y” to mint MUST automatically harmonize all version state
- * No human edits to `version.py`, `main.py`, or artifacts are permitted
- STATE
- * Mint pipeline is strictly ordered and enforced:
- 1. detect current TRUTH and compute next TRUTH number
- 2. user confirms mint (“y”)
- 3. auto-update authoritative `TRUTH_VERSION` to new number
- 4. **Pre-artifact verification**:
- * TRUTH.md syntax and contiguity
- * single `TRUTH_VERSION` authority
- * version equals new TRUTH number
- * `app/main.py` imports authoritative version
- * AI index internal integrity
- * NO artifact existence checks
- 5. create FULL and SLIM truth artifacts
- 6. **Post-artifact verification**:
- * FULL zip exists
- * SLIM zip exists
- * artifact names match TRUTH number
- * AI index embedded/consistent
- 7. finalize and lock TRUTH
- NOTES
- * Prior failures (V14/V15) were caused by premature artifact verification
- * This truth explicitly forbids that class of error
- * Minting is now deterministic, phase-safe, and mechanically trustworthy


==================================================
TRUTH - project_template (TRUTH_V17)
==================================================

LOCKED
- Version: 17
- Timestamp: 2026-01-11 06:47:43

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V17)
- ====================================
- LOCKED
- * Verification MUST be explicitly phase-aware and MUST run in two named phases:
- * **PHASE 1/2: Pre-artifact verification**
- * **PHASE 2/2: Post-artifact verification**
- * Minting MUST emit clear console output identifying each phase exactly as:
- * `PHASE 1/2: Pre-artifact verification`
- * `PHASE 2/2: Post-artifact verification`
- * Pre-artifact verification MUST NOT assert the existence of FULL or SLIM artifacts
- * Post-artifact verification MUST assert:
- * FULL artifact exists
- * SLIM artifact exists
- * artifact filenames match the minted TRUTH number
- * The verifier interface MUST be explicit and non-ambiguous:
- * `verify_truth` MUST support an explicit phase argument (`--phase pre` and `--phase post`, or equivalent)
- * Phase selection MUST control whether artifact checks are enforced
- * Minting MUST remain ZERO-manual for versioning:
- * Answering “y” to mint MUST automatically update the authoritative `TRUTH_VERSION`
- * No human edits to `version.py`, `main.py`, or artifacts are permitted
- STATE
- * `tools/truth_manager.py` mint pipeline is strictly ordered and enforced as:
- 1. detect current TRUTH and compute next TRUTH number
- 2. user confirms mint (“y”)
- 3. auto-update authoritative `TRUTH_VERSION` to new number
- 4. emit `PHASE 1/2: Pre-artifact verification`
- * run `verify_truth --phase pre`
- 5. create FULL and SLIM truth artifacts
- 6. emit `PHASE 2/2: Post-artifact verification`
- * run `verify_truth --phase post`
- 7. finalize and lock TRUTH
- * `tools/verify_truth.py` behavior:
- * `--phase pre` runs all truth checks except artifact existence/naming checks
- * `--phase post` runs all truth checks including artifact existence/naming checks
- * Any legacy or ambiguous flags (e.g., `--skip-artifacts`) MUST be removed or deprecated in favor of explicit phase control
- NOTES
- * This truth formalizes the two-stage verification model and makes mint ordering mechanically auditable from logs.
- * Follow-on truths will address atomic writes, truncation/ellipsis guards, SLIM content assertions, and cross-platform tooling.


==================================================
TRUTH - project_template (TRUTH_V18)
==================================================

LOCKED
- Version: 18
- Timestamp: 2026-01-11 06:49:05

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V18)
- ====================================
- LOCKED
- * Minting MUST be resilient against silent corruption from partial writes
- * Updates to truth-critical state MUST be atomic:
- * `app/version.py` updates MUST be atomic (temp write + replace)
- * `TRUTH.md` updates MUST be atomic (temp write + replace)
- * `_ai_index` rebuild MUST be atomic (build in temp dir + swap/replace)
- * Verification MUST detect truncation/ellipsis artifacts:
- * Truth verification MUST FAIL if any repo text file contains a standalone truncation line matching: `^\s*\.\.\.\s*$`
- * This check MUST run in both verification phases (`--phase pre` and `--phase post`)
- * Minting MUST remain ZERO-manual for versioning:
- * Answering “y” MUST harmonize version state automatically
- * No human edits to `version.py`, `main.py`, or artifacts are permitted
- STATE
- * `tools/truth_manager.py` implements atomic writes:
- * `write_truth_version()` writes `app/version.py.tmp` then replaces `app/version.py`
- * `append_truth_md()` writes `TRUTH.md.tmp` then replaces `TRUTH.md`
- * `tools/ai_index.py` builds index into `_ai_index_tmp/` and then swaps to `_ai_index/` atomically
- * `tools/verify_truth.py` includes `verify_no_truncation_lines()`:
- * Scans all relevant repo text files (excluding `_truth/`, `_ai_index/`, venv, caches, zips, binaries)
- * Fails with file path + line number if a standalone `...` line is found
- * Runs for both `--phase pre` and `--phase post`
- NOTES
- * Atomic writes prevent “half-written truth state” and restore mechanical trust under interruption (crash/power loss)
- * Standalone ellipsis detection targets real truncation errors without false positives (e.g., `Tuple[str, ...]`)


==================================================
TRUTH - project_template (TRUTH_V19)
==================================================

LOCKED
- Version: 19
- Timestamp: 2026-01-11 06:49:53

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V19)
- ====================================
- LOCKED
- * SLIM truth artifacts MUST obey the SLIM exclusion contract and MUST be mechanically verifiable
- * Post-artifact verification (`--phase post`) MUST assert SLIM contents correctness, not just SLIM existence
- * SLIM verification MUST FAIL if the SLIM zip contains any forbidden paths or file types per config
- * SLIM verification MUST be driven by the authoritative tooling config (no hardcoded lists in code)
- STATE
- * `tools/truth_config.json` is the authoritative source of:
- * common exclusions (both FULL and SLIM)
- * SLIM-only exclusions
- * forbidden directories and file extensions for SLIM
- * `tools/verify_truth.py` adds `verify_slim_contents()` and runs it in `--phase post` only:
- * Opens the SLIM zip for the minted TRUTH number
- * Enumerates all members
- * Asserts none match:
- * excluded directories (e.g., `_truth/`, `_ai_index/`, `.git/`, `__pycache__/`, venvs, caches)
- * excluded file patterns/extensions (e.g., `.zip`, `.avi`, `.mp4`, `.png` if configured, etc.)
- * On failure, prints offending member path(s) and exits non-zero
- * `tools/truth_manager.py` continues to create SLIM based on the same config rules used by verification
- NOTES
- * This truth upgrades SLIM from “we think it’s slim” to “we can prove it is slim”
- * This prevents config drift and accidental inclusion of large/generated/private artifacts in SLIM outputs


==================================================
TRUTH - project_template (TRUTH_V20)
==================================================

LOCKED
- Version: 20
- Timestamp: 2026-01-11 06:50:33

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V20)
- ====================================
- LOCKED
- * Project health checks MUST be runnable without PowerShell
- * A cross-platform doctor command MUST exist and MUST perform the same essential checks as the PowerShell doctor script
- * Doctor MUST be non-destructive (read/verify only) and MUST exit non-zero on failure
- STATE
- * Add `tools/doctor.py` as the cross-platform equivalent of `tools/doctor.ps1`
- * `tools/doctor.py` performs, at minimum:
- 1. `python -m tools.verify_truth --phase post` (full verification including artifacts and SLIM content checks)
- 2. `python -m app.main` (smoke run; must execute successfully)
- * `tools/doctor.ps1` remains supported on Windows, but must delegate to or remain consistent with `tools/doctor.py`
- * `_BOOTSTRAP.txt` and `README.txt` MUST document the cross-platform doctor invocation:
- * `python -m tools.doctor`
- NOTES
- * This truth removes platform lock-in and enables CI/automation environments to run the same mechanical trust checks.
- * Doctor is intentionally verification-only: it must not mint, modify, or regenerate anything.


==================================================
TRUTH - project_template (TRUTH_V21)
==================================================

LOCKED
- Version: 21
- Timestamp: 2026-01-11 07:12:07

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V21)
- ==================================================
- LOCKED
- Continuous Integration MUST enforce mechanical trust on every push and PR
- CI MUST run the same non-destructive health gate as developers run locally
- CI MUST fail if `python -m tools.doctor` fails
- STATE
- Add a GitHub Actions workflow that runs on push and pull_request:
  - checks out repo
  - sets up Python
  - runs: `python -m tools.doctor`
- CI is read/verify only and MUST NOT mint, modify, or regenerate repo state
- NOTES
- This prevents regressions of truth, verification, artifacts, and index integrity


==================================================
TRUTH - project_template (TRUTH_V22)
==================================================

LOCKED
- Version: 22
- Timestamp: 2026-01-11 07:29:46

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V22)
- ==================================================
- LOCKED
- Creating a new project from the template MUST be zero-manual and mechanically correct
- New project creation MUST reseed truth state cleanly:
  - `PROJECT_NAME` replaced everywhere required
  - `_truth/` cleared/reset
  - `_ai_index/` cleared/reset and rebuilt
  - `TRUTH_VERSION` set to 1 in `app/version.py`
  - `TRUTH.md` seeded as a fresh truth history starting at V1
- New project creation MUST run a verification gate at the end and MUST fail fast on violation
- STATE
- `tools/new_project.py` implements the reseed workflow (cross-platform)
- `tools/new_project.ps1` delegates to `python -m tools.new_project`
- Workflow order is enforced:
- 1) copy template to destination
- 2) reset `_truth/` and `_ai_index/`
- 3) replace project name tokens
- 4) set `PROJECT_NAME` and `TRUTH_VERSION = 1` in `app/version.py`
- 5) seed `TRUTH.md` to TRUTH_V1
- 6) build `_ai_index` (`python -m tools.ai_index build`)
- 7) run `python -m tools.verify_truth --phase pre`
- Success prints `NEW_PROJECT OK`; failures stop immediately with non-zero exit
- NOTES
- This prevents new projects from inheriting template artifacts and guarantees a clean truth baseline.


==================================================
TRUTH - project_template (TRUTH_V23)
==================================================

LOCKED
- Version: 23
- Timestamp: 2026-01-11 07:31:40

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V23)
- ==================================================
- LOCKED
- Verification MUST detect additional authority drift and silent corruption
- `PROJECT_NAME` MUST have exactly ONE authoritative definition
- Truth configuration MUST have exactly ONE authoritative source
- Truncation detection MUST be stronger and configurable
- STATE
- `PROJECT_NAME` authority:
  - Exactly one assignment of `PROJECT_NAME = "..."` is permitted
  - It MUST reside in `app/version.py`
  - Any additional definitions MUST cause verification failure
- Truth config authority:
  - `tools/truth_config.json` is the single authoritative truth config
  - Any duplicate truth config file (e.g. root `truth_config.json`) MUST cause verification failure or be auto-removed during mint
- Truncation / corruption guards:
  - Verification MUST FAIL if any repo text file contains a standalone line matching: `^\s*\.\.\.\s*$`
  - Verification MUST FAIL if any repo text file contains forbidden marker substrings defined in `tools/truth_config.json`
- These checks MUST run in both verification phases (`--phase pre` and `--phase post`)
- NOTES
- This truth tightens authority boundaries and prevents subtle drift that can pass basic checks
- No behavioral changes to minting or artifacts are introduced; this is guard-only hardening


==================================================
TRUTH - project_template (TRUTH_V24)
==================================================

LOCKED
- Version: 24
- Timestamp: 2026-01-11 07:43:31

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V24)
- ==================================================
- LOCKED
- Verification MUST be mechanically correct and MUST NOT crash
- `python -m tools.verify_truth --phase pre|post` and `python -m tools.doctor` MUST run to completion (non-zero exit only on real verification failures)
- The V23 forbidden-marker scan MUST be wired to the authoritative config loader and MUST NOT reference undefined functions
- Truth config authority MUST be enforced deterministically:
  - `tools/truth_config.json` is authoritative
  - legacy duplicate `truth_config.json` at repo root MUST NOT be silently tolerated (verification must fail OR mint must auto-remove it before verification is considered valid)
- STATE
- Fix `tools/verify_truth.py` so forbidden-marker scanning loads config correctly (no NameError / undefined symbols)
- Ensure both phases call the forbidden-marker scan successfully
- Decide and enforce policy for legacy root `truth_config.json`:
  - Either fail verification when present, OR
  - remove it automatically during mint/new_project and do not emit “OK” status while it remains
- NOTES
- Current failure: `verify_forbidden_marker_substrings()` calls `load_config()` which is undefined, causing verification to crash in both phases and breaking doctor.


==================================================
TRUTH - project_template (TRUTH_V25)
==================================================

LOCKED
- Version: 25
- Timestamp: 2026-01-11 07:44:50

STATEMENT
- ﻿**CONTRACT ONLY**
- Here’s the **paste-ready TRUTH** to lock *before* we touch files.
- ```text
- ==================================================
- TRUTH - project_template (TRUTH_V25)
- ==================================================
- LOCKED
- Verification MUST be mechanically correct and MUST NOT crash
- `python -m tools.verify_truth --phase pre|post` and `python -m tools.doctor` MUST run to completion (non-zero exit only on real verification failures)
- The V23 forbidden-marker scan MUST be wired to the authoritative config loader and MUST NOT reference undefined functions
- Truth config authority MUST be enforced deterministically:
  - `tools/truth_config.json` is authoritative
  - legacy duplicate `truth_config.json` at repo root MUST NOT be silently tolerated (verification must fail OR mint must auto-remove it before verification is considered valid)
- STATE
- Fix `tools/verify_truth.py` so forbidden-marker scanning loads config correctly (no NameError / undefined symbols)
- Ensure both phases call the forbidden-marker scan successfully
- Decide and enforce policy for legacy root `truth_config.json`:
  - Either fail verification when present, OR
  - remove it automatically during mint/new_project and do not emit “OK” status while it remains
- NOTES
- Current failure: `verify_forbidden_marker_substrings()` calls `load_config()` which is undefined, causing verification to crash in both phases and breaking doctor.


==================================================
TRUTH - project_template (TRUTH_V26)
==================================================

LOCKED
- Version: 26
- Timestamp: 2026-01-11 08:01:35

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V26)
- ==================================================
- LOCKED
- Truth verification MUST be mechanically correct and MUST NOT crash
- Forbidden-marker scanning MUST load config correctly and MUST NOT scan the authoritative config file itself
- Post-artifact verification and doctor MUST pass after minting creates FULL/SLIM artifacts
- STATE
- `tools/verify_truth.py` forbidden-marker scan:
  - uses the authoritative config loader
  - excludes `tools/truth_config.json` from scanning
- Minting produces FULL and SLIM artifacts successfully and post-phase verification passes
- NOTES
- V25 mint crashed before artifact creation; V26 restores a green artifact state with the fixed verifier.


==================================================
TRUTH - project_template (TRUTH_V27)
==================================================

LOCKED
- Version: 27
- Timestamp: 2026-01-11 09:15:39

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V27)
- ==================================================
- LOCKED
- No broken patches: verification/doctor MUST not crash (SyntaxError is forbidden)
- CI Doctor MUST be phase-correct:
  - CI MUST NOT require local-only truth artifacts (FULL/SLIM zips) to exist in the repo
  - CI MUST run doctor in PRE phase
- Local Doctor MAY remain POST phase by default
- STATE
- `tools/doctor.py` MUST accept `--phase pre|post` (default: post)
- GitHub Actions workflow MUST run: `python -m tools.doctor --phase pre`
- Restore `tools/verify_ai_index.py` to a valid, strict implementation (no syntax errors)
- NOTES
- CI failure root cause: doctor was running post-phase (artifact-required) on a clean checkout
- Local failure root cause: broken `verify_ai_index.py` introduced by a bad patch


==================================================
TRUTH - project_template (TRUTH_V28)
==================================================

LOCKED
- Version: 28
- Timestamp: 2026-01-11 09:25:33

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V28)
- ==================================================
- LOCKED
- CI doctor MUST pass in PRE phase on GitHub Actions Linux runners
- _ai_index verification MUST be byte-stable across platforms
- Line ending normalization MUST NOT cause manifest size mismatches
- _WHY.txt MUST NOT cause recurring integrity failures
- STATE
- CI failure observed:
  - VERIFY FAIL: size mismatch for _WHY.txt (manifest 249 != actual 238)
- Local Windows verification may pass after rebuild, but CI fails on Linux
- Indicates manifest was generated from CRLF bytes while CI verifies LF bytes
- ROOT CAUSE
- _ai_index manifest captured file sizes from a CRLF working tree
- GitHub Actions checks out files with LF line endings
- _WHY.txt byte count differs between environments, triggering failure
- REQUIRED CHANGES
- Enforce LF line endings at the repository level via .gitattributes
- Renormalize tracked files so repository stores LF, not CRLF
- Rebuild _ai_index AFTER normalization so manifest reflects LF bytes
- Ensure _WHY.txt is treated as LF-only input for manifest generation
- ACCEPTANCE
- Fresh clone on GitHub Actions passes:
  - python -m tools.doctor --phase pre
- Fresh Windows clone + rebuild does NOT reintroduce CI mismatch
- No size mismatch errors for _WHY.txt or any manifest-tracked file
- NOTES
- This TRUTH explicitly addresses cross-platform byte determinism
- No weakening of verification logic is permitted


==================================================
TRUTH - project_template (TRUTH_V29)
==================================================

LOCKED
- Version: 29
- Timestamp: 2026-01-11 09:33:50

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V29)
- ==================================================
- LOCKED
- A single authoritative TRUTH_VERSION MUST exist
- All version references MUST be synchronized at mint time
- Truth minting MUST fail if any version drift is detected
- _ai_index MUST be rebuilt and verified as part of mint
- Bootstrap, index, and contract files MUST be validated during mint

