FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY law_links/ law_links/
COPY data/law_aliases.json data/law_aliases.json

EXPOSE 8978

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8978"]
