# Stage 00 — Project init & guardrails

## Goal
Create minimal, runnable scaffold for the OASIS→NS-3/SNS3 pipeline with safety rails.

## Deliverables
- Confirm folder tree; ensure .claude/settings.json and slash commands loaded.
- Add a Python venv + requirements.txt (sgp4, numpy, pandas optional).
- Create Makefile with: setup / test / parse / scenario / simulate.

## Steps (YOU MUST)
1. Read repo and CLAUDE.md. Summarize plan (no edits yet).
2. Propose concrete file list and get confirmation.
3. Implement files incrementally, running small tests after each change.
4. Avoid destructive commands; keep diffs small and well-described.

## Acceptance
- `make setup` succeeds.
- `make parse` shows a usage message (no real data yet).
