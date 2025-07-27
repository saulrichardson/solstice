FROM python:3.11-slim

WORKDIR /app

# Copy project files for dependency installation
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir -e .

# Expose port (actual port comes from environment)
EXPOSE ${SOLSTICE_GATEWAY_PORT:-4000}

# Run with uvicorn - port from environment
CMD uvicorn fact_check.gateway.app.main:app --host 0.0.0.0 --port ${SOLSTICE_GATEWAY_PORT:-4000} --reload