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

