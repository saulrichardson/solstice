#!/usr/bin/env python
"""Minimal test to isolate the issue."""

from pathlib import Path
from src.injestion.standard_pipeline import StandardPipeline
from src.injestion.config import DEFAULT_CONFIG

pdf_path = Path("./data/clinical_files/Arunachalam et al. (2021).pdf")
print(f"Testing: {pdf_path}")

pipeline = StandardPipeline(config=DEFAULT_CONFIG)

# Add debug to process_pdf
import sys
original_process_pdf = pipeline.process_pdf

def debug_process_pdf(path):
    print("1. Converting to images...", flush=True)
    images = pipeline._convert_to_images(path)
    print(f"   Got {len(images)} images", flush=True)
    
    print("2. Running detection...", flush=True)
    layouts = pipeline.detector.detect_images(images)
    print(f"   Got {len(layouts)} layouts", flush=True)
    
    print("3. Applying consolidation...", flush=True)
    consolidated = pipeline._apply_consolidation(layouts, images)
    print(f"   Got {len(consolidated)} pages", flush=True)
    
    print("4. Creating document...", flush=True) 
    document = pipeline._create_document(consolidated, path, images)
    print(f"   Created document with {len(document.blocks)} blocks", flush=True)
    
    print("5. Saving outputs...", flush=True)
    pipeline._save_outputs(document, path)
    print("   Done!", flush=True)
    
    return document

try:
    document = debug_process_pdf(pdf_path)
    print("SUCCESS!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()