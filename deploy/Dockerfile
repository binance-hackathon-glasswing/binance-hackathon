# Official Python 3.12.15 slim-bookworm multi-platform digest, resolved 2026-10-10.
FROM python:3.12.15-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY deploy/requirements-runtime.lock /app/deploy/requirements-runtime.lock
RUN pip install --no-cache-dir -r deploy/requirements-runtime.lock && pip check
COPY larp /app/larp
COPY migrations /app/migrations
RUN useradd --system --uid 10001 --no-create-home larp
USER 10001
# Inspection-only default, no database, model or signing process starts implicitly.
CMD ["python", "-c", "from larp.contracts import Document; print('LARP offline runtime image; activation is not configured')"]
