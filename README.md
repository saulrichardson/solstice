# Solstice – Clinical Document Fact-Checking Pipeline

Solstice is an LLM-powered pipeline for verifying medical claims against clinical documents. It uses computer vision for PDF layout detection, extracts structured content, and runs multi-step LLM verification.

## System Overview

### Core Services
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

### LLM Pipeline Flow
```
1. PDF Documents
       ↓
2. Ingestion Pipeline
   - Layout detection (Detectron2)
   - Text extraction
   - Figure/table extraction
       ↓
3. Structured Documents (JSON)
       ↓
4. Fact-Check Pipeline (via Gateway)
   - Evidence extraction (LLM)
   - Quote verification (LLM)  
   - Completeness check (LLM)
   - Image analysis (Vision LLM)
   - Evidence presentation (LLM)
       ↓
5. Evidence Report
   - Supporting evidence
   - Contradicting evidence
   - Confidence scores
```

## Quick Start

### Prerequisites

- Python 3.11 or 3.12
- Docker
- OpenAI API key
- Poppler: `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux)

### Setup

```bash
# Clone and enter directory
git clone <repo-url> && cd solstice

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install
make install-detectron2

# Configure API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...

# Start gateway service
make up
```

### Run

```bash
# Process PDFs
python -m src.cli ingest

# Run fact-check  
python -m src.cli run-study
```

Results in `data/studies/`