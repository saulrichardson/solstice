# Solstice – Automated Clinical Document Fact-Checking System

## Overview

Solstice is an advanced multi-agent AI system designed to automatically verify medical and pharmaceutical claims against clinical documents. It combines state-of-the-art computer vision, natural language processing, and multi-modal AI to extract evidence from complex PDFs and assess claim accuracy.

### Key Features

- **Multi-Agent Architecture**: Specialized AI agents for evidence extraction, verification, and presentation
- **Computer Vision Pipeline**: ML-powered layout detection using Detectron2 for accurate PDF parsing
- **Multi-Modal Analysis**: Extracts evidence from both text and visual elements (tables, figures, charts)
- **Intelligent Text Processing**: Medical term preservation, OCR correction, and context-aware extraction
- **Comprehensive Reporting**: Generates detailed evidence reports with source tracking and confidence scores

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Solstice System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Ingestion  │    │   Gateway    │    │ Fact-Check   │    │
│  │   Pipeline   │    │   Service    │    │   Engine     │    │
│  │              │    │              │    │              │    │
│  │ • PDF → Doc  │    │ • LLM Proxy  │    │ • Multi-Agent│    │
│  │ • Layout Det │    │ • Audit Log  │    │ • Evidence   │    │
│  │ • Text Ext   │    │ • Retry      │    │ • Verify     │    │
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

## Quick Start

### Prerequisites

- Python 3.11 or 3.12 (required for Detectron2 compatibility)
- Docker (for running the Gateway service)
- OpenAI API key
- Poppler (for PDF processing): `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux)

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd solstice

# Install Python dependencies
make install

# Install Detectron2 for layout detection (optional but recommended)
make install-detectron2

# Create .env file with your OpenAI API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...

# Start the Gateway service
make up
```

### Running a Fact-Check Study

1. **Prepare your documents** - Place PDFs in `data/clinical_files/`:
   ```
   data/clinical_files/
   ├── FlublokPI.pdf
   ├── CDC Influenza vaccines.pdf
   └── Arunachalam et al. (2021).pdf
   ```

2. **Process the PDFs** - Convert to structured documents:
   ```bash
   python -m src.cli ingest
   ```

3. **Create claims file** - Define claims to verify in `data/claims/example_claims.json`:
   ```json
   {
     "study_name": "Flublok Efficacy Claims",
     "claims": [
       {
         "id": "claim_001",
         "text": "Flublok is FDA approved for adults 18 years and older"
       },
       {
         "id": "claim_002", 
         "text": "Flublok contains 3x the hemagglutinin content of standard flu vaccines"
       }
     ]
   }
   ```

4. **Run the fact-check**:
   ```bash
   python -m src.cli run-study \
     --claims data/claims/example_claims.json \
     --documents FlublokPI "CDC Influenza vaccines"
   ```

5. **View results** in `data/studies/Flublok_Efficacy_Claims/`

## Module Documentation

### 1. Ingestion Module (`src/injestion/`)

The ingestion module converts PDFs into structured, analyzable documents.

#### Features
- **ML-Based Layout Detection**: Uses Detectron2 with PubLayNet/PrimaLayout models
- **Intelligent Text Extraction**: PyMuPDF-based extraction with medical term preservation
- **Multi-Pipeline Support**: Scientific (academic papers) and Marketing (visual materials) pipelines
- **Quality Assurance**: Built-in visualization tools for debugging

#### Usage
```python
from src.injestion.scientific import ingest_pdf

# Process a scientific paper
document = ingest_pdf("research_paper.pdf")
print(f"Extracted {len(document.blocks)} text blocks")
print(f"Found {len(document.figures)} figures/tables")
```

#### Output Structure
```
data/cache/<PDF_NAME>/
├── extracted/
│   ├── content.json      # Structured document
│   ├── document.md       # Markdown version
│   └── figures/          # Extracted images
├── visualizations/       # Layout detection results
└── pages/               # Page rasterizations
```

### 2. Gateway Module (`src/gateway/`)

A lightweight proxy service for OpenAI's API with enterprise features.

#### Features
- **Unified LLM Interface**: All AI calls route through the gateway
- **Audit Logging**: Write-only cache of all API responses
- **Automatic Retry**: Exponential backoff for transient failures
- **Provider Abstraction**: Extensible to support multiple LLM providers

#### Architecture
```
Fact-Check Agents → Gateway → OpenAI API
                      ↓
                 Audit Logs
```

### 3. Fact-Check Module (`src/fact_check/`)

The core fact-checking engine using a multi-agent pipeline.

#### Agent Pipeline

1. **EvidenceExtractor** → Finds relevant passages in documents
2. **EvidenceVerifierV2** → Verifies exact quotes and context
3. **CompletenessChecker** → Identifies missing evidence
4. **ImageEvidenceAnalyzer** → Analyzes tables, figures, charts
5. **EvidencePresenter** → Consolidates final evidence report

#### Configuration
```python
# Customize agent models in src/fact_check/config/agent_models.py
AGENT_MODELS = {
    "evidence_extractor": "gpt-4.1",
    "image_evidence_analyzer": "o4-mini",  # Vision-capable
    # ... other agents
}
```

## Data Flow

```
1. PDF Documents
       ↓
2. Ingestion Pipeline
   - Layout detection
   - Text extraction
   - Figure extraction
       ↓
3. Structured Documents (JSON)
       ↓
4. Fact-Check Engine
   - Evidence extraction
   - Quote verification
   - Image analysis
       ↓
5. Evidence Report
   - Supporting evidence
   - Contradicting evidence
   - Confidence scores
```

## Project Structure

```
solstice/
├── src/
│   ├── cli/              # Command-line interface
│   ├── injestion/        # PDF processing pipelines
│   │   ├── scientific/   # Academic paper pipeline
│   │   ├── marketing/    # Marketing material pipeline
│   │   └── shared/       # Common components
│   ├── gateway/          # LLM proxy service
│   │   ├── app/         # FastAPI application
│   │   └── providers/   # LLM provider implementations
│   ├── fact_check/       # Multi-agent fact-checking
│   │   ├── agents/      # Individual AI agents
│   │   ├── orchestrators/ # Pipeline coordination
│   │   └── config/      # Model configuration
│   └── interfaces/       # Shared data models
├── data/
│   ├── clinical_files/   # Input PDFs
│   ├── cache/           # Processed documents
│   ├── claims/          # Claim definition files
│   └── studies/         # Fact-check results
├── docker/              # Docker configurations
├── scripts/             # Setup and utility scripts
└── docs/               # Additional documentation
```

## Advanced Usage

### Custom Pipeline Configuration

```python
from src.injestion.shared.config import IngestionConfig
from src.injestion.scientific import PDFIngestionPipeline

config = IngestionConfig(
    detection_dpi=600,              # Higher quality scanning
    score_threshold=0.3,            # Stricter confidence
    merge_threshold=0.5,            # Box merging threshold
    expand_boxes=True,              # Prevent text cutoffs
    box_padding=20                  # Pixels to expand
)

pipeline = PDFIngestionPipeline(config=config)
document = pipeline.process_pdf("complex_layout.pdf")
```

### Batch Processing

```python
from src.fact_check.orchestrators import StudyOrchestrator

study = StudyOrchestrator(
    claims_file="data/claims/all_claims.json",
    documents=["doc1", "doc2", "doc3"],
    output_dir=Path("data/studies/comprehensive_study")
)

study.run()
```

### Marketing Pipeline

For marketing materials with complex layouts:

```bash
python -m src.injestion.marketing.cli marketing_brochure.pdf \
    --preset aggressive \
    --box-padding 15.0
```

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...              # Your OpenAI API key

# Optional
FILESYSTEM_CACHE_DIR=data/cache/gateway  # Gateway audit logs
SOLSTICE_LOG_LEVEL=INFO                  # Logging level
SOLSTICE_GATEWAY_PORT=8000               # Gateway port
FACT_CHECK_MAX_WORKERS=10                # Parallel processing
```

## Common Commands

```bash
# System management
make up                 # Start gateway service
make down               # Stop services
make logs               # View gateway logs
make verify             # Check installation

# Document processing
python -m src.cli ingest              # Process all PDFs
python -m src.cli ingest --help       # See options

# Fact checking
python -m src.cli run-study           # Run with defaults
python -m src.cli run-study --help    # See all options

# Development
make lint               # Run code linters
make format             # Format code
make clean              # Clean cache files
```

## Troubleshooting

### Installation Issues

**Python version mismatch**:
```bash
# Install pyenv and Python 3.11.9
pyenv install 3.11.9
pyenv local 3.11.9
```

**Detectron2 installation fails**:
```bash
# Use the robust installation script
bash scripts/install-detectron2.sh
```

### Processing Issues

**Poor text extraction**:
- Increase `detection_dpi` in config
- Check PDF quality with visualization tools
- Try marketing pipeline for complex layouts

**Missing figures/tables**:
- Lower `score_threshold` for more detections
- Check `data/cache/<PDF>/visualizations/` for detection results

### Gateway Issues

**Connection errors**:
- Verify `OPENAI_API_KEY` is set correctly
- Check gateway is running: `make logs`
- Test health endpoint: `curl localhost:8000/health`

## Contributing

1. Use Python 3.11 or 3.12
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Run formatters: `make format`
4. Run linters: `make lint`
5. Test changes thoroughly

## Architecture Principles

1. **Modularity**: Each component (ingestion, gateway, fact-check) is independent
2. **Extensibility**: Easy to add new pipelines, agents, or LLM providers
3. **Reliability**: Comprehensive error handling and retry logic
4. **Observability**: Structured logging and audit trails throughout
5. **Performance**: Parallel processing where possible, intelligent caching

## License

Proprietary - See LICENSE file for details