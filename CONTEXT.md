# Legal References

This glossary describes legal references in source text and the provisions they identify.

## Language

**Legal reference**:
A passage of source text identifying one or more legal provisions through hierarchy levels and an explicit or context-dependent law. A reference can be extracted even when its law is unspecified or unresolved.

**Legal provision**:
An individual target identified by a law and the specified levels within it. Each output `LawLink` represents one such target.

**Grouped legal reference**:
A legal reference containing a list of values at one or more hierarchy levels within one branch. Lists at different levels identify every combination of their values: subpoints а and б within points 1 and 2 identify four provisions.

**Reference range**:
An inclusive sequence of provision identifiers at one hierarchy level. A hyphen within an identifier does not by itself establish a range.

**Law alias**:
A name or abbreviation associated with a law ID in `law_aliases.json`. Inflected forms may occur in source text.

**Unknown law**:
A law mentioned in a legal reference whose identity cannot be resolved through the supplied law aliases. Its extracted reference has `law_id=null`; unknown identity does not mean the law does not exist.

**Unspecified law**:
A law whose name is absent from an extracted reference. The reference has `law_id=null` unless its law can be established from context; absence of a name differs from an unrecognized name.

**Ambiguous law**:
A law mention that matches more than one possible law identity. Even an exact alias can be ambiguous when the supplied dictionary associates it with multiple IDs.

**Point or part**:
The level of a reference represented by `point_article`; the assignment places both points and parts in this field.

**Subpoint**:
The level within a point or part represented by `subpoint_article`.

**Semantic analyzer**:
The shared stage after syntax parsing that turns AST alternatives into
provision paths. Semantic tickets extend this analyzer and its provision-path
representation; they do not create separate semantic stages for each feature.

**Provision path**:
One interpreted target within a legal reference. It retains law identity
status and candidate IDs, plus separate article, part, point, subpoint, and
paragraph values until the output mapper projects it to the narrower API
schema.

**Contextual resolver**:
A separate left-to-right pass over semantic references. It carries the latest
explicit law and article, fills omitted law identities, and resolves
self/anaphoric targets from the most recent compatible context. Text-only
input does not provide the enclosing document, so `настоящей статьи/закона`
uses backward context as a fallback and otherwise remains unresolved.

**LawLink projection**:
The response keeps its existing fields: `law_id`, `article`, `point_article`,
and `subpoint_article`. If both part and point are present, `point_article`
contains the point and the part is omitted from the response. A part alone maps
to `point_article`. Paragraphs remain internal and do not prevent supported
fields from being returned. For an ambiguous law alias, the response uses the
smallest candidate ID; the internal path retains the ambiguity status and all
candidate IDs. The mapper records diagnostics for omitted hierarchy levels and
for this deterministic ambiguous-ID projection.
