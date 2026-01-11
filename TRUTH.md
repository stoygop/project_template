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
- TRUTH_VERSION is an integer and the single authoritative truth version
- TRUTH_VERSION is stored only in app/version.py
- Minting a truth MUST require explicit user approval before incrementing version
- Minting MUST increment TRUTH_VERSION exactly by +1
- Minting MUST always produce FULL and SLIM zip artifacts on success
- Truth statement input MUST terminate on a standalone line `END` (sentinel-based)
- EOF / Ctrl+Z based termination is forbidden
- Minting MUST fail fast and loudly on version or format errors
- Truth header parsing MUST tolerate UTF-8 BOM and CRLF/LF differences

STATE
- tools/mint_truth.ps1 reads truth input line-by-line until `END`
- Truth statement files are written UTF-8 without BOM
- tools/truth_manager.py strips BOM before header validation
- Version parsing does not assume TRUTH_V-prefixed strings
- Version increment and artifact creation are atomic (no partial mint)

NOTES
- This truth formalizes integer-only versioning and END-sentinel input
- Header parsing hardening prevents Windows paste/encoding failures
- Any remaining EOF-based input handling or fragile header parsing is invalid

END

TRUTH - project_template (TRUTH_V3)
==================================================

LOCKED
- Minting MUST rebuild and verify _ai_index as part of every successful truth mint
- tools/truth_manager.py MUST call tools.verify_ai_index.main() using its actual signature (no argv if unsupported)
- Minting MUST fail fast and loudly if _ai_index rebuild/verify fails
- Successful mint MUST still produce FULL and SLIM zips after _ai_index passes

STATE
- tools/truth_manager.py no longer passes argv into verify_ai_index.main() when it takes no parameters
- _ai_index rebuild/verify remains mandatory during mint

NOTES
- This truth locks the mint pipeline integration with verify_ai_index and prevents signature mismatch regressions

END

