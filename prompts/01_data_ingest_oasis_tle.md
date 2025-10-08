# Stage 01 — Ingest OASIS log + (optional) TLE

## Goal
Parse OASIS-generated logs to extract: command windows (enter/exit), X-band data link windows, accessible time.
Optionally support TLE→visibility windows for validation when given TLE.

## Inputs
- Sample: `data/sample_oasis.log` (create synthetic if not available)
- (Optional) TLE samples in `data/`

## Steps
1. Implement `scripts/parse_oasis_log.py`:
   - Regex parse 'enter command window' / 'exit command window' / 'X-band data link window' lines.
   - Build window objects: start/end UTC, type, satellite, gateway, notes.
   - Output `data/oasis_windows.json` with schema + summary stats.
2. Add CLI options: `--tz`, `--sat`, `--gw`, `--min-duration` (filter/normalize).
3. (Optional) If TLE given, compute coarse pass windows for cross-check and add as `source="tle"`.

## Acceptance
- Unit tests for parser edge cases (duplicate/overlap/missing exit).
- Summary printed with counts and total durations.
