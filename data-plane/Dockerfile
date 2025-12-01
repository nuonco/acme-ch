# Use Python 3.13 slim image for smaller size
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY *.py ./
COPY services/ ./services/

# Copy templates directory
COPY templates/ ./templates/

# Set default environment variables (override these at runtime)
ENV ACME_CH_API_URL="" \
    ACME_CH_API_TOKEN="" \
    ACME_CH_ORG_ID=""

# Run the application
CMD ["python", "main.py"]
