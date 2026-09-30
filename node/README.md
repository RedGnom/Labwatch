# LabWatch — узел (агент)

Собирает телеметрию и отправляет её на сервер LabWatch.

## Запуск (разработка, всё на одном ПК)

    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -e .

    cp .env.example .env               # оставить localhost
    python -m node.main

## Переезд на разные устройства

1. На серверном ноутбуке узнать IP:
   - Linux/Mac: `ip a`
   - Windows: `ipconfig`
2. В `node/.env` поменять **одну строку**: