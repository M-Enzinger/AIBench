# Frontend build stage
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Backend stage
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY --from=frontend /frontend/dist ./static

ENV AIBENCH_DB_PATH=/app/data/aibench.db
RUN mkdir -p /app/data

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "2222"]
