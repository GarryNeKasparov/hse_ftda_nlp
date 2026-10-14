"""Extract legal-reference candidates with source spans and parse alternatives."""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from bisect import bisect_left
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Iterable, Mapping, Sequence

from lark import Token, Tree
from lark.exceptions import UnexpectedInput, UnexpectedToken
from pymorphy3 import MorphAnalyzer
from rapidfuzz.distance import Levenshtein

from law_links.syntax.grammar import (create_parser, expand_trees, materialize_shape,
                                      tree_to_ast)
from law_links.syntax.models import (Analysis, AstLeaf, AstNode, CandidateSpan,
                                     Diagnostic, LexicalCandidate)
from law_links.syntax.numbers import NumberNormalizer

_TOKEN_RE = re.compile(
    r"[^\W\d_](?:\.\d+)+(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?"
    r"|\d+(?:\.\d+)*(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?"
    r"|[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])*"
    r"|[^\w\s]",
    re.UNICODE,
)
_INTEGER_ID_RE = re.compile(r"\d+(?:\.\d+)*(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?\Z")
_COMPOUND_ID_RE = re.compile(r"[^\W\d_](?:\.\d+)+(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?\Z", re.UNICODE)
_HYPHEN_ID_RE = re.compile(r"\d+(?:\.\d+)*-\d+(?:\.\d+)*(?:[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?\Z")
_MARKER_LEMMAS = {
    "статья": "ARTICLE",
    "часть": "PART",
    "пункт": "POINT",
    "подпункт": "SUBPOINT",
    "абзац": "PARAGRAPH",
}
_SHORT_MARKERS = {
    "ст": ("ARTICLE",), "ст.": ("ARTICLE",),
    "ч": ("PART",), "ч.": ("PART",),
    "п": ("POINT",), "п.": ("POINT",),
    "подп": ("SUBPOINT",), "подп.": ("SUBPOINT",),
    "пп": ("PP",), "пп.": ("PP",),
    "абз": ("PARAGRAPH",), "абз.": ("PARAGRAPH",),
}
_WORD_CONJUNCTIONS = {"и": "AND", "или": "OR"}
_RANGE_MARKERS = {"-", "–", "—"}
_QUOTE_MARKS = {"\"", "«", "»", "“", "”", "„", "‟", "\u201e", "\u201c", "\u201d"}
_LOOKALIKE_LETTERS = "ckaeopxymtbh"
_LOOKALIKE_TRANSLATION = str.maketrans({"c": "с", "k": "к", "a": "а", "e": "е",
                                        "o": "о", "p": "р", "x": "х", "y": "у",
                                        "m": "м", "t": "т", "b": "в", "h": "н"})


@dataclass(frozen=True)
class _RawToken:
    """A whitespace-free primitive token whose offsets refer to the input."""

    value: str
    start: int
    end: int


@dataclass(frozen=True)
class _Edge:
    """One possible lexical token spanning one or more primitive tokens."""

    token: LexicalCandidate
    first: int
    after: int


@dataclass(frozen=True)
class _FullLawAlias:
    """A sufficiently long law-name alias available to bounded typo matching."""

    forms: tuple[frozenset[str], ...]
    surface: str
    law_ids: tuple[int, ...]


@dataclass
class _FuzzyFormIndexNode:
    """A BK-tree node mapping a normalized token form to alias positions."""

    form: str
    alias_positions: set[int]
    children: dict[int, _FuzzyFormIndexNode]


_ParseShape = tuple[str, int | str, tuple["_ParseShape", ...]]
_PARSE_CACHE_MAXSIZE = 4096
_FUZZY_FORM_CACHE_MAXSIZE = 32768
_INVALID_PARSE_PREFIX = object()


class ReferenceAnalyzer:
    """Analyze source text into candidate spans and correlated parse alternatives."""

    def __init__(self, law_aliases: Mapping[str, Sequence[str]], morphology: MorphAnalyzer | None = None):
        self._morphology = morphology or MorphAnalyzer()
        self._numbers = NumberNormalizer(self._morphology)
        self._alias_trie: dict = {}
        self._alias_form_dispatch: dict[int, dict[str, frozenset[frozenset[str]]]] = {}
        self._alias_compact_nodes: set[int] = set()
        self._alias_dispatch_root: int | None = None
        self._fuzzy_aliases: dict[int, list[_FullLawAlias]] = defaultdict(list)
        self._fuzzy_form_indexes: dict[int, tuple[_FuzzyFormIndexNode | None, ...]] = {}
        self._fuzzy_first_index: _FuzzyFormIndexNode | None = None
        self._fuzzy_form_cache: OrderedDict[
            tuple[int, int, tuple[str, ...]], frozenset[int]
        ] = OrderedDict()
        self._fuzzy_cache_hits = 0
        self._fuzzy_cache_misses = 0
        self._fuzzy_aliases_checked = 0
        self._max_fuzzy_alias_chars = 0
        self._marker_forms: dict[str, str] = {}
        self._singular_marker_forms: set[str] = set()
        self._plural_marker_forms: set[str] = set()
        self._fuzzy_marker_forms: tuple[tuple[str, str], ...] = ()
        self._fuzzy_marker_deletions: dict[str, frozenset[tuple[str, str]]] = {}
        self._build_marker_index()
        self._build_alias_index(law_aliases)
        self._parser = create_parser()
        self._parse_shapes: OrderedDict[tuple[str, ...], _ParseShape | None | object] = OrderedDict()
        self._parse_cache_hits = 0
        self._parse_cache_misses = 0

    @property
    def parse_cache_info(self) -> dict[str, int]:
        """Return bounded grammar-shape cache counters for profiling."""
        return {"hits": self._parse_cache_hits, "misses": self._parse_cache_misses,
                "size": len(self._parse_shapes), "maxsize": _PARSE_CACHE_MAXSIZE,
                "failures": sum(shape is None or shape is _INVALID_PARSE_PREFIX
                                for shape in self._parse_shapes.values())}

    @property
    def fuzzy_cache_info(self) -> dict[str, int]:
        """Return bounded fuzzy-form lookup counters for profiling."""
        return {"hits": self._fuzzy_cache_hits, "misses": self._fuzzy_cache_misses,
                "size": len(self._fuzzy_form_cache), "maxsize": _FUZZY_FORM_CACHE_MAXSIZE,
                "aliases_checked": self._fuzzy_aliases_checked}

    def _build_fuzzy_form_indexes(self) -> None:
        """Build one BK-tree per token position and alias token count."""
        indexes = {}
        first_forms: dict[str, set[int]] = defaultdict(set)
        for token_count, aliases in self._fuzzy_aliases.items():
            roots: list[_FuzzyFormIndexNode | None] = [None] * token_count
            forms_by_position: list[dict[str, set[int]]] = [
                defaultdict(set) for _ in range(token_count)
            ]
            for alias_position, alias in enumerate(aliases):
                for form in alias.forms[0]:
                    first_forms[form].add(token_count)
                for token_position, forms in enumerate(alias.forms):
                    for form in forms:
                        forms_by_position[token_position][form].add(alias_position)

            for token_position, forms in enumerate(forms_by_position):
                root = None
                for form, alias_positions in forms.items():
                    if root is None:
                        root = _FuzzyFormIndexNode(form, alias_positions, {})
                        continue
                    node = root
                    while True:
                        distance = Levenshtein.distance(form, node.form)
                        child = node.children.get(distance)
                        if child is None:
                            node.children[distance] = _FuzzyFormIndexNode(
                                form, alias_positions, {})
                            break
                        node = child
                roots[token_position] = root
            indexes[token_count] = tuple(roots)
        self._fuzzy_form_indexes = indexes
        first_root = None
        for form, token_counts in first_forms.items():
            if first_root is None:
                first_root = _FuzzyFormIndexNode(form, token_counts, {})
                continue
            node = first_root
            while True:
                distance = Levenshtein.distance(form, node.form)
                child = node.children.get(distance)
                if child is None:
                    node.children[distance] = _FuzzyFormIndexNode(form, token_counts, {})
                    break
                node = child
        self._fuzzy_first_index = first_root
        self._fuzzy_first_alias_lengths.cache_clear()
        self._fuzzy_form_cache.clear()
        self._fuzzy_cache_hits = 0
        self._fuzzy_cache_misses = 0
        self._fuzzy_aliases_checked = 0

    @lru_cache(maxsize=32768)
    def _fuzzy_first_alias_lengths(self, source_forms: tuple[str, ...]) -> frozenset[int]:
        """Find possible alias lengths from the first source word alone."""
        root = self._fuzzy_first_index
        if root is None:
            return frozenset()
        lengths = set()
        for source_form in source_forms:
            pending = [root]
            while pending:
                node = pending.pop()
                distance = Levenshtein.distance(source_form, node.form)
                if distance <= 2:
                    lengths.update(node.alias_positions)
                lower, upper = distance - 2, distance + 2
                pending.extend(child for edge, child in node.children.items()
                               if lower <= edge <= upper)
        return frozenset(lengths)

    def _fuzzy_form_alias_candidates(self, token_count: int, token_position: int,
                                     source_forms: tuple[str, ...]) -> frozenset[int]:
        """Find aliases with a token form no more than two edits from the source."""
        key = (token_count, token_position, source_forms)
        if key in self._fuzzy_form_cache:
            self._fuzzy_cache_hits += 1
            candidates = self._fuzzy_form_cache.pop(key)
            self._fuzzy_form_cache[key] = candidates
            return candidates

        self._fuzzy_cache_misses += 1
        roots = self._fuzzy_form_indexes.get(token_count, ())
        root = roots[token_position] if token_position < len(roots) else None
        candidates: set[int] = set()
        if root is not None:
            for source_form in source_forms:
                pending = [root]
                while pending:
                    node = pending.pop()
                    distance = Levenshtein.distance(source_form, node.form)
                    if distance <= 2:
                        candidates.update(node.alias_positions)
                    lower, upper = distance - 2, distance + 2
                    pending.extend(child for edge, child in node.children.items()
                                   if lower <= edge <= upper)
        result = frozenset(candidates)
        self._fuzzy_form_cache[key] = result
        if len(self._fuzzy_form_cache) > _FUZZY_FORM_CACHE_MAXSIZE:
            self._fuzzy_form_cache.popitem(last=False)
        return result

    def _parse_shape(self, path, *, materialize=True):
        """Return a cached grammar shape, optionally binding its terminals."""
        key = tuple(item.kind for item in path)
        if key in self._parse_shapes:
            self._parse_cache_hits += 1
            shape = self._parse_shapes.pop(key)
            self._parse_shapes[key] = shape
        else:
            self._parse_cache_misses += 1
            try:
                parsed = self._parser.parse(path)
            except UnexpectedToken:
                # The grammar cannot accept this prefix with any continuation.
                shape = _INVALID_PARSE_PREFIX
            except UnexpectedInput:
                shape = None
            else:
                token_positions = {
                    (item.kind, item.start, item.end, item.value): index
                    for index, item in enumerate(path)
                }

                def encode(tree):
                    if isinstance(tree, Token):
                        token_key = (tree.type, tree.start_pos or 0, tree.end_pos or 0,
                                     str(tree))
                        return ("token", token_positions[token_key], ())
                    return ("tree", str(tree.data),
                            tuple(encode(child) for child in tree.children))

                shape = encode(parsed)
            self._parse_shapes[key] = shape
            if len(self._parse_shapes) > _PARSE_CACHE_MAXSIZE:
                self._parse_shapes.popitem(last=False)
        if shape is None or shape is _INVALID_PARSE_PREFIX or not materialize:
            return shape

        return materialize_shape(shape, path)

    @classmethod
    def from_alias_file(cls, path: str | Path) -> ReferenceAnalyzer:
        """Load the assignment's law-alias JSON and build a reusable analyzer."""
        aliases = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(aliases)

    def analyze(self, text: str) -> Analysis:
        """Return all recognized token candidates, candidate spans, and parse alternatives."""
        return self._analyze(text, selected_only=False)

    def analyze_for_service(self, text: str) -> Analysis:
        """Retain the candidate spans used by semantic selection in /detect."""
        return self._analyze(text, selected_only=True)

    def _analyze(self, text: str, selected_only: bool) -> Analysis:
        raw_tokens = self._tokenize(text)
        edges = self._recognize_edges(raw_tokens, text)
        candidates, diagnostics = self._parse_candidates(
            raw_tokens, edges, text, selected_only=selected_only)
        lexical = tuple(sorted({edge.token for outgoing in edges.values() for edge in outgoing},
                               key=lambda token: (token.start, token.end, token.kind, token.value)))
        return Analysis(lexical, tuple(candidates), tuple(diagnostics))

    @staticmethod
    def _matching_form(value: str) -> str:
        """Normalize a lexeme for dictionary matching while retaining source spelling."""
        normalized = unicodedata.normalize("NFC", value).casefold()
        return "QUOTE" if normalized in _QUOTE_MARKS else normalized

    @lru_cache(maxsize=32768)
    def _word_forms(self, value: str) -> frozenset[str]:
        """Return the literal and every morphological lemma candidate for a word."""
        literal = self._matching_form(value)
        if not any(character.isalpha() for character in value):
            return frozenset((literal,))
        forms = {literal, literal.replace("ё", "е")}
        for parse in self._morphology.parse(value):
            lemma = self._matching_form(parse.normal_form)
            forms.update((lemma, lemma.replace("ё", "е")))
        return frozenset(forms)

    def _build_marker_index(self) -> None:
        """Index hierarchy marker inflections and short exact abbreviations."""
        self._marker_forms.update({key: kind for key, kinds in _SHORT_MARKERS.items()
                                   for kind in kinds})
        fuzzy_forms = []
        for lemma, kind in _MARKER_LEMMAS.items():
            for parse in self._morphology.parse(lemma):
                if parse.normal_form != lemma:
                    continue
                for inflected in parse.lexeme:
                    form = self._matching_form(inflected.word)
                    # Treat ё/е spellings as equivalent during marker lookup,
                    # while retaining the original source form on each edge.
                    matching_forms = {form, form.replace("ё", "е")}
                    for matching_form in matching_forms:
                        self._marker_forms[matching_form] = kind
                        if inflected.tag.number == "sing":
                            self._singular_marker_forms.add(matching_form)
                        elif inflected.tag.number == "plur":
                            self._plural_marker_forms.add(matching_form)
                        if len(matching_form) >= 4:
                            fuzzy_forms.append((matching_form, kind))
        self._fuzzy_marker_forms = tuple(sorted(set(fuzzy_forms)))
        deletions: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for form, kind in self._fuzzy_marker_forms:
            candidate = (form, kind)
            deletions[form].add(candidate)
            for index in range(len(form)):
                deletions[form[:index] + form[index + 1:]].add(candidate)
        self._fuzzy_marker_deletions = {
            deletion: frozenset(candidates)
            for deletion, candidates in deletions.items()
        }
        self._fuzzy_marker_kinds.cache_clear()

    @lru_cache(maxsize=32768)
    def _fuzzy_marker_kinds(self, word: str) -> frozenset[str]:
        """Return all marker kinds within one edit using deletion-index candidates."""
        keys = {word}
        keys.update(word[:index] + word[index + 1:] for index in range(len(word)))
        candidates = {candidate for key in keys
                      for candidate in self._fuzzy_marker_deletions.get(key, ())}
        return frozenset(
            kind for form, kind in candidates
            if not (len(word) > len(form) and word.endswith(form))
            and Levenshtein.distance(word, form, score_cutoff=1) <= 1
        )

    def _build_alias_index(self, law_aliases: Mapping[str, Sequence[str]]) -> None:
        """Build a morphology-aware trie retaining every ID for each alias."""
        seen: set[tuple[str, int]] = set()
        fuzzy_records: dict[str, tuple[tuple[frozenset[str], ...], set[int]]] = {}
        for raw_id, aliases in law_aliases.items():
            law_id = int(raw_id)
            for alias in aliases:
                key = (self._matching_form(alias), law_id)
                if key in seen:
                    continue
                seen.add(key)
                pieces = self._tokenize(alias)
                node = self._alias_trie
                for piece in pieces:
                    forms = self._alias_forms(piece.value)
                    child = node.setdefault(forms, {})
                    node = child
                node.setdefault(None, set()).add(law_id)
                surface = " ".join(self._matching_form(piece.value) for piece in pieces)
                if len(surface) >= 20 and sum(any(char.isalpha() for char in piece.value)
                                               for piece in pieces) >= 2:
                    forms = tuple(self._word_forms(piece.value) for piece in pieces)
                    existing = fuzzy_records.setdefault(surface, (forms, set()))
                    existing[1].add(law_id)
        for surface, (forms, law_ids) in fuzzy_records.items():
            alias = _FullLawAlias(forms, surface, tuple(sorted(law_ids)))
            self._fuzzy_aliases[len(forms)].append(alias)
            self._max_fuzzy_alias_chars = max(self._max_fuzzy_alias_chars, len(surface))
        self._build_alias_dispatch()
        self._build_fuzzy_form_indexes()

    def _build_alias_dispatch(self) -> None:
        """Index each trie node's outgoing forms for direct and dirty lookup."""
        self._alias_form_dispatch.clear()
        self._alias_compact_nodes.clear()
        pending = [self._alias_trie]
        while pending:
            node = pending.pop()
            by_form: dict[str, set[frozenset[str]]] = defaultdict(set)
            for expected, child in node.items():
                if expected is None:
                    continue
                for form in expected:
                    by_form[form].add(expected)
                    if form.isalpha() and 2 <= len(form) <= 6:
                        self._alias_compact_nodes.add(id(node))
                pending.append(child)
            self._alias_form_dispatch[id(node)] = {
                form: frozenset(keys) for form, keys in by_form.items()
            }
        self._alias_dispatch_root = id(self._alias_trie)

    @staticmethod
    def _tokenize(text: str) -> tuple[_RawToken, ...]:
        """Split text into Unicode words and punctuation while retaining offsets."""
        return tuple(_RawToken(match.group(), match.start(), match.end())
                     for match in _TOKEN_RE.finditer(text))

    def _recognize_edges(self, raw: tuple[_RawToken, ...], text: str) -> dict[int, list[_Edge]]:
        """Recognize hierarchy markers, identifiers, conjunctions, and law aliases."""
        if self._alias_dispatch_root != id(self._alias_trie):
            self._build_alias_dispatch()
        edges: dict[int, list[_Edge]] = defaultdict(list)
        by_span: dict[tuple[int, int, str, str], set[int]] = defaultdict(set)
        fuzzy_starts = []
        unknown_law_spans: list[tuple[int, int]] = []
        compound_conjunction_tokens: set[int] = set()
        dirty_alias_ends: dict[int, dict[str, tuple[int, ...]]] = {}

        def add(first: int, after: int, kind: str, law_ids: Iterable[int] = (),
                evidence: str = "", token_value: str | None = None):
            source = text[raw[first].start:raw[after - 1].end]
            forms = tuple(sorted({f"{position - first}:{form}"
                                  for position in range(first, after)
                                  for form in self._word_forms(raw[position].value)}))
            candidate = LexicalCandidate(kind, token_value if token_value is not None else source,
                                         raw[first].start, raw[after - 1].end,
                                         tuple(sorted(set(law_ids))), (evidence,) if evidence else (),
                                         forms)
            edges[first].append(_Edge(candidate, first, after))

        def dirty_forms(cursor: int) -> dict[str, tuple[int, ...]]:
            """Join short split spellings once per source position."""
            by_form = dirty_alias_ends.get(cursor)
            if by_form is None:
                ends_by_form: dict[str, list[int]] = defaultdict(list)
                joined = ""
                fragments = 0
                for index in range(cursor, len(raw)):
                    value = raw[index].value
                    if value.isalpha():
                        joined += self._matching_form(value)
                        fragments += 1
                        if fragments >= 2 and len(joined) <= 6:
                            ends_by_form[joined].append(index + 1)
                        if len(joined) > 6:
                            break
                    elif value.isalnum():
                        break
                by_form = {form: tuple(ends) for form, ends in ends_by_form.items()}
                dirty_alias_ends[cursor] = by_form
            return by_form

        def alias_token_ends(expected: frozenset[str], cursor: int,
                             forms: frozenset[str],
                             by_form: dict[str, tuple[int, ...]]) -> tuple[int, ...]:
            """Match one alias word directly or across dirty splits."""
            if expected.intersection(forms):
                return (cursor + 1,)
            compact_forms = {form for form in expected
                             if form.isalpha() and 2 <= len(form) <= 6}
            return tuple(sorted({after for form in compact_forms
                                 for after in by_form.get(form, ())}))

        # Keep the parenthesized spelling as one lexical item. Whitespace may
        # occur around either parenthesis, but punctuation or prose may not.
        for index in range(len(raw) - 3):
            if (self._matching_form(raw[index].value) != "и"
                    or raw[index + 1].value != "("
                    or self._matching_form(raw[index + 2].value) != "или"
                    or raw[index + 3].value != ")"):
                continue
            if any(text[raw[position].end:raw[position + 1].start].strip()
                   for position in range(index, index + 3)):
                continue
            add(index, index + 4, "AND_OR")
            compound_conjunction_tokens.update(range(index, index + 4))

        def quoted_subpoint_context(opening: int, closing: int) -> bool:
            """Recognize a quoted letter after a subpoint marker or within its list."""
            if closing != opening + 2:
                return False
            letter = raw[opening + 1].value
            if not self._is_identifier(letter) or len(letter) != 1:
                return False

            cursor = opening
            while cursor >= 0:
                marker = cursor - 1
                if marker >= 0 and raw[marker].value == ".":
                    marker -= 1
                if marker >= 0 and any(
                        edge.token.kind in {"SUBPOINT", "PP"}
                        for edge in edges.get(marker, ())):
                    return True

                # A later quoted letter inherits the marker through a list of
                # one-letter quoted selectors joined by comma or conjunction.
                previous_close = cursor - 1
                if (previous_close >= 0
                        and (raw[previous_close].value == ","
                             or self._matching_form(raw[previous_close].value)
                             in _WORD_CONJUNCTIONS)):
                    previous_close -= 1
                if (previous_close < 2
                        or raw[previous_close].value not in _QUOTE_MARKS
                        or not self._is_identifier(raw[previous_close - 1].value)
                        or len(raw[previous_close - 1].value) != 1
                        or raw[previous_close - 2].value not in _QUOTE_MARKS):
                    return False
                cursor = previous_close - 2
            return False

        def comma_bridges_hierarchy(comma_index: int, higher_kind: str | None) -> bool:
            """Mark a comma as a level gap after a complete lower-level selector."""
            ranks = {"PARAGRAPH": 0, "SUBPOINT": 1, "PP": 1,
                     "POINT": 2, "PART": 3, "ARTICLE": 4}
            if higher_kind not in ranks:
                return False
            cursor = comma_index - 1
            saw_identifier = False
            while cursor >= 0:
                kinds = {item.token.kind for item in edges.get(cursor, ())}
                lower_kinds = kinds & ranks.keys()
                if lower_kinds:
                    return (saw_identifier and any(
                        ranks[kind] < ranks[higher_kind] for kind in lower_kinds))
                if kinds & {"ID", "ORDINAL"}:
                    saw_identifier = True
                elif kinds & {"COMMA", "AND", "OR", "AND_OR", "RANGE"}:
                    pass
                elif raw[cursor].value in _QUOTE_MARKS or raw[cursor].value == ".":
                    pass
                else:
                    return False
                cursor -= 1
            return False

        def ascii_hyphen_context(index: int) -> str:
            """Classify selector hyphens from their nearest hierarchy marker."""
            marker_kinds = {"ARTICLE", "PART", "POINT", "SUBPOINT", "PP", "PARAGRAPH"}
            for cursor in range(index - 1, -1, -1):
                kinds = {edge.token.kind for edge in edges.get(cursor, ())}
                if kinds & marker_kinds:
                    form = self._matching_form(raw[cursor].value)
                    is_article = "ARTICLE" in kinds
                    singular = form in self._singular_marker_forms
                    plural = form in self._plural_marker_forms
                    if singular and not plural:
                        return "singular_article" if is_article else "ambiguous"
                    if plural and not singular:
                        return "plural"
                    if singular and plural:
                        coordinated = (cursor >= 3
                                       and raw[cursor - 1].value in {",", "и", "или"}
                                       and self._is_identifier(raw[cursor - 2].value))
                        if coordinated:
                            ranks = {"PARAGRAPH": 0, "SUBPOINT": 1, "PP": 1,
                                     "POINT": 2, "PART": 3, "ARTICLE": 4}
                            current_rank = max(ranks[kind] for kind in kinds & ranks.keys())
                            for previous in range(cursor - 3, -1, -1):
                                previous_kinds = {edge.token.kind
                                                  for edge in edges.get(previous, ())}
                                previous_levels = previous_kinds & ranks.keys()
                                if previous_levels:
                                    if max(ranks[kind] for kind in previous_levels) < current_rank:
                                        break
                                    return "plural"
                            else:
                                return "plural"
                        return "singular_article" if is_article else "ambiguous"
                    return "ambiguous"
                if "\n" in text[raw[cursor].end:raw[cursor + 1].start]:
                    return "ambiguous"
                if kinds & {"LAW", "SELF_LAW", "ANAPHORIC_LAW"}:
                    return "ambiguous"
                if raw[cursor].value in {".", ";", "!", "?"}:
                    return "ambiguous"
                if (not self._is_identifier(raw[cursor].value)
                        and raw[cursor].value not in {",", "и", "или"}):
                    return "ambiguous"
            return "ambiguous"

        for index, token in enumerate(raw):
            word = self._matching_form(token.value)
            if word in {key.rstrip(".") for key in _SHORT_MARKERS}:
                marker_end = index + 2 if index + 1 < len(raw) and raw[index + 1].value == "." else index + 1
                if marker_end > index + 1 and raw[marker_end - 1].start == token.end:
                    marker_kind = _SHORT_MARKERS[word][0]
                    is_t_p_abbreviation = (
                        marker_kind == "POINT" and index >= 2
                        and self._matching_form(raw[index - 2].value) == "т"
                        and raw[index - 1].value == "."
                        and raw[index - 2].end == raw[index - 1].start)
                    if not is_t_p_abbreviation:
                        add(index, marker_end, marker_kind, evidence="exact_abbreviation")
                else:
                    add(index, index + 1, _SHORT_MARKERS[word][0], evidence="exact_abbreviation")
            elif word in self._marker_forms:
                add(index, index + 1, self._marker_forms[word], evidence="exact_marker")
            elif word not in {value for value, _ in _SHORT_MARKERS.items()} and len(word) >= 4:
                for kind in self._fuzzy_marker_kinds(word):
                    add(index, index + 1, kind, evidence="fuzzy_marker")

            if word in _WORD_CONJUNCTIONS and index not in compound_conjunction_tokens:
                add(index, index + 1, _WORD_CONJUNCTIONS[word])
            if token.value == ",":
                following_marker = (self._marker_forms.get(
                    self._matching_form(raw[index + 1].value))
                    if index + 1 < len(raw) else None)
                precedes_lower_level = comma_bridges_hierarchy(index, following_marker)
                comma_kind = ("LEVEL_COMMA" if precedes_lower_level
                              else "COMMA")
                add(index, index + 1, comma_kind)
            if token.value == "в":
                add(index, index + 1, "IN")
            hyphen_context = (ascii_hyphen_context(index) if token.value == "-"
                              else "ambiguous")
            if (token.value in _RANGE_MARKERS
                    and not (token.value == "-"
                             and hyphen_context == "singular_article")):
                add(index, index + 1, "RANGE")
            if self._is_identifier(token.value):
                add(index, index + 1, "ID", evidence="opaque_identifier")
            if index + 2 < len(raw):
                combined = "".join(item.value for item in raw[index:index + 3])
                if (raw[index].end == raw[index + 1].start
                        and raw[index + 1].end == raw[index + 2].start
                        and _HYPHEN_ID_RE.fullmatch(combined)):
                    if ascii_hyphen_context(index + 1) != "plural":
                        add(index, index + 3, "ID", evidence="atomic_hyphen_identifier")

            if word == "фз":
                after = index + 1
                if after < len(raw) and raw[after].value == "№":
                    after += 1
                if after < len(raw) and _INTEGER_ID_RE.fullmatch(raw[after].value):
                    after += 1
                    if (after + 1 < len(raw) and raw[after].value in _RANGE_MARKERS
                            and _INTEGER_ID_RE.fullmatch(raw[after + 1].value)):
                        after += 2
                    elif (after + 1 < len(raw) and raw[after].value in _RANGE_MARKERS
                          and self._matching_form(raw[after + 1].value) == "фз"):
                        after += 2
                    add(index, after, "LAW", evidence="unknown_federal_law")

            if word == "федеральный" and index + 1 < len(raw):
                law_word = self._word_forms(raw[index + 1].value)
                if "закон" in law_word:
                    after = index + 2
                    if after < len(raw) and raw[after].value == "№":
                        after += 1
                    if after < len(raw) and _INTEGER_ID_RE.fullmatch(raw[after].value):
                        after += 1
                        if (after + 1 < len(raw) and raw[after].value in _RANGE_MARKERS
                                and _INTEGER_ID_RE.fullmatch(raw[after + 1].value)):
                            after += 2
                        elif (after + 1 < len(raw) and raw[after].value in _RANGE_MARKERS
                              and self._matching_form(raw[after + 1].value) == "фз"):
                            after += 2
                        add(index, after, "LAW", evidence="unknown_federal_law")

            if word == "QUOTE":
                opening = token.value
                closing_mark = {"«": "»", "„": "“", "“": "”", "‟": "”"}.get(
                    opening, opening)
                closing = next((after for after in range(index + 1, len(raw))
                                if raw[after].value == closing_mark
                                and "\n" not in text[raw[after - 1].end:raw[after].start]), None)
                if closing is not None:
                    quoted_letter = quoted_subpoint_context(index, closing)
                    if quoted_letter:
                        add(index, closing + 1, "ID", evidence="quoted_subpoint",
                            token_value=raw[index + 1].value)
                    else:
                        add(index, closing + 1, "LAW", evidence="unknown_quoted_title")

            if "кодекс" in self._word_forms(token.value):
                start = index
                while start > 0 and self._can_precede_code_name(raw[start - 1].value):
                    start -= 1
                if start < index:
                    add(start, index + 1, "LAW", evidence="unknown_code_name")

            # Preserve explicit, unlisted law names as LAW tokens. Alias edges
            # are collected below and take precedence when they cover this same
            # complete phrase.
            forms = self._word_forms(token.value)
            if forms & {"закон", "конституция"}:
                start = index
                while start > 0 and self._word_forms(raw[start - 1].value) & {
                        "федеральный", "конституционный", "российский"}:
                    start -= 1
                after = index + 1
                if after < len(raw) and raw[after].value.casefold() == "от":
                    cursor = after + 1
                    month_forms = {"январь", "февраль", "март", "апрель", "май",
                                   "июнь", "июль", "август", "сентябрь", "октябрь",
                                   "ноябрь", "декабрь"}
                    date_forms = month_forms | {"год", "n", "№", "фз", "фкз"}
                    while cursor < len(raw) and cursor - after <= 16:
                        value = raw[cursor].value
                        if value in _QUOTE_MARKS:
                            opening = value
                            closing_mark = {"«": "»", "„": "“", "“": "”", "‟": "”"}.get(
                                opening, opening)
                            closing = next((position for position in range(cursor + 1, len(raw))
                                            if raw[position].value == closing_mark), None)
                            if closing is not None:
                                after = closing + 1
                            break
                        word_forms = self._word_forms(value)
                        is_date_number = bool(re.fullmatch(r"\d+(?:[./]\d+)*", value))
                        if (not is_date_number and not word_forms & date_forms
                                and value not in {"-", ".", "/"}):
                            break
                        cursor += 1
                if after == index + 1 and after < len(raw) \
                        and raw[after].value in _QUOTE_MARKS:
                    opening = raw[after].value
                    closing_mark = {"«": "»", "„": "“", "“": "”", "‟": "”"}.get(
                        opening, opening)
                    closing = next((position for position in range(after + 1, len(raw))
                                    if raw[position].value == closing_mark
                                    and "\n" not in text[raw[position - 1].end:
                                                         raw[position].start]), None)
                    if closing is not None:
                        after = closing + 1
                elif after < len(raw) and self._matching_form(raw[after].value) in {
                        "рф", "российской"}:
                    after += 1
                    if (after < len(raw)
                            and "федерация" in self._word_forms(raw[after].value)):
                        after += 1
                if after > index + 1:
                    unknown_law_spans.append((start, after))

            if "конвенция" in forms:
                convention_title = (
                    {"конвенция"}, {"о"}, {"защита"}, {"право"},
                    {"человек"}, {"и"}, {"основной", "основный"}, {"свобода"},
                )
                after = index + len(convention_title)
                is_known_form = (after <= len(raw) and all(
                    expected & self._word_forms(raw[position].value)
                    for position, expected in zip(range(index, after), convention_title)))
                if is_known_form:
                    unknown_law_spans.append((index, after))
                else:
                    add(index, index + 1, "LAW", evidence="unknown_explicit_law")

            if (index > 0 and token.value and token.value[0].isalpha()
                    and any(edge.token.kind in {"ID", "ORDINAL"}
                            for edge in edges.get(index - 1, ()))):
                fuzzy_starts.append(index)
            if self._numbers.is_ordinal(token.value):
                ordinal_value = self._numbers.ordinal_number(token.value)
                evidence = (f"ordinal_value:{ordinal_value}" if ordinal_value is not None
                            else "morphological_ordinal")
                add(index, index + 1, "ORDINAL", evidence=evidence)
            # A written ordinal can have a cardinal prefix: "сто двадцать
            # первого". Keep the whole phrase as one terminal with its original
            # source span so the grammar and semantic projection see one value.
            if (token.value.isalpha()
                    and self._numbers.cardinal_number(token.value) is not None):
                for after in range(index + 2, min(len(raw), index + 8) + 1):
                    phrase_tokens = raw[index:after]
                    if any(not item.value.isalpha() for item in phrase_tokens):
                        break
                    phrase_value = self._numbers.ordinal_phrase_number(
                        tuple(item.value for item in phrase_tokens))
                    if phrase_value is not None:
                        add(index, after, "ORDINAL",
                            evidence=f"ordinal_value:{phrase_value}")

            modifier_forms = self._word_forms(token.value)
            if modifier_forms & {"настоящий", "указанный", "этот"} and index + 1 < len(raw):
                following = self._word_forms(raw[index + 1].value)
                target_kind = "SELF" if "настоящий" in modifier_forms else "ANAPHORIC"
                level = next((kind for lemma, kind in _MARKER_LEMMAS.items()
                              if lemma in following), None)
                if level is not None:
                    add(index, index + 2, f"{target_kind}_{level}",
                        evidence="contextual_structural_reference")
                if "закон" in following:
                    add(index, index + 2, f"{target_kind}_LAW",
                        evidence="contextual_law_reference")

            pending = [(self._alias_trie, index)]
            visited = set()
            while pending:
                node, cursor = pending.pop()
                state = (id(node), cursor)
                if state in visited or cursor >= len(raw):
                    continue
                visited.add(state)
                forms = self._word_forms(raw[cursor].value)
                dispatch = self._alias_form_dispatch[id(node)]
                candidates = {expected for form in forms
                              for expected in dispatch.get(form, ())}
                by_form = {}
                if id(node) in self._alias_compact_nodes and raw[cursor].value.isalpha():
                    by_form = dirty_forms(cursor)
                    candidates.update(expected for form in by_form
                                      for expected in dispatch.get(form, ()))
                for expected in candidates:
                    child = node[expected]
                    for after in alias_token_ends(expected, cursor, forms, by_form):
                        ids = child.get(None, ())
                        if ids:
                            by_span[(index, after, "LAW",
                                     text[raw[index].start:raw[after - 1].end])].update(ids)
                        pending.append((child, after))

        known_law_spans = {(first, after): ids
                           for (first, after, kind, _), ids in by_span.items()
                           if kind == "LAW"}
        for first, after in unknown_law_spans:
            exact_ids = known_law_spans.get((first, after), set())
            title_ids = set().union(*(
                ids for (title_start, title_after), ids in known_law_spans.items()
                if first < title_start and title_after == after
            )) if any(first < title_start and title_after == after
                      for title_start, title_after in known_law_spans) else set()
            fuzzy_title_ids = set()
            if not exact_ids and not title_ids:
                opening = next((position for position in range(first, after)
                                if raw[position].value in _QUOTE_MARKS), None)
                if opening is not None:
                    if opening + 1 < after:
                        fuzzy_title_ids = set().union(*(
                            edge.token.law_ids
                            for edge in self._fuzzy_law_edges(raw, opening, text)
                            if edge.after == after
                        ))
            if not exact_ids:
                resolved_ids = title_ids or fuzzy_title_ids
                evidence = ("law_alias_title" if title_ids else
                            "fuzzy_law_alias_title" if fuzzy_title_ids else
                            "unknown_explicit_law")
                add(first, after, "LAW", law_ids=resolved_ids, evidence=evidence)
        for (first, after, kind, value), ids in by_span.items():
            forms = tuple(sorted({f"{position - first}:{form}"
                                  for position in range(first, after)
                                  for form in self._word_forms(raw[position].value)}))
            source = LexicalCandidate(kind, value, raw[first].start, raw[after - 1].end,
                                      tuple(sorted(ids)), ("law_alias",), forms)
            edges[first].append(_Edge(source, first, after))
        # Fuzzy law names can contribute to a reference only at a position
        # reached from a structural marker through recognized lexical edges.
        # Plain prose often contains one-letter ID candidates followed by a
        # word; searching law aliases at every such position is wasted work.
        reference_starts = {"ARTICLE", "PART", "POINT", "SUBPOINT", "PP", "PARAGRAPH",
                            "SELF_ARTICLE", "SELF_PART", "SELF_POINT", "SELF_SUBPOINT",
                            "SELF_PARAGRAPH"}
        fuzzy_positions = set(fuzzy_starts)
        reachable = [False] * (len(raw) + 1)
        for index in range(len(raw)):
            outgoing = edges.get(index, ())
            if any(edge.token.kind in reference_starts for edge in outgoing):
                reachable[index] = True
            if reachable[index] and index in fuzzy_positions:
                exact_law_ends = [edge.after for edge in outgoing
                                  if edge.token.kind == "LAW" and edge.token.law_ids]
                fuzzy_edges = self._fuzzy_law_edges(raw, index, text)
                if exact_law_ends:
                    longest_exact_law_end = max(exact_law_ends)
                    fuzzy_edges = tuple(edge for edge in fuzzy_edges
                                        if edge.after > longest_exact_law_end)
                edges[index].extend(fuzzy_edges)
            if reachable[index]:
                for edge in edges.get(index, ()):
                    reachable[edge.after] = True
        merged = {}
        for first, outgoing in edges.items():
            unique = {}
            for edge in outgoing:
                key = (edge.after, edge.token.kind, edge.token.value)
                previous = unique.get(key)
                if previous is None:
                    unique[key] = edge
                    continue
                token = edge.token
                combined = LexicalCandidate(
                    token.kind, token.value, token.start, token.end,
                    tuple(sorted(set(previous.token.law_ids) | set(token.law_ids))),
                    tuple(sorted(set(previous.token.evidence) | set(token.evidence))),
                    tuple(sorted(set(previous.token.matching_forms) | set(token.matching_forms))),
                )
                unique[key] = _Edge(combined, first, edge.after)
            merged[first] = list(unique.values())
        return merged

    def _fuzzy_law_edges(self, raw: tuple[_RawToken, ...], start: int,
                         text: str) -> tuple[_Edge, ...]:
        """Match full law-name spans within two character edits of an alias."""
        matches: dict[int, set[int]] = defaultdict(set)
        lengths = self._fuzzy_first_alias_lengths(tuple(sorted(
            self._word_forms(raw[start].value))))
        if not lengths:
            return ()
        source_forms = [self._word_forms(raw[start].value)]
        surface_length = len(self._matching_form(raw[start].value))
        for after in range(start + 2, min(len(raw) + 1, start + max(lengths) + 1)):
            if "\n" in text[raw[after - 2].end:raw[after - 1].start]:
                break
            value = raw[after - 1].value
            source_forms.append(self._word_forms(value))
            surface_length += 1 + len(self._matching_form(value))
            if surface_length < 20:
                continue
            if surface_length > self._max_fuzzy_alias_chars + 2:
                break
            token_count = after - start
            if token_count not in lengths:
                continue
            candidate_positions = None
            for token_position, forms in enumerate(source_forms):
                indexed_positions = self._fuzzy_form_alias_candidates(
                    token_count, token_position, tuple(sorted(forms)))
                candidate_positions = (set(indexed_positions) if candidate_positions is None
                                       else candidate_positions.intersection(indexed_positions))
                if not candidate_positions:
                    break
            for alias_position in candidate_positions or ():
                alias = self._fuzzy_aliases[token_count][alias_position]
                self._fuzzy_aliases_checked += 1
                if abs(surface_length - len(alias.surface)) > 2:
                    continue
                remaining = 2
                for word_forms, alias_forms in zip(source_forms, alias.forms):
                    if word_forms.intersection(alias_forms):
                        continue
                    best = min((Levenshtein.distance(source, target,
                                                     score_cutoff=remaining)
                                for source in word_forms for target in alias_forms),
                               default=remaining + 1)
                    remaining -= best
                    if remaining < 0:
                        break
                if remaining >= 0:
                    matches[after].update(alias.law_ids)
        return tuple(
            _Edge(LexicalCandidate("LAW", text[raw[start].start:raw[after - 1].end],
                                   raw[start].start, raw[after - 1].end,
                                   tuple(sorted(law_ids)), ("fuzzy_law_alias",),
                                   tuple(sorted({f"{position-start}:{form}"
                                                 for position in range(start, after)
                                                 for form in self._word_forms(raw[position].value)}))),
                  start, after)
            for after, law_ids in matches.items()
        )

    @staticmethod
    def _is_identifier(value: str) -> bool:
        """Recognize opaque numeric, letter, dotted, superscript, and hyphen IDs."""
        return (bool(_INTEGER_ID_RE.fullmatch(value)) or bool(_COMPOUND_ID_RE.fullmatch(value))
                or bool(_HYPHEN_ID_RE.fullmatch(value))
                or (len(value) == 1 and value.isalpha()
                    and ("а" <= value.casefold() <= "я" or value.casefold() == "ё")))

    @lru_cache(maxsize=32768)
    def _alias_forms(self, value: str) -> frozenset[str]:
        """Add visual-script alternatives only for short supplied law aliases."""
        forms = set(self._word_forms(value))
        if (len(value) <= 8 and value.isalpha()
                and any(character in _LOOKALIKE_LETTERS for character in value.casefold())
                and any(not character.isascii() for character in value)):
            forms.add(self._matching_form(value.casefold().translate(_LOOKALIKE_TRANSLATION)))
        return frozenset(forms)

    @lru_cache(maxsize=32768)
    def _can_precede_code_name(self, value: str) -> bool:
        """Allow inflected names and modifiers before an unknown code-name head."""
        return any(parse.tag.POS in {"ADJF", "NOUN", "PRTF", "PRTS"}
                   for parse in self._morphology.parse(value))

    def _parse_candidates(self, raw, edges, text, selected_only=False):
        """Parse every complete lexical path and retain malformed continuations."""
        starts = {"ARTICLE", "PART", "POINT", "SUBPOINT", "PP", "PARAGRAPH",
                  "SELF_ARTICLE", "SELF_PART", "SELF_POINT", "SELF_SUBPOINT",
                  "SELF_PARAGRAPH"}
        grouped: dict[tuple[int, int], dict[AstNode, None]] = defaultdict(dict)
        deferred: dict[tuple[int, int], list[tuple[Tree, tuple[LexicalCandidate, ...]]]] = (
            defaultdict(list))
        incomplete_spans: dict[tuple[int, int], int] = {}
        starts_at = [item.start for item in raw]

        for first, outgoing in sorted(edges.items()):
            for first_edge in sorted(outgoing, key=lambda edge: (
                    edge.token.kind, edge.token.value, edge.after)):
                if first_edge.token.kind not in starts:
                    continue
                pending = [(first_edge.after, (first_edge.token,))]
                visited = set()
                while pending:
                    cursor, path = pending.pop()
                    path_key = (cursor, tuple((item.kind, item.value, item.start, item.end,
                                               item.law_ids) for item in path))
                    if path_key in visited:
                        continue
                    visited.add(path_key)
                    tree = None
                    if path[-1].kind in {"ID", "ORDINAL", "LAW", "SELF_LAW", "ANAPHORIC_LAW",
                                         "ANAPHORIC_ARTICLE",
                                         "SELF_ARTICLE", "SELF_PART", "SELF_POINT",
                                         "SELF_SUBPOINT", "SELF_PARAGRAPH"}:
                        tree = self._parse_shape(path, materialize=not selected_only)
                    if tree is _INVALID_PARSE_PREFIX:
                        continue
                    if tree is not None:
                        span = (path[0].start, path[-1].end)
                        if selected_only:
                            deferred[span].append((tree, path))
                        else:
                            lexical = {(item.kind, item.start, item.end, item.value): item
                                       for item in path}
                            for expanded in expand_trees(tree):
                                ast = tree_to_ast(expanded, lexical)
                                if isinstance(ast, AstNode):
                                    grouped[span][ast] = None
                        next_index = bisect_left(starts_at, span[1])
                        next_piece = raw[next_index] if next_index < len(raw) else None
                        if next_piece is not None:
                            following_index = bisect_left(starts_at, next_piece.end)
                            following = raw[following_index] if following_index < len(raw) else None
                            reference_starts = {"ARTICLE", "PART", "POINT", "SUBPOINT", "PP",
                                                "PARAGRAPH", "SELF_ARTICLE", "SELF_PART",
                                                "SELF_POINT", "SELF_SUBPOINT", "SELF_PARAGRAPH"}
                            is_connector = self._is_unfinished_connector(next_piece.value)
                            if next_piece.value == ",":
                                comma_followers = edges.get(following_index, ())
                                selector_kinds = {"ID", "ORDINAL", "RANGE", "IN"}
                                join_kinds = {"AND", "OR", "AND_OR"}
                                is_connector = False
                                if any(edge.token.kind in join_kinds for edge in comma_followers):
                                    is_connector = following is None
                                if (any(edge.token.kind in join_kinds for edge in comma_followers)
                                        and following is not None):
                                    after_join = bisect_left(starts_at, following.end)
                                    join_followers = edges.get(after_join, ())
                                    has_citation_continuation = any(
                                        edge.token.kind in selector_kinds | reference_starts
                                        for edge in join_followers)
                                    after_join_token = (raw[after_join]
                                                        if after_join < len(raw) else None)
                                    ends_with_punctuation = (
                                        after_join_token is not None
                                        and not after_join_token.value[:1].isalnum())
                                    is_connector = (has_citation_continuation
                                                    or ends_with_punctuation)
                            if next_piece.value in _RANGE_MARKERS:
                                continues = (following_index in edges and any(
                                    edge.token.kind in {"ID", "ORDINAL"}
                                    for edge in edges[following_index]))
                            else:
                                continues = (following_index in edges and any(
                                    edge.token.kind in reference_starts
                                    | {"ID", "ORDINAL", "RANGE", "IN"}
                                    for edge in edges[following_index]))
                            ends_at_boundary = (following is None or
                                                not following.value[:1].isalnum())
                            if (is_connector and not continues
                                    and (ends_at_boundary or next_piece.value in _RANGE_MARKERS)):
                                incomplete_spans[span] = next_piece.end
                    for edge in sorted(edges.get(cursor, ()), key=lambda item: (
                            item.token.kind, item.token.value, item.after)):
                        if (edge.token.kind in {"LAW", "SELF_LAW", "ANAPHORIC_LAW"}
                                and path[-1].kind in {"LAW", "SELF_LAW", "ANAPHORIC_LAW"}):
                            continue
                        pending.append((edge.after, path + (edge.token,)))

        candidates = []
        diagnostics = []
        if selected_only:
            chosen: dict[int, tuple[int, int]] = {}
            for span in deferred:
                start, end = span
                if span not in incomplete_spans and (
                        start not in chosen or end > chosen[start][1]):
                    chosen[start] = span
            chosen_spans = set(chosen.values())
            spans = sorted(deferred)
        else:
            chosen_spans = None
            spans = sorted(grouped)
        for start, end in spans:
            incomplete = (start, end) in incomplete_spans
            candidate_diagnostics = ((Diagnostic("unfinished_continuation", end,
                                                 incomplete_spans[(start, end)]),)
                                      if incomplete else ())
            diagnostics.extend(candidate_diagnostics)
            if selected_only:
                if (start, end) not in chosen_spans:
                    continue
                alternatives: dict[AstNode, None] = {}
                for shape, path in deferred[start, end]:
                    tree = materialize_shape(shape, path)
                    lexical = {(item.kind, item.start, item.end, item.value): item
                               for item in path}
                    for expanded in expand_trees(tree):
                        ast = tree_to_ast(expanded, lexical)
                        if isinstance(ast, AstNode):
                            alternatives[ast] = None
            else:
                alternatives = grouped[start, end]
            candidates.append(CandidateSpan(start, end, tuple(alternatives), not incomplete,
                                            candidate_diagnostics))
        return candidates, diagnostics

    @staticmethod
    def _is_unfinished_connector(value: str) -> bool:
        """Recognize a dangling list, range, or hierarchy connector."""
        return value in _RANGE_MARKERS or value.casefold() in {"и", "или", "в"}
