# Lekki obraz z Pythonem — wszystkie zależności są darmowe (PyPI).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    LOG_DIR=/logs

WORKDIR /app

# Użytkownik bez uprawnień roota; katalogi /data i /logs należą do niego,
# więc nazwane volume'y dostaną poprawnego właściciela przy pierwszym montowaniu.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data /logs \
    && chown app:app /data /logs

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY scraper ./scraper

USER app

# /data: cookies.json + last_scan.json, /logs: logi skrapera i API.
VOLUME ["/data", "/logs"]
EXPOSE 5000

# Domyślnie: skraper w pętli. API uruchamia docker-compose osobnym poleceniem.
CMD ["python", "-m", "scraper.runner", "--loop"]
