FROM python:3.11-slim

WORKDIR /app

# Copy application first (needed for pip install with pyproject.toml)
COPY pyproject.toml .
COPY app/ ./app/

# Copy alembic for migrations
COPY alembic.ini .
COPY alembic/ ./alembic/

# Install dependencies
RUN pip install --no-cache-dir .

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
