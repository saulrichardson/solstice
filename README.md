# Solstice – Clinical Document Fact-Checking Pipeline

Solstice is an **end-to-end research prototype** that takes a pile of PDF clinical documents (drug labels, journal articles, slide decks …) and a list of free-text claims, and returns a structured, evidence-backed verdict for every claim.

📄 **[Technical Writeup (PDF)](docs/writeup/solstice.pdf)** - Detailed system architecture, LLM pipeline, and implementation notes

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
3. Claims File (data/claims/Flublok_Claims.json)
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

## 3. What happens under the hood?

Below is the *real* (slightly simplified) execution plan so you can map the commands you run to the modules that fire.

--------------------------------------------------------
Step 1: Ingest PDFs → machine-readable artefacts
--------------------------------------------------------

Command: `python -m src.cli ingest`

1. Loader (`src.injestion.shared.loader`)
   • Scans `data/clinical_files/` for PDF, TIFF or PNG files.  
   • Streams each file page-by-page to keep memory footprint low.

2. Layout Detection (`src.injestion.shared.processing.layout_detector`)
   • Uses Detectron2 fine-tuned on 9k annotated FDA labels.  
   • Returns bounding boxes for *title*, *paragraph*, *table*, *figure* and *footer*.

3. Text Extraction (`src.injestion.shared.processing.text_extractors.pymupdf_extractor`)
   • Calls PyMuPDF for vector text; falls back to Tesseract OCR if the page is scanned.  
   • Keeps exact coordinates → later we can highlight snippets in the PDF.

4. Normalisation & Indexing (`src.injestion.shared.processing.reading_order`)
   • Splits text into ~250-token chunks with a sliding window.  
   • Saves structured content for semantic search during fact-checking.

Output: Structured JSON per document under `data/scientific_cache/`.

--------------------------------------------------------
Step 2: Run the fact-checking pipeline
--------------------------------------------------------

Command: `python -m src.cli run-study --claims path/to/file.json`

Input objects
• Claim list  → e.g. "Flublok is FDA approved for adults 18+".  
• Document set → every processed document in `data/scientific_cache/*`.

Pipeline orchestrator (`src.fact_check.orchestrators.claim_orchestrator`) executes these agents per claim:

1. Evidence Extractor (`agents/evidence_extractor.py`)
   • Semantic search over all documents to retrieve top-k text chunks (+ figures captions).  
   • Uses LLM to filter for relevance & returns a ranked list.

2. Completeness Checker (`agents/completeness_checker.py`)
   • Ensures no critical evidence type was missed (RCT vs observational, safety vs efficacy).  
   • Merges evidence from multiple sources to ensure comprehensive coverage.

3. Evidence Verifier (`agents/evidence_verifier_v2.py`)
   • Verifies that extracted quotes exist in the document.  
   • Confirms quotes genuinely support the claim using chain-of-thought reasoning.

4. Image Evidence Analyzer (`agents/image_evidence_analyzer.py`)
   • Analyzes all images in the document after text pipeline completes.  
   • Uses Vision model to determine if images support the claim.

5. Evidence Presenter (`agents/evidence_presenter.py`)
   • Combines all verified text and image evidence.  
   • Converts into compact JSON schema + markdown for presentation.

All intermediate LLM calls are cached in `data/studies/<study>/claim_x/agent_outputs/` so re-runs are cheap.

--------------------------------------------------------
Step 3: Gateway & safeguards (optional but recommended)
--------------------------------------------------------

If you started the Docker gateway (`make up`):
• Rate limiting: honours your OpenAI quota and retries with exponential back-off.  
• Request proxying: Routes LLM requests through a central service for monitoring.

--------------------------------------------------------
Step 4: Output folder anatomy
--------------------------------------------------------

```
data/studies/Flu_Vaccine_Study/
├── study_report.json              # High-level verdict summary
├── claim_001/
│   ├── evidence_report.json       # Merged & cleaned evidence
│   └── agent_outputs/             # 5 subfolders (one per agent)
└── ...
```

## 4. Project structure

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

## 5. Quick-start

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
# Convert PDFs → structured JSON
python -m src.cli ingest

# Check all flu-vaccine claims
python -m src.cli run-study
```

---

## 6. Installation details

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

## 7. Run commands

```bash
# Process PDFs into machine-readable documents
python -m src.cli ingest

# Run the marketing document pipeline  
python -m src.cli ingest-marketing

# Fact-check claims against all cached documents
python -m src.cli run-study
```
