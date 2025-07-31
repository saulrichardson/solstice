# Solstice – Clinical Document Fact-Checking Pipeline

Solstice is an **end-to-end research prototype** that takes a pile of PDF clinical documents and a list of free-text claims, and returns a structured, evidence-backed verdict for every claim.

## Quick Guide: README vs Technical Writeup

**Use this README when you want to:**
- Install and run Solstice
- Understand the basic commands
- Troubleshoot installation issues

**Read the [Technical Writeup (PDF)](docs/writeup/solstice.pdf) when you want to:**
- Understand the system architecture and design decisions
- Learn how the LLM pipeline works
- See the processing flow and data structures
- Understand why text and image processing are separated

---

## 1. Installation

**Prerequisites:** Python 3.11–3.12, OpenAI API key, Poppler utils

### Setting up Python with pyenv (Recommended)

```bash
# Install pyenv (if not already installed)
curl https://pyenv.run | bash

# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Install Python 3.12
pyenv install 3.12.0
pyenv local 3.12.0  # Set for this project

# Verify Python version
python --version  # Should show Python 3.12.0
```

### Project Setup

```bash
# Clone and setup
git clone <repo-url> && cd solstice
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install everything
make install && make install-detectron2   # Add CPU_ONLY=1 for M-series Macs

# Configure OpenAI
cp .env.example .env && echo "OPENAI_API_KEY=sk-..." >> .env

# (Optional) Start gateway service
make up
```

**Troubleshooting:**
- Missing Poppler: `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux)
- M-series Mac: Use `make install-detectron2 CPU_ONLY=1`
- See full commands with `python -m src.cli --help`

---

## 2. Run commands

```bash
# See all available commands and options
python -m src.cli --help

# Process scientific PDFs into machine-readable documents
python -m src.cli ingest

# Process marketing materials with special layout handling
python -m src.cli ingest-marketing

# Fact-check claims against all cached documents
python -m src.cli run-study

# Clear the document cache (removes all processed documents)
python -m src.cli clear-all-cache
```

**Cache Management:**
- Processed documents are stored in `data/scientific_cache/` and `data/marketing_cache/`
- Use `clear-all-cache` to remove all cached documents and start fresh
- Clearing the cache does NOT delete original PDFs, only the processed versions
