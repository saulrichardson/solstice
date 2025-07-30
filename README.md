# Solstice

Solstice is an end-to-end system for extracting structured information from
clinical PDFs and automatically fact-checking claims against those documents.

* 📄  Advanced PDF layout detection (text / tables / figures)
* 🔍  Multi-agent claim verification with GPT-4-class models
* 🚀  Production-ready, Docker-based deployment

Full documentation lives in the `docs/` folder. If you are new to the project
start here:

* **Project overview:** [`docs/00_project_overview.md`](docs/00_project_overview.md)
* **Installation guide:** [`docs/01_installation.md`](docs/01_installation.md)

Quick start (core pipeline):

```bash
git clone <repo-url> && cd solstice
make install          # install Python deps
make ingest           # process PDFs in data/clinical_files/
make run-study        # verify sample claims
```

For questions or contributions please open an issue or pull request.

