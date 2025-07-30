# Solstice – internal toolkit

This repository is aimed at developers who already know what Solstice does.
The root README therefore stays minimal; detailed docs live in the `docs/`
folder.

## Quick start

```bash
git clone <repo-url> && cd solstice
make install          # Python deps (3.11 / 3.12)
make ingest           # Process PDFs in data/clinical_files/
make run-study        # Verify example claims
```

## Documentation

* Architecture & background – `docs/00_project_overview.md`
* Installation (incl. Detectron 2) – `docs/01_installation.md`

## Repo layout (very high level)

```
data/      user-supplied PDFs, cache, study outputs
src/       ingestion, fact-checking, gateway code
docs/      in-depth guides and API notes
writeup/   LaTeX report and figures (final paper)
```

Everything else should be self-explanatory once you open the docs.

