# Stage 02 — Scenario generation for NS-3/SNS3

## Goal
Transform parsed windows into a simulation scenario config (topology + schedule).

## Steps
1. Define `config/schema_scenario.json` (satellites, gateways, user beams, terminals, links, events).
2. Create `scripts/gen_scenario.py` to convert from `data/oasis_windows.json` to `config/ns3_scenario.json`.
3. Provide toggles for relay mode: `transparent` vs `regenerative`.
4. If SNS3 format differs, output `config/sns3_scenario.json`.

## Acceptance
- JSON Schema validates.
- Example scenario generated from sample windows.
