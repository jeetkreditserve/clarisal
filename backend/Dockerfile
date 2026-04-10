FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

ARG INSTALL_DEV_REQUIREMENTS=false
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_DEV_REQUIREMENTS" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

RUN addgroup --system app && adduser --system --group app
RUN mkdir -p /app/staticfiles /app/media && chown -R app:app /app
USER app

COPY --chown=app:app . .

EXPOSE 8000

CMD ["gunicorn", "clarisal.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
