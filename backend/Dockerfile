FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/__init__.py /app/backend/__init__.py
COPY backend/*.py /app/backend/
COPY backend/routes /app/backend/routes
COPY backend/services /app/backend/services
COPY backend/prompts /app/backend/prompts
COPY backend/tests /app/backend/tests

RUN pip install --upgrade pip && pip install /app/backend

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
