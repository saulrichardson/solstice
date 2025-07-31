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

## Quick-start

Prerequisites: Python 3.11–3.12, Docker (optional), an OpenAI API key, Poppler (`brew install poppler` / `apt-get install poppler-utils`).

```bash
# 1️⃣  Clone the repository
git clone <repo-url> && cd solstice

# 2️⃣  Create a virtual env (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# 3️⃣  Install dependencies (plus Detectron2 for layout detection)
make install && make install-detectron2

# 4️⃣  Configure OpenAI
cp .env.example .env && echo "OPENAI_API_KEY=sk-..." >> .env

# 5️⃣  (Optional) start gateway service for rate-limiting & audit logs
make up   # docker-compose up -d
```

Done! You can now ingest documents and run a fact-checking study:

```bash
# See all available commands
python -m src.cli --help

# Convert scientific PDFs → structured JSON
python -m src.cli ingest

# Process marketing materials (special layout handling)
python -m src.cli ingest-marketing

# Check all flu-vaccine claims
python -m src.cli run-study
```

---

## 1. Installation details

The quick-start should work on most systems. If it doesn't, follow the longer, OS-specific instructions below.

```bash
# 1. Clone & enter repo
git clone <repo-url> && cd solstice

# 2. Create a virtual environment (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Core dependencies
make install                # ↳ installs OpenAI, FAISS, PyMuPDF, etc.

# 4. Detectron2 (layout detection)
make install-detectron2     # uses CUDA if available, add CPU_ONLY=1 to force CPU

# 5. Environment variables
cp .env.example .env && echo "OPENAI_API_KEY=sk-..." >> .env

# 6. Optional: start gateway service
make up                     # docker-compose up -d
```

Common pitfalls:
• macOS M-series + Detectron2 – use `make install-detectron2 CPU_ONLY=1`.  
• Poppler missing – `brew install poppler` (macOS) / `apt-get install poppler-utils` (Debian/Ubuntu).  
• OpenAI rate limits – make sure the gateway is up; it automatically retries.

If problems persist, open an issue with the full error message and stack trace.

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
```
