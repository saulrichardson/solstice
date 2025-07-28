.PHONY: help check up down logs test-gateway lint format clean shell restart

help:
	@echo "Available commands:"
	@echo "  make check              Check if Docker is installed"
	@echo "  make up                 Start all services"
	@echo "  make down               Stop all services"
	@echo "  make logs               Show gateway logs"
	@echo "  make test-gateway       Test gateway is working"
	@echo "  make install            Install Python package for development"
	@echo "  make install-detectron2 Install Detectron2 for layout detection (Python 3.11 required)"
	@echo "  make install-tatr       Install Table Transformer (TATR) with weights"
	@echo "  make lint               Run linting"
	@echo "  make format             Format code"
	@echo "  make clean              Clean up cache files"

check:
	@command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required but not installed."; echo "Install from: https://docs.docker.com/get-docker/"; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "Error: Docker daemon is not running. Start Docker and try again."; exit 1; }
	@echo "✓ Docker is installed and running"


up: check
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file - please add your OpenAI API key"; fi
	docker compose up -d
	@echo ""
	@echo "Gateway running at http://localhost:4000"
	@echo "Test with: curl http://localhost:4000/health"


down:
	docker compose down

logs:
	docker compose logs -f gateway

test-gateway:
	@./scripts/test-gateway.sh

lint:
	ruff check .
	mypy .

format:
	black .
	ruff check --fix .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache

shell:
	docker compose exec gateway /bin/bash

# Development shortcuts
dev: dev-install up logs

restart:
	docker compose restart gateway
	make logs

install:
	@echo "Installing fact-check package..."
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "⚠️  Warning: No virtual environment detected"; \
		echo "   Recommended: python3 -m venv venv && source venv/bin/activate"; \
		echo ""; \
	fi
	pip install -e .
	@echo "✓ Package installed successfully"

install-detectron2: install
	@echo "Installing Detectron2 for layout detection..."
	@python -c "import sys; v=sys.version_info; exit(0 if 3.11<=v.major+v.minor/10<3.13 else 1)" || \
		{ echo "Error: Python 3.11 or 3.12 required"; exit 1; }
	@command -v pdfinfo >/dev/null 2>&1 || \
		{ echo "Warning: Poppler not installed. Install with: brew install poppler"; }
	@echo "Installing PyTorch..."
	@pip install torch torchvision
	@echo "Installing Detectron2..."
	@pip install git+https://github.com/facebookresearch/detectron2.git
	@echo "Installing compatible iopath for detectron2..."
	@pip install "iopath>=0.1.7,<0.1.10"
	@echo "✓ Detectron2 setup complete"

install-tatr: install
	@echo "Installing Table Transformer (TATR) dependencies..."
	@command -v tesseract >/dev/null 2>&1 || \
		{ echo "Warning: Tesseract not installed. Install with: brew install tesseract tesseract-lang"; }
	@echo "Resolving dependency conflicts..."
	@pip install "pillow~=9.5.0"
	@echo "Installing TATR package with OCR support..."
	@pip install -e ".[tatr]"
	@echo ""
	@echo "Downloading TATR weights..."
	@mkdir -p assets/tatr
	@echo "1. Downloading detection model (45MB)..."
	@if [ -f assets/tatr/pubtables1m_det_r18.pth ]; then \
		echo "   ✓ Detection weights already downloaded"; \
	else \
		curl -L -o assets/tatr/pubtables1m_det_r18.pth \
			https://huggingface.co/microsoft/table-transformer-detection/resolve/main/pytorch_model.bin || \
		{ echo "Error: Failed to download detection weights"; exit 1; }; \
		echo "   ✓ Detection weights downloaded"; \
	fi
	@echo "2. Downloading structure recognition model v1.1 (195MB)..."
	@if [ -f assets/tatr/tatr_v1.1_pub.pth ]; then \
		echo "   ✓ Structure weights already downloaded"; \
	else \
		curl -L -o assets/tatr/tatr_v1.1_pub.pth \
			https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-pub/resolve/main/pytorch_model.bin || \
		{ echo "Error: Failed to download structure weights"; exit 1; }; \
		echo "   ✓ Structure weights downloaded"; \
	fi
	@echo ""
	@echo "Verifying installation..."
	@python -c "from table_transformer import TableExtractionPipeline; print('✓ Table Transformer imported successfully')" || \
		{ echo "Error: Failed to import Table Transformer"; exit 1; }
	@echo "✓ Table Transformer setup complete"
