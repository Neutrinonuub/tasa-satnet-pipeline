# Stage 04 — Beams & scheduling

## Goal
Model user beam allocation to gateways during command/data windows; resolve conflicts and maximize throughput.

## Steps
1. Implement greedy scheduler (baseline) then optional ILP/CP-SAT for optimality.
2. Respect beam capacity constraints; avoid overlapping allocations per terminal/beam.
3. Output scheduled plan `reports/schedule.csv` and visualize Gantt-like timeline (ASCII or matplotlib).

## Acceptance
- Sanity checks pass (no overlaps, capacities respected).
