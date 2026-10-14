"""FastAPI adapter for the legal-reference detector."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Callable

from fastapi import FastAPI
from pydantic import BaseModel

from law_links.application import LegalReferenceDetector, build_detector


class LawLink(BaseModel):
    law_id: int | None = None
    article: str | None = None
    point_article: str | None = None
    subpoint_article: str | None = None


class LinksResponse(BaseModel):
    links: list[LawLink]


class TextRequest(BaseModel):
    text: str


def create_app(detector_factory: Callable[[], LegalReferenceDetector] = build_detector) -> FastAPI:
    """Create the HTTP adapter and initialize recognition resources at startup."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        detector = detector_factory()
        app.state.detector = detector
        # Keep the stage objects available to evaluation and diagnostic tooling.
        app.state.reference_analyzer = detector.reference_analyzer
        app.state.semantic_analyzer = detector.semantic_analyzer
        app.state.contextual_resolver = detector.contextual_resolver
        yield

    app = FastAPI(
        title="Law Links Service",
        description="Сервис для выделения юридических ссылок из текста",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.post("/detect", response_model=LinksResponse)
    async def detect(data: TextRequest) -> LinksResponse:
        links = app.state.detector.detect(data.text)
        return LinksResponse(links=[LawLink(**asdict(link)) for link in links])

    @app.get("/health")
    async def health_check():
        """Return the service health status."""
        return {"status": "healthy"}

    return app
