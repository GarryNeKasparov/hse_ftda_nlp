# Revised pipeline review and vote

This file records a concise summary of the critic agents' two review rounds.
It is not a verbatim transcript. The full responses are in the conversation
history. Scores are subjective architecture ratings, not extraction metrics.

## Candidates and method

- **A: Original pipeline.** Ten explicit stages; law recognition assigns IDs;
  parser is described as deciding ranges, structure, and shared tails; boundary
  detection may follow parsing.
- **B: Revised pipeline.** Preserve token and normalization alternatives;
  represent recognized laws as ID candidates; discover candidate spans before
  parsing and let parsing refine them; retain correlated AST alternatives and
  symbolic selectors; resolve identity and interpretation separately; expand
  within branches only after selection.
- **C: Whole-text generalized grammar.** Extend the grammar to arbitrary prose,
  boundaries, and recovery without candidate preselection.

First round: three critics independently reviewed semantics and aliases,
grammar and AST, and evaluation and performance. Each voted to revise A and
listed concrete blockers. The main repeated findings were:

- 580 normalized law aliases have multiple IDs; exact matching cannot always
  return one `law_id`.
- The current grammar has five ambiguous fixtures, while the BNF covers bounded
  candidates and does not define full-text recovery.
- Existing Earley checks consume manually annotated token kinds. They do not
  validate Russian tokenization, expected AST meaning, or raw-text output.
- The `LawLink` schema cannot express simultaneous point and part levels or
  paragraphs; projection policies remain unresolved.
- Context inheritance was previously deferred and should stay deferred.
- Runtime performance has not been measured on a representative workload.

Second round: all three rated A, B, and C from 0 to 5 on correctness,
information preservation, simplicity, and performance feasibility. Performance
ratings represent unmeasured engineering risk. Scores used the agreed review
weights: correctness 40%, information preservation 25%, simplicity 20%, and
performance feasibility 15%. Correctness blockers cannot be overridden by the
aggregate score.

| Critic focus | A | B | C | Vote |
|---|---:|---:|---:|---|
| Legal semantics and output schema | 2.35 | 4.10 | 2.70 | B |
| Grammar, boundaries, and AST | 2.35 | 4.10 | 2.35 | B |
| Evaluation, performance, and recovery | 2.45 | 4.10 | 2.15 | B |
| **Mean** | **2.38** | **4.10** | **2.40** | **B, 3–0** |

## Conditions and remaining concerns

All critics accepted B as the architecture for further experiments, not as a
production-complete service specification. Candidate discovery must be tested
against independently annotated spans because it can discard a reference
before Earley sees it. Tests should include dangling continuations, shared
tails, parenthetical interruptions, publication-coordinate negatives, and
overlapping candidates. Complete `LawLink` projection and performance against
the instructor's five-minute limit remain open.

The team chose the initial milestone: candidate spans and AST alternatives;
contiguous references first; retain an incomplete prefix with a diagnostic and
continue extracting later references. Contextual inheritance remains deferred.
