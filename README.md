# TASA SatNet Pipeline

A reproducible pipeline to turn **OASIS** satellite comms logs into **NS-3/SNS3** scenarios, then simulate links and compute KPIs.

## Stages
See `prompts/` (00 → 07). Use with Claude Code (interactive), or headless with `claude -p`.

## Quickstart
```bash
# Interactive
claude

# Headless example
claude -p "Open prompts/01_data_ingest_oasis_tle.md and implement the parser" --allowedTools "Read,Edit,Bash(python *:*)" --max-turns 6 --output-format json
```
