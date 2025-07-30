# Solstice

Solstice is a comprehensive clinical document processing system that transforms unstructured medical PDFs into actionable insights through state-of-the-art layout detection and AI-powered fact-checking.

## 🎯 What is Solstice?

Solstice addresses a critical challenge in healthcare and life sciences: extracting reliable, structured information from complex clinical documents (clinical trials, FDA submissions, research papers) and verifying claims against evidence. Built for production use, it combines advanced document processing with transparent, multi-agent fact-checking to ensure accuracy and traceability.

## ✨ Key Features

* **📄 Advanced PDF Processing**
  - State-of-the-art layout detection powered by Detectron2
  - Accurate extraction of text, tables, figures, and metadata
  - Intelligent text correction that preserves medical terminology
  - Handles complex multi-column layouts and scientific notation

* **🔍 Evidence-Based Fact Checking**
  - Multi-agent system with specialized roles (evidence extraction, validation, completeness checking)
  - Every claim traced to exact quotes with page references
  - Transparent verification process with detailed audit trails
  - Support for analyzing charts and visual evidence

* **🚀 Production Ready**
  - Docker-based deployment with automatic scaling
  - API gateway for centralized LLM management
  - Built-in caching and error handling
  - Comprehensive logging and monitoring

* **🏥 Domain Optimized**
  - Specialized pipelines for clinical vs. marketing documents
  - Preserves critical medical information (drug names, dosages, procedures)
  - Handles FDA documents, clinical trial protocols, and research papers

## 🚦 Quick Start

```bash
# Clone and setup
git clone <repo-url> && cd solstice
make install              # Install core dependencies (Python 3.11/3.12 required)

# Process clinical PDFs
cp your-documents.pdf data/clinical_files/
make ingest              # Extract structured content from PDFs

# Run fact-checking on claims
make run-study           # Verify claims against extracted evidence

# View results
ls data/cache/           # Extracted document content
ls data/studies/         # Fact-checking results
```

## 📚 Documentation

* **[Installation Guide](docs/01_installation.md)** - Detailed setup instructions with troubleshooting
* **[Project Overview](docs/00_project_overview.md)** - Architecture, components, and technical details

## 🏗️ Architecture Overview

```
PDF Documents → Ingestion Pipeline → Structured JSON → Fact-Checking System → Evidence Results
      ↓                                     ↓                    ↓
Layout Detection                    Tables & Figures      Multi-Agent Verification
Text Correction                     Metadata Extraction   Transparent Evidence Trails
```

### Core Components

1. **Document Ingestion** (`src/injestion/`)
   - Converts PDFs to searchable, structured JSON
   - Separate pipelines for clinical and marketing materials
   - Preserves document structure and relationships

2. **Fact-Checking Engine** (`src/fact_check/`)
   - Orchestrates multiple AI agents for comprehensive verification
   - Ensures evidence traceability and prevents hallucination
   - Generates detailed verification reports

3. **API Gateway** (`src/gateway/`)
   - Manages all LLM interactions with caching and retries
   - Provides usage analytics and cost control
   - OpenAI-compatible endpoints

## 🔧 Common Use Cases

- **Clinical Trial Analysis**: Extract protocols, results, and adverse events from trial documents
- **Regulatory Compliance**: Verify claims in FDA submissions and marketing materials
- **Literature Review**: Process and fact-check scientific papers at scale
- **Data Extraction**: Build structured datasets from unstructured medical documents
- **Evidence Synthesis**: Find and validate supporting evidence across document collections

## 🛠️ Development

```bash
make help         # Show all available commands
make verify       # Check installation status
make format       # Auto-format code
make lint         # Check code quality
make test         # Run test suite
```

## 📋 Requirements

- Python 3.11 or 3.12 (required for Detectron2 compatibility)
- Poppler for PDF processing
- OpenAI API key for fact-checking features
- 8GB+ RAM recommended for layout detection
- Docker for production deployment

## 🤝 Contributing

We welcome contributions! Please:
1. Check existing issues or create a new one
2. Fork the repository and create a feature branch
3. Ensure tests pass and code is formatted
4. Submit a pull request with clear description

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

Solstice builds on excellent open-source projects including Detectron2, LayoutParser, PyMuPDF, and the broader Python scientific computing ecosystem.

