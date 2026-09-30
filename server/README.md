# LabWatch — сервер

Принимает телеметрию от узлов и отдаёт её мобильному приложению.

## Запуск

    cp .env.example .env
    docker compose up --build

Сервер будет доступен на `http://localhost:8000` (или на IP машины, если
она в сети — порт слушается на 0.0.0.0).

Swagger: http://localhost:8000/docs

## Проверка

    curl http://localhost:8000/health
    # {"status":"ok"}

## Смена порта

Поменять `SERVER_PORT` в `.env`, перезапустить `docker compose up -d`.