# Сервис извлечения юридических ссылок

Сервис находит в русском тексте ссылки на статьи и другие положения законов и
возвращает их в формате `LawLink`. Он использует грамматику ссылок и словарь
вариантов названий законов.

## Установка и запуск локально

Получите проект:

```bash
git clone --branch homework_1 https://github.com/GarryNeKasparov/hse_ftda_nlp.git
cd hse_ftda_nlp
```

Создайте виртуальное окружение и установите зависимости приложения:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Запустите сервер:

```bash
.venv/bin/python main.py
```

Сервер доступен по адресу `http://127.0.0.1:8978`, интерактивная документация
API — по адресу `http://127.0.0.1:8978/docs`.

Проверка состояния:

```bash
curl http://127.0.0.1:8978/health
```

При успешном запуске сервис вернёт:

```json
{"status":"healthy"}
```

## Проверка распознавания

Отправьте текст на `POST /detect`. Например:

```bash
curl -X POST http://127.0.0.1:8978/detect \
  -H 'Content-Type: application/json' \
  -d '{"text":"В соответствии с пп. 1 п. 1 ст. 374 НК РФ организация признаётся плательщиком налога на имущество. Это правило применяется к указанным в статье объектам."}'
```

Ответ содержит найденные положения закона:

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

Если закон не удалось определить, `law_id` будет `null`. Отсутствующие уровни
ссылки также представлены как `null`.

## Запуск тестов

Установите тестовые зависимости и запустите проверки:

```bash
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -p no:cacheprovider tests
.venv/bin/python tools/check_docker_contract.py
```

Последняя команда проверяет, что Dockerfile копирует необходимые файлы и
открывает нужный порт.

## Запуск через Docker

Соберите образ:

```bash
docker build -t law-links-service .
```

Запустите контейнер:

```bash
docker run --rm --name law-links-service -p 8978:8978 law-links-service
```

Проверить контейнер можно запросами к `/health` и `/detect`, приведёнными выше.

## Структура проекта

- `law_links/syntax/` — лексический и синтаксический анализ, модели разбора и
  грамматика;
- `law_links/semantic.py`, `context.py`, `projection.py` — интерпретация ссылки,
  разрешение контекста и подготовка результата;
- `law_links/application.py` и `http.py` — сборка анализатора и HTTP API;
- `law_links/resources/reference-grammar.bnf` — грамматика;
- `data/law_aliases.json` — словарь названий и сокращений законов;
- `tests/` — проверки корректности и регрессии.
