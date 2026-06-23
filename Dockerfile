FROM python:3.13-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY adp ./adp
COPY eval ./eval
COPY transform ./transform
RUN pip install --no-cache-dir .

# dbt project lives outside the installed package; point the runner at it.
ENV ADP_DBT_DIR=/app/transform

EXPOSE 8000
# scale-to-zero friendly; bind all interfaces for container/cloud runtimes.
CMD ["uvicorn", "adp.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
