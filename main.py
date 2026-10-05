from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from law_link_mapper import map_semantic_analysis
from reference_parser import ReferenceAnalyzer
from semantic_analyzer import SemanticAnalyzer


class LawLink(BaseModel):
    law_id: Optional[int] = None
    article: Optional[str] = None
    point_article: Optional[str] = None
    subpoint_article: Optional[str] = None


class LinksResponse(BaseModel):
    links: List[LawLink]


class TextRequest(BaseModel):
    text: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    aliases_path = Path(__file__).resolve().parent / "law_aliases.json"
    app.state.reference_analyzer = ReferenceAnalyzer.from_alias_file(aliases_path)
    app.state.semantic_analyzer = SemanticAnalyzer()
    yield


app = FastAPI(
    title="Law Links Service",
    description="Cервис для выделения юридических ссылок из текста",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/detect")
async def get_law_links(data: TextRequest) -> LinksResponse:
    """
    Принимает текст и возвращает список юридических ссылок
    """
    analysis = app.state.reference_analyzer.analyze(data.text)
    semantic = app.state.semantic_analyzer.analyze(analysis)
    mapped = map_semantic_analysis(semantic)
    return LinksResponse(links=[LawLink(**asdict(item)) for item in mapped.links])


@app.get("/health")
async def health_check():
    """
    Проверка состояния сервиса
    """
    return {"status": "healthy"}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8978)
