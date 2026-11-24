FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN addgroup --system lancast && adduser --system --ingroup lancast lancast

COPY pyproject.toml ./
COPY dispatcher ./dispatcher
RUN pip install --upgrade pip && pip install .

USER lancast
CMD ["python", "-m", "dispatcher.worker"]
