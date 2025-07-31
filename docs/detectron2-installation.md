# Detectron2 Installation Guide

This document details the installation process for Detectron2 and related dependencies in the Solstice project.

## Overview

Detectron2 is used for advanced layout detection in PDF processing. The installation is complex due to:
1. Python version constraints (3.11-3.12 only, no 3.13+ support)
2. Build-from-source requirement for newer Python versions
3. A known issue with iopath that requires a patched version

## Installation Methods

### Method 1: Using Make (Recommended)

```bash
make install-detectron2
```

This command:
1. Verifies Python version (3.11 or 3.12)
2. Clears the iopath cache to prevent conflicts
3. Installs dependencies using `requirements-detectron2.txt`
4. Verifies the installation

### Method 2: Manual Installation

If the make command fails, you can install manually:

```bash
# 1. Clear iopath cache
rm -rf ~/.torch/iopath_cache/

# 2. Install torch first
pip install torch torchvision -c requirements-constraints.txt

# 3. Install detectron2 from source with no build isolation
pip install 'git+https://github.com/facebookresearch/detectron2.git' --no-build-isolation

# 4. Install patched iopath (MUST be done after detectron2)
pip install 'git+https://github.com/facebookresearch/iopath@e348b6797c40c9eb4c96bf75e9aaf1b248297548' --force-reinstall

# 5. Verify installation
python -c "import layoutparser as lp; print('Detectron2 available:', lp.is_detectron2_available())"
```

## Understanding the Components

### requirements-detectron2.txt

This file specifies:
- **torch>=2.7.0**: Required for detectron2 build process
- **detectron2 from git**: Built from source for Python 3.11+ compatibility
- **Patched iopath**: Fixes the `?dl=1` query parameter issue when downloading models
- **layoutparser[layoutmodels]**: Provides the high-level API for layout detection

### The iopath Issue

The standard iopath version (0.1.9) has a bug where it fails to download models from URLs with query parameters like `?dl=1`. This causes errors like:

```
ValueError: Unsupported query remaining: f{'dl': ['1']}
```

The patched version (commit e348b6797c40c9eb4c96bf75e9aaf1b248297548) fixes this issue.

### Version Conflicts

You will see this warning after installation:

```
detectron2 0.6 requires iopath<0.1.10,>=0.1.7, but you have iopath 0.1.11
```

**This is expected and safe to ignore.** The patched iopath 0.1.11 is API-compatible with the version detectron2 expects.
