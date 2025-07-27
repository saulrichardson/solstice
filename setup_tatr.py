"""Setup script for Table Transformer (TATR).

This script:
1. Installs required dependencies
2. Downloads TATR v1.1 weights
3. Verifies the installation
"""

import subprocess
import sys
import os
from pathlib import Path


def install_dependencies():
    """Install required Python packages."""
    print("Installing Table Transformer dependencies...")
    
    packages = [
        "table-transformer[pytesseract]",
        "pillow",
        "pdfplumber", 
        "PyMuPDF",
        "pandas",
        "tabulate",  # For markdown conversion
        "pytesseract"
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    print("\nDependencies installed successfully!")


def download_weights():
    """Download TATR v1.1 weights."""
    from src.injestion.extractors import download_tatr_weights
    
    print("\nDownloading TATR v1.1 weights...")
    try:
        download_tatr_weights()
        print("Weights downloaded successfully!")
    except Exception as e:
        print(f"Error downloading weights: {e}")
        print("\nPlease download manually from:")
        print("https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-pub/resolve/main/pytorch_model.bin")
        print(f"Save to: {os.path.expanduser('~/.cache/tatr/tatr_v1.1_pub.pth')}")


def verify_installation():
    """Verify TATR is properly installed."""
    print("\nVerifying installation...")
    
    # Check imports
    try:
        from tatr.inference import TableExtractor
        print("✓ table-transformer package imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import table-transformer: {e}")
        return False
    
    # Check weights
    weights_path = os.path.expanduser("~/.cache/tatr/tatr_v1.1_pub.pth")
    if os.path.exists(weights_path):
        print(f"✓ TATR weights found at {weights_path}")
    else:
        print(f"✗ TATR weights not found at {weights_path}")
        return False
    
    # Check Tesseract
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        print("✓ Tesseract OCR is installed")
    except Exception:
        print("✗ Tesseract OCR not found. Install with: brew install tesseract")
        print("  (TATR will still work but with reduced accuracy)")
    
    print("\nInstallation verified successfully!")
    return True


def main():
    """Main setup function."""
    print("Setting up Table Transformer (TATR)...")
    print("=" * 60)
    
    # Install dependencies
    install_dependencies()
    
    # Download weights
    download_weights()
    
    # Verify
    if verify_installation():
        print("\n" + "=" * 60)
        print("Setup completed successfully!")
        print("\nYou can now use TATR for table extraction:")
        print('  table_method="tatr" in extract_with_specialized_extractors()')
    else:
        print("\nSetup completed with warnings. Please check the errors above.")


if __name__ == "__main__":
    main()