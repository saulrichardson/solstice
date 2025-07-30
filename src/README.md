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



