FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy fix-core first so the relative path in requirements.txt resolves
COPY fix-core ./fix-core

# Copy backend and install dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN cd backend && pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

COPY backend ./backend

WORKDIR /app/backend

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
