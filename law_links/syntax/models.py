"""Source-positioned syntax results shared by parsing and interpretation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LexicalCandidate:
    """A recognized token alternative with provenance in the original text."""

    kind: str
    value: str
    start: int
    end: int
    law_ids: tuple[int, ...] = ()
    evidence: tuple[str, ...] = ()
    matching_forms: tuple[str, ...] = ()


@dataclass(frozen=True)
class AstLeaf:
    """A terminal in a parsed alternative, retaining its original span."""

    kind: str
    value: str
    start: int
    end: int
    law_ids: tuple[int, ...] = ()
    law_status: str | None = None
    evidence: tuple[str, ...] = ()
    matching_forms: tuple[str, ...] = ()


@dataclass(frozen=True)
class AstNode:
    """A grammar production with its ordered child nodes and source span."""

    kind: str | None
    value: str | None = None
    start: int = 0
    end: int = 0
    children: tuple[AstNode | AstLeaf, ...] = ()
    law_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class Diagnostic:
    """A candidate-local issue retained for review and later resolution."""

    code: str
    start: int
    end: int


@dataclass(frozen=True)
class CandidateSpan:
    """A source span and every grammar interpretation found for that span."""

    start: int
    end: int
    alternatives: tuple[AstNode, ...]
    complete: bool = True
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class Analysis:
    """The lexical candidates, parsed spans, and diagnostics for one text."""

    lexical_candidates: tuple[LexicalCandidate, ...]
    candidates: tuple[CandidateSpan, ...]
    diagnostics: tuple[Diagnostic, ...]
