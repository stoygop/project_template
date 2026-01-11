project_template — Truth-driven Python project skeleton

Quick start
1) Mint a new Truth
   cd "C:\Users\stoyg\Documents\Programming\project_template"
   powershell -ExecutionPolicy Bypass -File .\tools\mint_truth.ps1

2) Create a new project from this template
   cd "C:\Users\stoyg\Documents\Programming\project_template"
   powershell -ExecutionPolicy Bypass -File .\tools\new_project.ps1 -NewName test_project

3) Run the new project
   cd "C:\Users\stoyg\Documents\Programming\test_project"
   python -m app.main

Health check (cross-platform)
- Run:
  cd "C:\Users\stoyg\Documents\Programming\project_template"
  python -m tools.doctor

Truth Manager GUI
- Run:
  cd "C:\Users\stoyg\Documents\Programming\project_template"
  python -m tools.truth_gui

- What it does:
  - Shows current TRUTH_VERSION
  - Lets you mint the next Truth (prompts for multi-line Truth statement)
  - Lets you manage exception folders used by SLIM zips

Truth artifacts (FULL + SLIM)
- Each mint produces:
  - <PROJECT>_TRUTH_V<N>_FULL.zip
  - <PROJECT>_TRUTH_V<N>_SLIM.zip
- Both are written to: .\_truth\
- FULL includes everything except common build/env caches.
- SLIM excludes media/large extensions + user-configurable exception folders.

AI index (truth-coupled, no zip)
- Build:
  cd "C:\Users\stoyg\Documents\Programming\project_template"
  python -m tools.ai_index build

- Verify:
  cd "C:\Users\stoyg\Documents\Programming\project_template"
  python -m tools.verify_ai_index

- Output folder:
  .\_ai_index\
  (file map + python symbol index + rollups + integrity metadata)

Notes
- TRUTH_VERSION is authoritative and stored as an integer in app\version.py.
- When cloning a new project, the new project starts at TRUTH_V1 and gets its own _truth folder on first mint.
