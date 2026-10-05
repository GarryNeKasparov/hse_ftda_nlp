# Russian legal-reference syntax: primary evidence and parser implications

Research date: 2026-10-01. Scope: reference syntax, not advice on the application of law or verification of the current contents of every cited provision.

## Reading this note

**Evidence** means a form observed in an institutional publication, legal text, or court document. **Inference** means a proposed lexer or grammar decision motivated by that evidence. **Homework assumption** means a local requirement or design choice. **Unresolved** means the available evidence does not justify a deterministic rule. These distinctions apply throughout; an attested example is not an exhaustive specification of Russian legal prose.

External legal claims below use legislative/government publications and official court websites only. Some KSRF evidence was retrieved as search-index excerpts of the original official pages; direct access failures are recorded at the end. Commercial legal databases and academic discussions were discovery leads only, not authority for the findings.

Local task context was read from [README.md](../README.md), [instructor_note.md](../instructor_note.md), and [parser-design.md](parser-design.md). This note proposes no implementation and makes no claim about unseen benchmark coverage. Normalization findings and remaining assignment questions are included below.

## Institutional drafting guidance: a bounded starting point

**Evidence.** Yugra Duma hosts the State Duma's **2007** second edition of drafting recommendations/commentary. This historical publication is not the 2021 revision. [Title page][s1]

The following is a compact paraphrase of relevant recommendations:

- Article → part → point → subpoint is an illustrated hierarchy; article parts have numeric labels, points numeric labels with closing parentheses, and subpoints Cyrillic letters with closing parentheses. References start with the smallest unit. [§§9, 25–26][s1]
- Insertions retain existing numbering and can add raised digits to numeric or letter labels. [§12][s1]
- Paragraph references use ordinal words. Counting begins with the paragraph opening the containing unit; repealed paragraphs retain their place in later counting. [§§27, 70][s1]
- A part of a code is distinct from a part of an article. Ordinary references to articles of multipart codes omit the code-part number; amendment references can include it. [§§4, 23–24][s1]
- Self references use forms of `настоящий`; code citations omit enactment date and number. [§§23, 28][s1]

**Unresolved.** These prescriptions do not specify all court abbreviations, free prose, or legacy numbering. The primary examples below are needed alongside them.

## Practical rules, with evidence and limits

### 1. Keep point and part as separate structural levels

**Evidence.** The Supreme Court review approved on 28 September 2016 uses the following on printed page 3:

> пунктом 1 части 1 и частью 2 статьи 31

Point 1 belongs to part 1, while the second branch names part 2; both attach to article 31. The law appears after a parenthetical qualification. [Review, p. 3][s2]

**Inference.** The corresponding structure is a union of two paths:

```text
Law 44-ФЗ
└── Article 31
    ├── Part 1 → Point 1
    └── Part 2
```

A grammar limited to one interchangeable `POINT_OR_PART` slot cannot retain this distinction. Preserve explicit levels internally; schema projection is a later decision. This example also motivates allowing a bounded parenthetical interruption between a provision and its act. It does not establish a rule for arbitrarily long interruptions. [Review, p. 3][s2]

**Homework assumption / unresolved.** The local schema combines point and part into `point_article`; it has no selected mapping for simultaneous levels. The design document records this gap. No court example resolves a serialization contract. [README][readme], [design decisions][design]

### 2. Determine a level from its marker, not from identifier shape

**Evidence.** The Supreme Court's 2012 second-quarter review calls the lettered qualifying provisions of criminal-law articles points. On printed page 79 it uses `пп. «а», «б», «в»` and then expressly says the points were not specified. [Review, p. 79][s3]

Conversely, Plenum resolution No. 50 of 18 July 2014, §33, refers to numeric subpoints 1 and 2 of point 9 of article 1483 of the Civil Code. Thus letters do not imply subpoints, and digits do not imply points. [Plenum, §33][s4]

**Inference.** Preserve the stated level and allow numeric or letter labels. Numeric subpoints support that aspect of the homework examples, not every irregular sample. [Plenum, §33][s4], [README][readme]

### 3. Treat paragraph ordinals as positions within an explicitly identified parent

**Evidence.** Supreme Court appeal No. АПЛ25-42, dated 13 March 2025, concerns paragraph two of point 1 of government-approved connection Rules. It repeatedly identifies the paragraph and point without an article. [Determination, pp. 1–2][s5]

**Inference.** Preserve a paragraph ordinal under its stated parent. Do not relabel it to fit the output schema. An article must be optional internally. [Determination, pp. 1–2][s5]

**Unresolved.** Resolving paragraph numbers against the original act needs its structure and relevant edition. Extraction from plain text alone cannot reconstruct every paragraph boundary or determine which repealed paragraphs remain in the count. The homework's omission of a paragraph field remains an output decision. [design decisions][design]

### 4. Recognize ordinal parts, including coordinated and ranged ordinals

**Evidence.** The required KSRF notice uses spelled-out part ordinals for Labour Code provisions and combines an ordinal range with another ordinal:

> частями первой-четвертой и одиннадцатой

Its target is article 133.1. The same notice also contains numeric parts and a reference to paragraph one of a part. [KSRF notice; indexed official text][s6]

**Inference.** Interpret ordinals with their level marker. Here the selected parts are 1–4 and 11, under atomic article label 133.1. [KSRF notice][s6]

**Unresolved.** This is evidence of particular forms, not a complete inflection table or proof that all ordinals can always be safely converted to numeric labels.

### 5. Keep dotted and letter-dotted identifiers atomic

**Evidence.** The KSRF-hosted text of the electoral-guarantees law, articles 3–6, has subpoint labels `а.1`, `а.2`, and `б.1`. Its internal references combine them with point 3.2 and the current article. The same text contains an ordinal part label followed by a dotted suffix when citing a criminal-law provision. [Legal text; indexed official text][s7]

Supreme Court document 2273344 cites administrative-regulation points with several dotted segments, including 2.10.1.1 and 2.10.1.2. It also reproduces a label containing a parenthesized suffix, 2.5.3(1). [Court document, regulation discussion][s8]

**Inference.** Dots inside a label are not hierarchy separators by themselves. `2.10.1.1` following a point marker denotes one stated point label. Likewise, `а.1` need not mean subpoint а followed by a separate point 1. Preserve the raw identifier and its punctuation. An internal lexical model should allow multiple numeric segments and letter-plus-number forms; exotic parenthesized suffixes can be preserved even if downstream support is deferred. [Electoral legal text][s7], [court document][s8]

**Unresolved.** There is no established maximum number of dotted segments in this sample, and a dotted label does not reveal the whole structure of the target act.

### 6. Preserve superscript information before flattening it

**Evidence.** A KSRF institutional report for 2020 contains criminal-law references rendered by the index as `159¹–159³`, followed by other superscript-numbered articles. [Institutional report; indexed official text][s9]

**Inference.** Raised suffixes can distinguish a provision identifier from an ordinary integer. Retain the source spelling and, where available, typography metadata. A renderer or OCR output that concatenates a base and suffix can lose this distinction: a generated illustration is 15 with raised 1 becoming plain `151`. This is a data-loss scenario, not a claim that article 151 should be rewritten. [KSRF report][s9]

**Unresolved.** This research establishes occurrence of superscript labels; it does not establish universal equivalence between a raised suffix, a dot, a hyphen, and adjacent baseline digits. Only act-specific evidence can support such equivalence. The report PDF itself could not be fetched directly, so the exact typography was not independently inspected visually. [KSRF report][s9]

### 7. A hyphen can be part of one provision identifier

**Evidence.** The required KSRF notice says:

> частью 1.3-3 статьи 32.2

The singular part marker is direct counterevidence to treating this occurrence as a range. [KSRF notice; indexed official text][s6]

An accessible Supreme Court Plenum text also refers to article 28-1 of a federal law with a singular article marker. [Plenum No. 30, §24][s10]

**Inference.** Provide an atomic identifier alternative containing hyphens. Singular agreement is useful evidence but not a universal disambiguator. Retain competing interpretations when the target cannot be checked; longest-token recognition alone cannot decide every case. [Plenum No. 30, §24][s10]

**Homework assumption.** Expanding `43.2–6` into 43.2 through 43.6 is local and provisional; no accessed primary source establishes that general convention. Constrain or reconsider it. [design decisions][design]

### 8. Separate explicit lists from ranges, and syntax from target enumeration

**Evidence.** Plenum No. 30, §24, combines two integer subpoint ranges under one point and article using `1-10 и 16-18`. Its §25 combines a single identifier with another range. Thus a hyphen can also express an actual range in an appropriate plural construction. [Plenum No. 30, §§24–25][s10]

**Inference.** Represent `Single`, `List`, and `Range` separately. A comma and final conjunction can combine different selector forms. Expansion of simple integer ranges is a reasonable homework policy, but resolving the set of actual legal provisions requires the target's ordering, insertions, repeals, and edition. A generated range between articles 9 and 12 cannot by punctuation alone answer whether an inserted article 10.1 is included. [Plenum No. 30][s10]

**Homework assumption.** The local agreement to expand integer ranges inclusively supplies an output policy. It is not proof of one universal legal enumeration algorithm. [design decisions][design]

### 9. Letter ranges do not justify blindly walking the full Russian alphabet

**Evidence.** KSRF's hosted electoral-law financing chapter combines multiple letter ranges. Its displayed labels include the sequence е, ж, з and then и, к; the target list therefore does not use ё or й at those positions. [Chapter VIII; indexed official text][s11]

The KSRF-hosted prosecution-law text combines individual letters with a letter range under a shared point and current article. It also uses letter ranges elsewhere in its service provisions. [Section V; indexed official text][s12]

**Inference.** Expand a letter range against the target unit's actual ordered labels when that structure is available. For the observed electoral-law sequence, walking the complete modern alphabet would invent labels. Inserted dotted letter labels create a further ordering question: a generated range from а to в does not by itself establish whether а.1 is included. [Electoral financing text][s11], [electoral articles 3–6][s7]

**Unresolved.** No verified primary drafting rule establishing a universal skipped-letter set across all acts was obtained. In particular, the observation about ё and й does not prove how ы, ъ, and ь are handled everywhere. Any fixed homework alphabet and its skip set must be documented as assumptions. Accepting an explicit unusual letter and expanding a range through it are separate decisions. [design decisions][design]

### 10. Parse coordination as branches before expanding selectors

**Evidence.** Plenum No. 50, §33, coordinates points 2, 4, and 6 with subpoints 1 and 2 of point 9, sharing article 1483 and its code. The point-9 branch has deeper structure than the other branches. [Plenum, §33][s4]

**Inference.** This yields five provision paths: three direct point paths, and two subpoint paths under point 9. A global Cartesian product of every identifier at every level would invent references. Attach a common tail to compatible branches, then expand lists inside each branch. [Plenum, §33][s4]

**Homework assumption / unresolved.** The local phrase “all combinations” needs a structural scope: combinations within one explicitly nested branch differ from combinations across coordinated branches. The primary evidence does not determine attachment for every comma or conjunction in unrestricted prose. [design decisions][design]

### 11. Common tails can include a law, while preceding branches name different articles

**Evidence.** The 2005 fourth-quarter Supreme Court review contains compact criminal-law citations in which several point/part/article branches precede one trailing code name. It also uses `п.п.` with internal periods and no-space forms of part/article abbreviations. [Review, criminal-law discussion of the Parenkov case][s13]

**Inference.** Model shared tails at more than one level: a law can scope multiple articles, and an article can scope multiple parts. Repeated markers are branch boundaries when their structure demands it. Generated illustration: `часть 2 статьи 8 и часть 3 статьи 9 УК РФ` has two article branches, not both parts under both articles. This illustrates a grammar capability, not a quoted sentence. [2005 review][s13]

**Unresolved.** A nearest-law heuristic can over-attach. A conjunction may join sentences, legal references, or ordinary prose. Retain unresolved attachment rather than asserting that all preceding fragments share the final law.

### 12. Abbreviations are context-dependent; `пп.` is especially ambiguous

**Evidence.** The 2012 second-quarter review uses the doubled-p abbreviation for plural **points**, including lettered points; its surrounding prose confirms the level. [Review, p. 79][s3]

In the official report of case АКПИ12-1326, the Supreme Court distinguishes `подп.` for lettered subpoints from `пп.` for a list of Rules points. [Official decision extract][s14]

**Inference.** Marker normalization needs lexical alternatives and syntactic context, not a universal `пп.` → subpoint substitution. Explicit full words should carry stronger level evidence. Labels alone do not settle the ambiguity. Retain the source abbreviation if the context remains inconclusive. [2012 review][s3], [decision extract][s14]

**Homework assumption.** README uses `пп.` for subpoints in its worked examples. That is a supported local convention for those examples, not the only meaning in official writing. The distinction is grounded in court texts here; no general-language dictionary answer is needed as legal authority. [README][readme], [decision extract][s14]

**Evidence.** No-space and internally dotted abbreviations also occur in the 2005 review; abbreviation matching should accommodate those observed spellings without treating every period as a sentence boundary. [2005 review][s13]

### 13. An act name can be full, abbreviated, quoted, numbered, or locally introduced

**Evidence.** Appeal АПЛ25-42 introduces a full federal-law name and a shortened topical name, a full Civil Code name and its acronym, Rules approved by a government resolution, and an order of the Moscow mayor. [Determination, pp. 2–4][s5]

The court's 2013 Presidium ruling No. 17630/12 introduces the full Civil Code name and then a shorter code name for subsequent use. [Ruling, factual/legal discussion][s15]

**Inference.** A `LAW` token should mean the cited legal instrument, not just a federal statute. Candidate forms include an act kind plus date/number/title; code names and acronyms; quoted known titles; and names explicitly introduced by a local definition. Supporting nested quotation marks matters when the title itself mentions another named act. Resolve those candidates separately from the provision hierarchy. [Determination][s5], [Presidium ruling][s15]

**Unresolved.** A bare quoted phrase is not automatically an act name. Nor is a short number necessarily a unique identity. A definition introduced with `далее` needs document context; extraction of the definition and resolution of later mentions are different operations. [Presidium ruling][s15], [local alias evidence](../law_aliases.json)

### 14. Distinguish missing law names, self references, and anaphora

**Evidence.** The KSRF-hosted referendum law, final/transitional chapter, uses the current article and the current federal constitutional law as reference targets. Its article 93 also names article 92 of that current law. [Legal text; indexed official text][s16]

The KSRF electoral-law text uses the current point and current article with dotted letter subpoints. [Articles 3–6][s7]

**Inference.** Distinguish omitted, self, and anaphoric targets. Self references require the enclosing act or provision; anaphora requires an antecedent. Converting either to an external law ID needs context. [Referendum legal text][s16]

**Homework assumption.** The design initially emits `law_id=null` without an explicit law and defers inheritance. This note supplies syntax evidence; it does not change that policy. Ambiguity among several known acts is a separate condition from an unknown act. [design decisions][design], [local alias evidence](../law_aliases.json)

### 15. Exclude publication coordinates from provision extraction

**Evidence.** The referendum-law chapter places `ст. 3921` inside a parenthetical citation to *Собрание законодательства Российской Федерации*, alongside year 1995 and issue 42. The same sentence has genuine references to an article and part of the law outside those publication coordinates. [Article 93; indexed official text][s16]

**Inference.** Mark publication coordinates separately; their item number is not a provision of the named law. Parentheses alone are insufficient grounds for exclusion. [Referendum legal text][s16]

**Unresolved.** Similar numerical expressions can be case numbers, dates, document registration numbers, page citations, measurements, or list headings. These are candidate negative contexts, not an exhaustively established exclusion grammar. An act title describing an amendment can itself contain genuine references; whether to emit those mentions is a separate extraction contract.

## Lexer and grammar sketch: design inferences, not an implementation

The numbered rules above motivate the following division of responsibilities. The sketch is deliberately incomplete: it describes the concepts needed to retain evidence and ambiguity, not a proven unambiguous grammar.

```text
IDENTIFIER := opaque provision label retaining original spelling
SELECTOR   := Single(IDENTIFIER) | List(SELECTOR...) | Range(start, end)
LEVEL      := Paragraph | Subpoint | Point | ArticlePart | Article
TARGET     := ExplicitAct | SelfAct | AnaphoricAct | OmittedAct
PATH       := sequence of explicitly stated LEVEL/SELECTOR pairs
REFERENCE  := one PATH, or coordinated PATH branches with shared tails
```

**Inference.** Lex before expanding; parse parent attachment and branches before resolving acts or enumerating selectors. This is an engineering proposal motivated by the observed labels and shared tails, not an official parser specification. [dotted-label evidence][s8], [shared-law evidence][s13]

**Inference.** Preserve source spans, raw labels, and an unresolved alternative when information has been lost or attachment is ambiguous. This is an engineering recommendation for reviewability, not a legal drafting requirement. The hypothetical strings in this note are illustrations for grammar discussion and have not been run as parser tests.

**Unresolved.** Repeated level markers, intervening prose, exceptions, forward references, quoted amendments, and references across sentences need explicit scope policies. The accessed examples do not establish a single unrestricted grammar or guarantee that a deterministic parser will always choose the intended reading.

## Local dataset evidence supplied by the main audit

The following findings were supplied by the concurrent local audit; this research did not repeat its counting. They describe the workspace dataset, not Russian legal drafting generally. Each refers to [law_aliases.json](../law_aliases.json).

| Local observation | Practical consequence / inference |
|---|---|
| 1,055 IDs; 18,724 alias entries; 17,934 unique casefolded strings; 580 casefolded strings map to more than one ID. | Alias recognition and unique identity resolution are separate steps. A matching surface form can leave multiple known candidates. |
| `ФЗ №7-ФЗ` maps to IDs 247, 401, 446, 471, 501, and 533, with different dates/titles. | A bare number cannot always select a unique dataset ID. Preserve ambiguity or use explicit date/title evidence. |
| The audited categories include 415 decree IDs, 34 order IDs, 21 code IDs, and 488 federal-law IDs; accounting titles/standards and older laws also occur. | Do not restrict the act lexicon to `ФЗ` plus code-name patterns. These figures are the reported categories, not an asserted complete partition. |
| Standalone quoted-title aliases exist, for example under ID 21; the longest alias is 796 characters. | Act candidates need known-title matching and adequate boundaries. A short arbitrary maximum title length would lose supplied aliases. |
| ID 8 has short aliases mixing Latin `C` and Cyrillic `К`. | Visual similarity and exact character identity differ. This is a local normalization issue; the normalization section below gives the Unicode analysis. |

**Homework assumption.** README requests individual provision outputs and uses intentionally irregular examples. Those requirements are local evidence for service behavior; official citation style cannot be assumed to define all expected input forms. [README][readme], [instructor note](../instructor_note.md)

## Normalization findings

### N1. Preserve superscript boundaries before compatibility normalization

**Evidence.** Unicode distinguishes canonical normalization (NFC/NFD) from compatibility normalization (NFKC/NFKD). Compatibility normalization removes superscript distinctions; canonical normalization preserves them. The standard cautions against blindly applying compatibility normalization when formatting distinctions carry meaning. [Unicode UAX #15, sections 1.1–1.2](https://unicode.org/reports/tr15/)

**Grammar implication, inferred.** An identifier written with a superscript must retain that boundary before normalization: flattening `15¹` to `151` could confuse an inserted article with article 151. Recognize the raw identifier first; keep original spelling and a structured representation. Choosing whether the API should serialize it as `15¹`, `15.1`, or another form is an assignment question, not answered by Unicode.

### N2. Use token-specific punctuation processing

**Evidence.** RapidFuzz's `default_process` removes non-alphanumeric characters, trims whitespace, and lowercases text. Its Levenshtein API accepts preprocessing as a separate optional operation. Neither function supplies a legal-reference grammar. [RapidFuzz preprocessing](https://rapidfuzz.github.io/RapidFuzz/Usage/utils.html), [Levenshtein API](https://rapidfuzz.github.io/RapidFuzz/Usage/distance/Levenshtein.html)

**Grammar implication, inferred.** Do not apply that default processor to whole references. Dots, hyphens, commas, quotes, and number signs may delimit identifiers, lists, ranges, and document metadata. First retain their token roles; normalize whitespace/case and equivalent quote forms without discarding the original span. Morphological matching and fuzzy matching require separately specified policies.

### N3. Treat visually similar scripts as controlled matching alternatives

**Evidence.** Unicode specifies confusable detection separately from its normalization forms, including mixed Latin/Cyrillic strings. The local dictionary's family-code aliases use Latin `C` followed by Cyrillic `К`. [Unicode UTS #39, sections 4–5](https://www.unicode.org/reports/tr39/), [local alias dictionary](../law_aliases.json)

**Grammar implication, inferred.** Add controlled lookalike variants when matching known abbreviations; do not transliterate all source text or provision letters indiscriminately. Preserve raw letters so an uncertain Latin/Cyrillic interpretation remains visible. Detecting a visual resemblance does not establish that two legal identifiers are identical.

### N4. Morphological normalization can yield alternative readings

**Evidence.** The pymorphy2 author documentation describes multiple parses per word and explains that their scores do not reliably resolve context-dependent ambiguity. Its example `стали` has readings with different lemmas, and it notes that domain usage may differ from the corpus frequencies used for ranking. This documents a morphological limitation, not a recommendation to install that library. [Author documentation, parsing and disambiguation](https://pymorphy2.readthedocs.io/en/stable/user/guide.html)

**Grammar implication, inferred.** Match the vocabulary of hierarchy markers and multiword law aliases against appropriate morphological candidates. A pipeline that always replaces each word with its first predicted lemma can discard a valid law-name match before parsing. Prefer explicit marker forms or retain alternatives for constrained alias matching; select a library only after deciding the required behavior.

## Questions external research cannot settle

The assignment defines a service with four output fields, explicitly expands a subpoint list, and supplies aliases. It does not define outputs for simultaneous point/part levels, paragraphs, superscript serialization, ambiguous dictionary IDs, unsupported laws, contextual inheritance, deduplication, or every range notation. Its sample inputs alone do not supply expected outputs for those cases. [README](../README.md), [service scaffold](../main.py)

The instructor specifies four hidden benchmarks of 500 texts each and a five-minute total runtime limit, but gives no scoring formula or annotated outputs in the note. External legal conventions cannot establish those hidden benchmark labels. [Instructor note](../instructor_note.md)

**Design consequence, inferred.** Keep evidence-backed syntax rules separate from chosen fallback/output policies. Seek instructor clarification for schema limitations and ambiguous notation; preserve the relevant distinctions internally until then. No conclusion about LL(k), LR(k), Earley, or GLR follows from the sources without an actual grammar and its lexical assumptions.

## Access record and exact limitations

1. **Required Supreme Court source:** the 20-page PDF opened; the wording was verified on printed page 3, PDF index 2. Screenshot retrieval failed. [PDF][s2]

2. **Required KSRF source:** indexed text retrieved; direct browser opens failed. Python requests failed certificate verification, then returned **HTTP 403** with verification disabled. HTML unavailable. [Official notice][s6]

3. **Accessible institutional drafting guidance:** Yugra's 45-page PDF opened. Title page: **2007**, second edition. Screenshot retrieval failed. [Institutional publication][s1]

4. **Unverified newer guidance:** `https://duma.gov.ru/media/files/9Sc61P4yf42i9INdk8GHYItzqb3hwMEF.pdf` returned a browser internal error and a direct HTTPS read timeout. The official portal's June 2021 news index confirms that drafting recommendations were posted, but its direct page and the information section could not be opened. The complete 2021 official text was not retrieved, and no claim of its exact current wording is made. [Official portal notice][s17]

5. **Other KSRF sources:** indexed excerpts retrieved; direct electoral/prosecution/referendum opens failed. The institutional-report PDF timed out. [Electoral text][s11], [prosecution text][s12], [referendum text][s16], [report][s9]

6. **Accessible court evidence:** Supreme Court reviews, Plenum texts, abbreviation extracts, and appeal АПЛ25-42 opened as HTML/PDF text. [2012 review][s3], [2005 review][s13], [Plenum 2014][s4], [Plenum 2012][s10], [decision extract][s14], [appeal][s5]

7. **Rules not established:** universal letter skipping; universal interpretation of shortened dotted ranges; universal superscript/dot/hyphen equivalence; exhaustive anaphora or coordination resolution; and complete coverage of free prose or hidden benchmarks. These remain limitations, not inferred guarantees.

## Primary-source register

The links below are also used next to the claims above. “Indexed” records a retrieval limitation, not a different publisher.

| Key | Publisher / document | Useful locator | Retrieval |
|---|---|---|---|
| S1 | State Duma drafting recommendations/commentary, 2007 edition, hosted by Yugra Duma | §§9, 12, 23–28, 70 | PDF extracted text |
| S2 | Supreme Court review approved 28 September 2016 | printed pp. 1, 3 | PDF extracted text |
| S3 | Supreme Court review for second quarter 2012, approved 10 October 2012 | printed p. 79 | PDF extracted text |
| S4 | Plenum VAS resolution No. 50, 18 July 2014, on official Supreme Court site | §33 | HTML |
| S5 | Supreme Court appeal No. АПЛ25-42, 13 March 2025 | pp. 1–4 | PDF extracted text |
| S6 | KSRF notice 19406 | labour-code and КоАП references | Indexed |
| S7 | Electoral-guarantees law on KSRF site | articles 3–6 | Indexed |
| S8 | Supreme Court document 2273344 | administrative-regulation points | Indexed |
| S9 | KSRF institutional report for 2020 | criminal-law superscript article references | Indexed PDF text |
| S10 | Supreme Court Plenum No. 30, 11 December 2012 | §§24–25 | HTML |
| S11 | Electoral-guarantees law on KSRF site | Chapter VIII, donation restrictions | Indexed |
| S12 | Prosecution law on KSRF site | Section V, service provisions | Indexed |
| S13 | Supreme Court fourth-quarter 2005 review | Parenkov case discussion | HTML |
| S14 | Supreme Court case АКПИ12-1326 official extract | heading distinguishing marker abbreviations | HTML |
| S15 | Presidium VAS ruling No. 17630/12, 18 June 2013, on Supreme Court site | shortened code-name introduction | Indexed |
| S16 | Referendum law on KSRF site | Chapter XV, article 93 | Indexed |
| S17 | Official legal-information portal, June 2021 news | notice dated 8 June 2021 | Indexed |

[s1]: https://www.dumahmao.ru/ai_fill/File/Forms%20of%20documents/Comments.pdf
[s2]: https://vsrf.ru/Show_pdf.php?Id=11033
[s3]: https://www.vsrf.ru/Show_pdf.php?Id=8197
[s4]: https://www.vsrf.ru/documents/all/17747
[s5]: https://vsrf.ru/lk/practice/stor_pdf/2450698
[s6]: https://www.ksrf.ru/news/19406/
[s7]: https://ksrf.ru/about/legalbases/Guarantee/Article3.php
[s8]: https://vsrf.ru/lk/practice/stor_pdf/2273344
[s9]: https://www.ksrf.ru/about/Maintenance/Documents/%D0%98%D0%BD%D1%84%D0%BE%D1%80%D0%BC%D0%B0%D1%86%D0%B8%D1%8F%202020.pdf
[s10]: https://www.vsrf.ru/files/14106/
[s11]: https://www.ksrf.ru/about/legalbases/Guarantee/Chapter8.php
[s12]: https://www.ksrf.ru/about/legalbases/PublicProsecutor/Chapter5.php
[s13]: https://www.vsrf.ru/documents/all/15064
[s14]: https://www.vsrf.ru/files/14366/
[s15]: https://www.vsrf.ru/documents/arbitration/19742/
[s16]: https://www.ksrf.ru/about/legalbases/Referendum/Chapter15.php
[s17]: https://pravo.gov.ru/news/?month=6&year=2021&ysclid=lvid1mx33u191506527
[readme]: ../README.md
[design]: parser-design.md
