FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/storage

EXPOSE 2222

ENV PORT=2222
ENTRYPOINT ["/app/entrypoint.sh"]
