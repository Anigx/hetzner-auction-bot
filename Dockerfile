FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --uid 10001 --create-home bot \
    && mkdir -p /app/data \
    && chown -R bot:bot /app
USER bot

CMD ["python", "bot.py"]
