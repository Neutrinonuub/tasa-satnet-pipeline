# Stage 05 — Network slicing (k8s) — stub

## Goal
Provide a thin abstraction that maps scenario outputs to k8s/network-slicing intents (no real cluster ops).

## Steps
1. Define `scripts/slicing_stub.py` exporting JSON intents (bandwidth/latency per slice).
2. Document how intents would be applied in a real system (CRDs/Controllers).

## Acceptance
- `reports/slicing_intents.json` generated.
