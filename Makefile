.PHONY: help check up down logs test-gateway test-fact-checker lint format clean shell restart

help:
	@echo "Available commands:"
	@echo "  make check              Check if Docker is installed"
	@echo "  make up                 Start all services"
	@echo "  make down               Stop all services"
	@echo "  make logs               Show gateway logs"
	@echo "  make test-gateway       Test gateway is working"
	@echo "  make test-fact-checker  Test fact-checker endpoint"
	@echo "  make install            Install Python package for development"
	@echo "  make install-detectron2 Install Detectron2 for layout detection (Python 3.11 required)"
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

test-fact-checker:
	@./scripts/test-fact-checker.sh

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
	@echo "Installing patched iopath (fixes ?dl=1 issue)..."
	@pip install --force-reinstall git+https://github.com/facebookresearch/iopath@e348b6797c40c9eb4c96bf75e9aaf1b248297548
	@echo "✓ Detectron2 setup complete"
