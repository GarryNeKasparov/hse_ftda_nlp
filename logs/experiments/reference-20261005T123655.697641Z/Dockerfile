FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY reference_parser.py .
COPY law_link_mapper.py .
COPY docs/reference-grammar.bnf docs/reference-grammar.bnf
COPY law_aliases.json .

EXPOSE 8978

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8978"]
