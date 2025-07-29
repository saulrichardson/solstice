#!/usr/bin/env python
"""Trace where the error is happening."""

import sys
import trace
from pathlib import Path

# Create a Trace object, telling it what to ignore, and whether to
# do tracing or line-counting or both.
tracer = trace.Trace(
    count=False,
    trace=True,
    ignoredirs=[sys.prefix, sys.exec_prefix, "/Users/saul/projects/solstice/solstice/.venv"],
)

# Run the test
pdf_path = Path("./data/clinical_files/Arunachalam et al. (2021).pdf")
print(f"Tracing execution for: {pdf_path}\n")

# Run with tracing
tracer.run('from src.injestion.pipeline import ingest_pdf; ingest_pdf(pdf_path)')