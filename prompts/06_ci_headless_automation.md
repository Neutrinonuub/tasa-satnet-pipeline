# Stage 06 — CI & headless automation

## Goal
Demonstrate `claude -p` headless runs for repeatable tasks and JSON outputs.

## Steps
1. Add GitHub Actions workflow (if repo on GitHub) to run `make parse && make scenario && make metrics`.
2. Provide scripts/headless_examples.sh with `claude -p --output-format json` examples.

## Acceptance
- Headless examples produce machine-parsable JSON and exit 0.
