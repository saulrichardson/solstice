# Source Tree Overview

This directory contains all runtime code for **Solstice**.  The high-level
layout is organised by functional domain rather than by technical layer so
that contributors can quickly locate the part of the system they are working
on.

```
src/
├── cli/            # Command-line entry-points (ingest, run-study, etc.)
├── injestion/      # PDF processing pipelines – convert documents → JSON
│   ├── scientific/ # Standard pipeline for clinical/scientific PDFs
│   ├── marketing/  # Specialised pipeline for marketing material
│   └── shared/     # Re-usable ingestion utilities (box model, storage…)
├── fact_check/     # Multi-agent claim verification system
│   ├── agents/     # Evidence extraction, validation, completeness, images
│   ├── orchestrators/ # Coordinate agents per claim / study
│   └── utils/      # JSON parsing, resource helpers, etc.
├── gateway/        # HTTP service that proxies LLM requests (OpenAI-style)
├── core/           # Shared low-level utilities (config, logging, HTTP)
├── interfaces/     # Pydantic models shared across subsystems
└── util/           # Misc helper scripts and one-off tools
```

Key design notes
----------------
1. **BaseAgent.run() is the only way to execute a fact-checking agent.**
   This ensures consistent input validation, metadata logging, and output
   persistence across the pipeline.

2. **Ingestion and fact-checking are decoupled.**  The ingestion pipelines
   output normalised JSON files to `data/cache/…`.  The fact-checking
   orchestrators read those files asynchronously, enabling you to re-run
   claim verification without regenerating layouts.

3. **All external interactions flow through the `gateway` service.**  This
   keeps API-key handling, retries and caching in one place so the rest of
   the codebase can assume a stable OpenAI-compatible endpoint.

4. **Tests live next to the code they cover** (e.g. `tests/` packages inside
   `fact_check`).  Run `pytest` from the repo root.

For a deeper dive, see the architecture docs in the project-root `docs/`
folder.

