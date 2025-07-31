# Installation Guide

This guide walks you through setting up **Fact Check** end-to-end.

It covers:
1. Basic setup (required) – text extraction & fact-checking.
2. Advanced setup (optional) – AI-powered PDF layout detection.

## Prerequisites

• Python 3.11 or 3.12  
• Poppler (`brew install poppler` / `apt-get install poppler-utils`).  
• OpenAI API key  
• Docker (optional, for the gateway service).

## 1. Clone + Python version

```bash
git clone <repository-url>
cd fact-check

# If pyenv is available the included .python-version file will auto-activate 3.11.9
python --version  # should report 3.11 / 3.12
```

If you need to install Python 3.11 manually, see Appendix A below.

## 2. Virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

Verify the version inside the venv:

```bash
python --version  # 3.11.x or 3.12.x
```

## 3. Core dependencies

```bash
make install
```

This installs:
• fact_check & gateway packages (editable mode)  
• FAISS, OpenAI, PyMuPDF, etc.

## 4. (Optional) Detectron2 for layout detection

```bash
make install-detectron2           # add CPU_ONLY=1 to skip CUDA
```

Expect a 5–10 min build and ~2 GB disk space.

## 5. Environment variables

```bash
cp .env.example .env
echo "OPENAI_API_KEY=sk-..." >> .env
```

## 6. Quick verification

```bash
make verify
```

Output should confirm that all critical libraries and Poppler are found.

## 7. Gateway service (optional)

```bash
make up        # docker-compose up -d
```

Provides rate-limit retries, audit logs, and cost accounting.

## 8. First run

```bash
# Convert PDFs → structured JSON
python -m src.cli ingest

# Fact-check claims
python -m src.cli run-study --name Demo_Study
```

Results live in data/studies/Demo_Study/.

---

### Appendix A – Installing Python 3.11 with pyenv

```bash
# macOS example
brew install pyenv
pyenv install 3.11.9
pyenv local 3.11.9       # creates .python-version automatically
```

Re-create your venv afterwards.

### Appendix B – Troubleshooting

• Wrong Python version inside venv → delete `.venv` and recreate with `python3.11`.  
• Detectron2 build fails on macOS M-series → `make install-detectron2 CPU_ONLY=1`.  
• `RuntimeError: Poppler missing` → install Poppler via your package manager.  
• OpenAI rate limits → make sure the gateway container is running (`make up`).

