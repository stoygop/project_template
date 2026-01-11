==================================================
TRUTH - project_template (TRUTH_V1)
==================================================

LOCKED
- Version: 1
- Truth history reset: prior TRUTH entries removed by explicit decision
- Doctor supports explicit phases: `python -m tools.doctor --phase pre|post`
- CI runs doctor in PRE phase: `python -m tools.doctor --phase pre`
- Truth minting is one-command and prompts for TRUTH text in-terminal; terminator is END
- Minting auto-commits any pre-mint dirty working tree state (one-click workflow)
- _ai_index generation is cross-platform deterministic (LF output; no CRLF/LF byte drift)
- Repository enforces LF via .gitattributes for text files that affect verification/indexing

STATEMENT
- This TRUTH intentionally restarts project_template truth history at V1.
- All prior TRUTH content is considered harvested and superseded by this reset.

NOTES
- Next: define and implement phased TRUTH format (LOCKED PRE / LOCKED POST) and migrate forward in new history.

END

==================================================
TRUTH - project_template (TRUTH_V2)
==================================================

LOCKED
- Version: 2
- Timestamp: 2026-01-11 10:23:30

STATEMENT
- ﻿==================================================
- TRUTH - project_template (TRUTH_V2)
- ==================================================
- LOCKED PRE
- TRUTH format is standardized as D:
  - `LOCKED PRE`
  - `LOCKED POST`
  - optional `NOTES`
  - single `END`
- Truth workflow must be enforced as a first-class process:
  - CONFIRM step exists (lock “last changes verified by user”)
  - DREAM step exists (lock next implementation requirements)
  - DEBUG step exists (fast iteration path when DREAM fails)
- Tooling must support the workflow without manual bookkeeping:
  - `tools.truth_manager` must offer explicit commands or flags to mint CONFIRM/DREAM/DEBUG truths
  - Mint must refuse malformed TRUTH blocks (missing sections, wrong order, missing END)
- LOCKED POST
- One-command mint flow supports the workflow end-to-end:
  - prompts for TRUTH text
  - runs pre-verify before modifying repo state
  - mints TRUTH
  - rebuilds `_ai_index`
  - runs `tools.doctor --phase pre`
  - commits + pushes
- Provide a “repeat loop” path when tests fail:
  - mint DEBUG truth
  - patch
  - test
  - return to CONFIRM when fixed
- NOTES
- This truth is about workflow + enforcement only (no feature work)
- END

