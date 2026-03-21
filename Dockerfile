FROM python:3.11-slim

# Asenna Node.js frontendin buildia varten
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Backend-riippuvuudet
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Frontend build
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build

# Kopioi backend + frontendin build
COPY backend/ ./backend/
RUN cp -r frontend/dist backend/static

WORKDIR /app/backend

ENV DATABASE_URL=sqlite:///./cot_data.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
