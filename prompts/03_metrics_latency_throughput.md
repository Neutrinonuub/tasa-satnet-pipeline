# Stage 03 — Metrics & KPIs

## Goal
Compute latency components (propagation/processing/queuing/transmission) and throughput for each window and end-to-end path.

## Steps
1. Add `scripts/metrics.py` with formulas and pluggable parameters.
2. For propagation, accept geometry-based light-time or fixed RTT approximations.
3. Processing delay depends on relay mode (transparent vs regenerative).
4. Generate `reports/metrics.csv` + `reports/summary.md` with tables.

## Acceptance
- Deterministic results for a fixed scenario (golden snapshot test).
