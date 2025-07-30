# Solstice

**Transform clinical PDFs into verified, structured data** - Solstice automatically extracts information from medical documents and fact-checks claims against evidence.

## What Does Solstice Do?

Solstice solves a critical problem: clinical documents (PDFs of trials, FDA submissions, research papers) contain valuable information locked in unstructured formats. Solstice extracts this data and verifies medical claims against the source documents.

### 🔄 How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Your PDFs     │ ──► │    Ingestion     │ ──► │ Structured JSON │
│                 │     │                  │     │                 │
│ • Clinical Docs │     │ • Text Extract   │     │ • Clean Text    │
│ • FDA Filings   │     │ • Table Detect   │     │ • Tables        │
│ • Research      │     │ • Layout Parse   │     │ • Figures       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                            │
                                                            ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Verified Claims │ ◄── │   Fact Check     │ ◄── │     Claims      │
│                 │     │                  │     │                 │
│ • Evidence      │     │ • Find Evidence  │     │ "Drug X reduces │
│ • Page Refs     │     │ • Verify Claims  │     │  symptoms by    │
│ • Confidence    │     │ • Check Images   │     │  40%"           │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## 📁 What Goes Where

```
solstice/
│
├── data/                    ← Your workspace
│   ├── clinical_files/      ← Drop PDFs here
│   ├── cache/               ← Extracted content (JSON)
│   ├── claims/              ← Claims to verify
│   └── studies/             ← Verification results
│
├── src/                     ← The engine
│   ├── injestion/           ← PDF → JSON converter
│   ├── fact_check/          ← Claim verification
│   └── gateway/             ← API management
│
└── docs/                    ← Guides & details
```

## 🚀 Quick Start

### 1. Install (5 minutes)
```bash
git clone <repo-url> && cd solstice
make install      # Requires Python 3.11 or 3.12
```

### 2. Add Your PDFs
```bash
cp your-document.pdf data/clinical_files/
```

### 3. Extract Content
```bash
make ingest
# Creates: data/cache/your-document/extracted_content.json
```

### 4. Verify Claims
```bash
make run-study
# Creates: data/studies/latest/evidence_report.json
```

## 🎯 Key Components

### Ingestion Pipeline
Converts PDFs into searchable, structured data:
- **Extracts**: Text, tables, figures, metadata
- **Fixes**: Common PDF text errors (spacing, encoding)
- **Preserves**: Medical terms, drug names, dosages
- **Output**: Clean JSON with page references

### Fact-Checking System
Verifies claims using multiple AI agents:
- **Evidence Agent**: Finds relevant passages
- **Verification Agent**: Confirms evidence supports claims
- **Completeness Agent**: Checks nothing is missing
- **Image Agent**: Analyzes charts and figures
- **Output**: Evidence report with exact quotes and page numbers

### Gateway Service
Manages AI/LLM interactions:
- **Purpose**: Central API proxy for all AI calls
- **Features**: Caching, retries, cost tracking
- **Usage**: `make up` to start, `make down` to stop

## 📊 Example Output

**Input PDF**: Clinical trial results  
**Claim**: "Treatment reduced symptoms by 40%"

**Output**:
```json
{
  "claim": "Treatment reduced symptoms by 40%",
  "verdict": "SUPPORTED",
  "evidence": [
    {
      "text": "The primary endpoint showed a 40.2% reduction in symptom severity (p<0.001)",
      "page": 12,
      "confidence": 0.95
    }
  ]
}
```

## 📚 Learn More

- **[Installation Guide](docs/01_installation.md)** - Step-by-step setup

## 🔧 Common Commands

```bash
make help         # Show all commands
make verify       # Check installation
make ingest       # Process PDFs
make run-study    # Run fact-checking
make up           # Start gateway
make logs         # View logs
make down         # Stop services
```

## 💡 Use Cases

- **Pharma Companies**: Verify claims in clinical trial reports
- **Regulatory Teams**: Check FDA submission accuracy
- **Research Groups**: Extract data from literature at scale
- **Medical Writers**: Fact-check publications against sources

## 🤝 Contributing

Contributions welcome! See open issues or submit a pull request.

## 📄 License

See LICENSE file for details.

