.PHONY: help check up down logs lint format shell restart docker-status

help:
	@echo "Available commands:"
	@echo "  make check              Check if Docker is installed"
	@echo "  make up                 Start all services"
	@echo "  make down               Stop all services"
	@echo "  make logs               Show gateway logs"
	@echo "  make docker-status      Show Docker runtime info"
	@echo "  make install            Install Python package for development"
	@echo "  make install-detectron2 Install Detectron2 for layout detection (Python 3.11.9 required)"
	@echo "  make verify             Verify installation and dependencies"
	@echo "  make lint               Run linting"
	@echo "  make format             Format code"
	@echo "  make writeup            Build technical documentation PDF"
	@echo "  (no clean target anymore)"

check:
	@command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required but not installed."; echo "Install from: https://docs.docker.com/get-docker/"; exit 1; }
	@if ! docker info >/dev/null 2>&1; then \
		if command -v colima >/dev/null 2>&1 && colima status >/dev/null 2>&1; then \
			echo "Docker not responding. Restarting Colima..."; \
			colima restart; \
			sleep 2; \
			docker info >/dev/null 2>&1 || { echo "Error: Docker still not working after Colima restart"; exit 1; }; \
		else \
			echo "Error: Docker daemon is not running."; \
			echo "Try one of these:"; \
			echo "  - Docker Desktop: Open Docker.app"; \
			echo "  - Colima: Run 'colima start' or 'colima restart'"; \
			echo "  - Rancher Desktop: Run 'rdctl start'"; \
			exit 1; \
		fi \
	fi
	@echo "✓ Docker is installed and running"


up: check
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file - please add your OpenAI API key"; fi
	docker compose up -d
	@echo ""
	@PORT=$$(grep -E '^SOLSTICE_GATEWAY_PORT=' .env 2>/dev/null | cut -d= -f2 || echo "8000"); \
	echo "Gateway running at http://localhost:$$PORT"; \
	echo "Test with: curl http://localhost:$$PORT/health"


down:
	docker compose down

logs:
	docker compose logs -f gateway

lint:
	ruff check .
	mypy .

format:
	black .
	ruff check --fix .



shell:
	docker compose exec gateway /bin/bash


restart:
	docker compose restart gateway
	make logs

docker-status:
	@echo "=== Docker Runtime Status ==="
	@if command -v colima >/dev/null 2>&1; then \
		echo "Colima: $$(colima status 2>&1 | grep -E '(running|stopped)' | head -1 || echo 'not installed')"; \
	fi
	@if pgrep -x "Docker Desktop" >/dev/null 2>&1; then \
		echo "Docker Desktop: running"; \
	else \
		echo "Docker Desktop: not running"; \
	fi
	@echo ""
	@echo "Active context: $$(docker context show 2>/dev/null || echo 'unknown')"
	@echo "Docker daemon: $$(docker info >/dev/null 2>&1 && echo 'accessible ✓' || echo 'not accessible ✗')"

install:
	@echo "Installing solstice package..."
	@echo "Checking Python version..."
	@PYTHON_VERSION=$$(python --version 2>&1 | awk '{print $$2}'); \
	if [ "$$PYTHON_VERSION" != "3.11.9" ]; then \
		echo "❌ Error: Python 3.11.9 required (found $$PYTHON_VERSION)"; \
		echo ""; \
		echo "To fix this:"; \
		echo "1. Install pyenv: https://github.com/pyenv/pyenv#installation"; \
		echo "2. Install Python 3.11.9: pyenv install 3.11.9"; \
		echo "3. Return to this directory - pyenv will auto-activate 3.11.9"; \
		echo ""; \
		echo "The .python-version file in this project specifies Python 3.11.9"; \
		exit 1; \
	fi
	@echo "✓ Python version $$PYTHON_VERSION is compatible"
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "⚠️  Warning: No virtual environment detected"; \
		echo "   Recommended: python3 -m venv venv && source venv/bin/activate"; \
		echo ""; \
	fi
	@echo "Updating pip and build tools..."
	@pip install --upgrade pip wheel setuptools
	pip install -c requirements-constraints.txt -e .
	@echo "✓ Package installed successfully"

install-detectron2: install
	@echo "Setting up Detectron2 for layout parser..."
	@command -v pdfinfo >/dev/null 2>&1 || \
		{ echo "Warning: Poppler not installed. PDF processing will fail."; \
		  echo "Install with:"; \
		  echo "  macOS: brew install poppler"; \
		  echo "  Linux: sudo apt-get install poppler-utils"; }
	@echo "Running robust installation script..."
	@bash scripts/install-detectron2.sh

verify:
	@echo "Verifying installation..."
	@python -c "import fact_check" 2>/dev/null && echo "✓ fact_check package installed" || echo "✗ fact_check package not found (run: make install)"
	@python -c "import gateway" 2>/dev/null && echo "✓ gateway package installed" || echo "✗ gateway package not found"
	@python -c "import openai" 2>/dev/null && echo "✓ OpenAI library installed" || echo "✗ OpenAI library not found"
	@python -c "import layoutparser" 2>/dev/null && echo "✓ LayoutParser installed" || echo "✗ LayoutParser not found (run: make install-detectron2)"
	@command -v pdfinfo >/dev/null 2>&1 && echo "✓ Poppler installed" || echo "✗ Poppler not found (PDF processing will fail)"
	@echo ""
	@echo "Python: $$(python --version)"
	@echo "Pip:    $$(pip --version)"

# Build technical documentation
.PHONY: writeup
writeup:
	@echo "Building Solstice technical documentation..."
	@mkdir -p docs/writeup/build
	@cd docs/writeup && pdflatex -interaction=nonstopmode -output-directory=build src/solstice.tex
	@cp docs/writeup/build/solstice.pdf docs/writeup/solstice.pdf
	@echo "✓ PDF generated: docs/writeup/solstice.pdf"
