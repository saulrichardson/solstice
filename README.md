# Solstice – Clinical Document Fact-Checking Pipeline

Solstice is an **end-to-end research prototype** that takes a pile of PDF clinical documents (drug labels, journal articles, slide decks …) and a list of free-text claims, and returns a structured, evidence-backed verdict for every claim.

Behind the scenes Solstice combines computer-vision layout analysis, traditional NLP, and a chain-of-thought LLM pipeline so you **don’t have to read 200 pages to check a single sentence**.

The project is intentionally kept small and hackable; everything runs from the command line and stores intermediate artefacts on disk so you can inspect (and tweak!) every step.

---

## 1. How Solstice fits together

```
┌─────────────────────────────────────────────────────────────────┐
│                         Solstice System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Ingestion  │    │   Gateway    │    │ Fact-Check   │    │
│  │   Pipeline   │    │   Service    │    │   Pipeline   │    │
│  │              │    │              │    │              │    │
│  │ • PDF → Doc  │    │ • LLM Proxy  │    │ • Extract    │    │
│  │ • Layout Det │    │ • Audit Log  │    │ • Verify     │    │
│  │ • Text Ext   │    │ • Retry      │    │ • Present    │    │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    │
│         │                    │                    │            │
│         └────────────────────┴────────────────────┘            │
│                              │                                  │
│                     ┌────────▼────────┐                        │
│                     │  Data Storage   │                        │
│                     │                 │                        │
│                     │ • Cache         │                        │
│                     │ • Documents     │                        │
│                     │ • Evidence      │                        │
│                     └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Processing flow

```
1. Input PDFs (data/clinical_files/)
   - FlublokPI.pdf
   - CDC Influenza vaccines.pdf  
   - Arunachalam et al. (2021).pdf
       ↓
2. Ingestion Pipeline
   - Detectron2 layout detection
   - PyMuPDF text extraction
   - Saves to data/scientific_cache/<document_name>/
       ↓
3. Claims File (data/claims/flu_vaccine_claims.json)
   - "Flublok is FDA approved for adults 18 years and older"
   - "Flublok demonstrated 30% better efficacy vs standard dose"
       ↓
4. Fact-Check Pipeline (5 LLM calls per claim)
   - Evidence extraction
   - Quote verification  
   - Completeness check
   - Image analysis
   - Evidence presentation
       ↓
5. Output (data/studies/Flu_Vaccine_Claims_Verification/)
   - study_report.json
   - claim_001/evidence_report.json
   - claim_002/evidence_report.json
```

## 3. Setup

### Prerequisites

- Python 3.11 or 3.12
- Docker
- OpenAI API key  
- Poppler: `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux)

# Quick-start (5 minutes)

```bash
# 1️⃣  Clone the repository
git clone <repo-url> && cd solstice

# 2️⃣  Create a virtual environment (optional but recommended)
python -m venv .venv && source .venv/bin/activate  # On Windows use .venv\Scripts\activate

# 3️⃣  Install python dependencies (+ Detectron2 for layout detection)
make install && make install-detectron2

# 4️⃣  Add your OpenAI API key
cp .env.example .env && echo "OPENAI_API_KEY=sk-..." >> .env

# 5️⃣  Spin up the optional gateway service (handles rate-limiting & audit logs)
make up  # docker-compose up -d under the hood
```

Done! You can now ingest documents and run a fact-checking study:

```bash
# Convert PDFs → structured JSON
python -m src.cli ingest

# Check all flu-vaccine claims
python -m src.cli run-study
```

---

## 4. Installation details (if you hit problems)

```bash
# Clone repository
git clone <repo-url> && cd solstice

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install
make install-detectron2

# Configure OpenAI
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...

# Start gateway service
make up
```

## 5. Run commands (expanded)

```bash
# Process included PDFs into structured documents
python -m src.cli ingest

# Run fact-check on flu vaccine claims
python -m src.cli run-study
```

## 6. What happens under the hood?

### 1. PDF Processing (`python -m src.cli ingest`)
- Reads PDFs from `data/clinical_files/`
- Detects layout elements at 400 DPI
- Extracts text preserving medical terminology
- Saves to `data/scientific_cache/FlublokPI/extracted/content.json` etc.

### 2. Fact-Checking (`python -m src.cli run-study`)
- Reads claims from `data/claims/flu_vaccine_claims.json`
- For each claim, runs 5 LLM agents sequentially
- Searches all cached documents for evidence
- Outputs to `data/studies/Flu_Vaccine_Claims_Verification/`

### 3. Output Structure
```
claim_001/
├── evidence_report.json     # Final consolidated evidence
├── agent_outputs/
│   ├── evidence_extractor/  # Found passages
│   ├── evidence_verifier/   # Quote verification
│   ├── completeness_check/  # Missing evidence types
│   ├── image_analyzer/      # Figure/table analysis
│   └── evidence_presenter/  # Final formatting
```

## 7. Project structure

```
solstice/
├── src/
│   ├── cli/                 # Command-line interface
│   ├── injestion/           # PDF processing
│   │   ├── scientific/      # Academic paper pipeline  
│   │   ├── marketing/       # Marketing material pipeline
│   │   └── shared/          # Common components
│   ├── gateway/             # LLM proxy service
│   │   └── app/             # FastAPI application
│   ├── fact_check/          # Fact-checking pipeline
│   │   ├── agents/          # Individual LLM agents
│   │   ├── orchestrators/   # Pipeline coordination
│   │   └── config/          # Model configuration
│   └── interfaces/          # Shared data models
├── data/
│   ├── clinical_files/      # Input PDFs
│   ├── scientific_cache/    # Processed documents
│   ├── claims/              # Claim files
│   └── studies/             # Results
├── docker/                  # Docker configurations
└── scripts/                 # Setup utilities
```

---

## 8. Contributing

Pull-requests are welcome.  The fastest path to a merged PR is:

1. Open a **Draft PR** early so we can discuss the approach.
2. Follow the existing naming and folder conventions (`*_pipeline`, `agents/*`, `orchestrators/*`).
3. Add a concise docstring that explains “why”, not only “what”.
4. Run `make lint test` (or at the very least `pytest -q`) before marking the PR as ready.

---

## 9. Troubleshooting FAQ

‣ `ImportError: No module named 'detectron2'`
    • The wheel build can be flaky on some systems.  Run `make install-detectron2 CPU_ONLY=1` to skip CUDA.

‣ `openai.error.RateLimitError`
    • Start the gateway service (`make up`) which retries failed calls with exponential back-off.

‣ `RuntimeError: Poppler not installed`
    • Install with `brew install poppler` (macOS) or `apt-get install poppler-utils` (Ubuntu/Debian).

If none of the above helps, open an issue with:
```
❯ python -m src.cli sys-info
OS, Python, Solstice commit, key dependency versions
```
and the full stack-trace.
