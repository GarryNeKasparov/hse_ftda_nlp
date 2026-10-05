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
