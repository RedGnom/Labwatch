FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir pyyaml

COPY app /app/app
COPY config /app/config

CMD ["python", "-m", "app.main"]