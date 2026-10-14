# Сервис извлечения юридических ссылок

FastAPI-сервис находит в русском тексте ссылки на статьи и другие положения
законов и возвращает их в формате `LawLink`. Распознавание использует грамматику
и словарь вариантов названий законов.

## Запуск

Установите зависимости проекта и запустите приложение:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Сервис будет доступен на `http://localhost:8978`. Документация OpenAPI находится
по адресу `http://localhost:8978/docs`.

## API

Отправьте текст на `POST /detect`:

```bash
curl -X POST http://localhost:8978/detect \
  -H 'Content-Type: application/json' \
  -d '{"text":"пп. 1 п. 1 ст. 374 НК РФ"}'
```

Ответ содержит одну запись на каждое распознанное положение:

```json
{
  "links": [
    {
      "law_id": 15,
      "article": "374",
      "point_article": "1",
      "subpoint_article": "1"
    }
  ]
}
```

`GET /health` возвращает состояние сервиса. Если закон не удалось определить,
`law_id` будет `null`; отсутствующие уровни ссылки также представлены как
`null`.

## Docker

Соберите и запустите контейнер:

```bash
docker build -t law-links-service .
docker run --rm -p 8978:8978 law-links-service
```

## Проверки

Запустите тесты и статическую проверку файлов Docker-образа:

```bash
.venv/bin/python -m pytest -p no:cacheprovider tests
.venv/bin/python tools/check_docker_contract.py
```

## Структура

- `law_links/syntax/` — лексические кандидаты, грамматика и синтаксические модели.
- `law_links/semantic.py`, `context.py`, `projection.py` — интерпретация, контекст и формат `LawLink`.
- `law_links/application.py` и `http.py` — сборка конвейера и FastAPI-адаптер.
- `law_links/resources/` — грамматика; `data/law_aliases.json` — словарь законов.
- `tests/` и `data/golden_*.jsonl` — регрессионные тесты и размеченные примеры.
