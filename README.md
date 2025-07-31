# Fact Check – Clinical Document Fact-Checking Pipeline

Fact Check is an **end-to-end research prototype** that takes a pile of PDF clinical documents (drug labels, journal articles, slide decks …) and a list of free-text claims, and returns a structured, evidence-backed verdict for every claim.

Behind the scenes Fact Check combines computer-vision layout analysis, traditional NLP, and a chain-of-thought LLM pipeline so you **don’t have to read 200 pages to check a single sentence**.

The project is intentionally kept small and hackable; everything runs from the command line and stores intermediate artefacts on disk so you can inspect (and tweak!) every step.

---

## 1. How Fact Check fits together

```
┌--------------------------------------------------------─────────┐
│                         Fact Check System                       │
├--------------------------------------------------------─────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Ingestion  │    │   Gateway    │    │ Fact-Check   │       │
│  │   Pipeline   │    │   Service    │    │   Pipeline   │       │
│  │              │    │              │    │              │       │
│  │ • PDF → Doc  │    │ • LLM Proxy  │    │ • Extract    │       │
│  │ • Layout Det │    │ • Audit Log  │    │ • Verify     │       │
│  │ • Text Ext   │    │ • Retry      │    │ • Present    │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                    │                    │             │
│         └────────────────────┴────────────────────┘             │
│                              │                                  │
│                     ┌────────▼────────┐                         │
│                     │  Data Storage   │                         │
│                     │                 │                         │
│                     │ • Cache         │                         │
│                     │ • Documents     │                         │
│                     │ • Evidence      │                         │
│                     └─────────────────┘                         │
└--------------------------------------------------------─────────┘

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

## 1. Quick-start

Below is the *real* (slightly simplified) execution plan so you can map the commands you run to the modules that fire.

--------------------------------------------------------
Step 1: Ingest PDFs → machine-readable artefacts
--------------------------------------------------------

Command: `python -m src.cli ingest`

1. Loader (`src.ingestion.shared.loader`)
   • Scans `data/clinical_files/` for PDF, TIFF or PNG files.  
   • Streams each file page-by-page to keep memory footprint low.

2. Layout Detection (`src.ingestion.shared.layout_detect`)
   • Uses Detectron2 fine-tuned on 9k annotated FDA labels.  
   • Returns bounding boxes for *title*, *paragraph*, *table*, *figure* and *footer*.

3. Text Extraction (`src.ingestion.shared.text_extract`)
   • Calls PyMuPDF for vector text; falls back to Tesseract OCR if the page is scanned.  
   • Keeps exact coordinates → later we can highlight snippets in the PDF.

4. Normalisation & Indexing (`src.ingestion.shared.postprocess`)
   • Splits text into ~250-token chunks with a sliding window.  
   • Inserts into a FAISS index (bi-encoder sentence embeddings) stored at `data/cache/<doc>/faiss.index`.

Output: Structured JSON + FAISS index per document under `data/cache/`.

--------------------------------------------------------
Step 2: Run the fact-checking pipeline
--------------------------------------------------------

Command: `python -m src.cli run-study --claims path/to/file.json`

Input objects
• Claim list  → e.g. “Flublok is FDA approved for adults 18+”.  
• Document set → every FAISS index in `data/cache/*`.

Pipeline orchestrator (`src.fact_check.orchestrators.pipeline`) executes **five specialised LLM agents** per claim:

1. Evidence Extractor (`agents/evidence_extractor.py`)
   • Semantic search over all indexes to retrieve top-k text chunks (+ figures captions).  
   • Uses GPT-4 to filter for relevance & returns a ranked list.

2. Image Analyzer (`agents/image_analyzer.py`)
   • If the extractor flagged an image region, sends the PNG crop to the OpenAI Vision model.  
   • Produces a natural-language caption we can later cite.

3. Evidence Verifier (`agents/evidence_verifier.py`)
   • Chain-of-thought prompt: “Does the passage logically support / refute the claim?  Answer Y/N and explain.”  
   • Adds a probability score calibrated with temperature scaling.

4. Completeness Check (`agents/completeness_check.py`)
   • Ensures no *critical* evidence type was missed (RCT vs observational, safety vs efficacy …).  
   • May trigger a second retrieval pass if gaps are detected.

5. Evidence Presenter (`agents/evidence_presenter.py`)
   • Converts everything into a compact JSON schema + a markdown snippet for UI use.  
   • Adds clickable PDF coordinate links when run inside the Streamlit demo.

All intermediate LLM calls are cached in `data/studies/<study>/claim_x/agent_outputs/` so re-runs are cheap.

--------------------------------------------------------
Step 3: Gateway & safeguards (optional but recommended)
--------------------------------------------------------

If you started the Docker gateway (`make up`):
• Rate limiting: honours your OpenAI quota and retries with exponential back-off.  
• Audit log: every request / response pair saved to `data/gateway_log.sqlite`.  
• Cost accounting: CLI command `python -m src.cli cost-report` prints spend per study.

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

## 2. Installation details

```
fact-check/
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

## 3. Run commands

Prerequisites: Python 3.11–3.12, Docker (optional), an OpenAI API key, Poppler (`brew install poppler` / `apt-get install poppler-utils`).

```bash
# 1️⃣  Clone the repository
git clone <repo-url> && cd fact-check

# 2️⃣  Create a virtual env (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# 3️⃣  Install dependencies (plus Detectron2 for layout detection)
make install && make install-detectron2

# 4️⃣  Configure OpenAI
cp .env.example .env && echo "OPENAI_API_KEY=sk-..." >> .env

# 5️⃣  (Optional) start gateway service for rate-limiting & audit logs
make up   # docker-compose up -d
```

---

## 4. What happens under the hood?

```bash
# Convert PDFs → structured JSON
python -m src.cli ingest

# Fact-check all claims against all cached documents
python -m src.cli run-study --name Flu_Study
```

For additional options run `python -m src.cli --help`.

---

## 5. Project structure 


```bash
# 1. Clone & enter repo
git clone <repo-url> && cd fact-check

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
