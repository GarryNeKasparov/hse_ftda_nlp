# Grammar experiment logs

Run both experiments and retain a separate record for each invocation:

```bash
/tmp/legal-grammar-venv/bin/python tools/run_grammar_experiments.py
```

Run the analyzer and API acceptance suite, then compare the service against the
annotated golden corpus. Inputs, predictions, exact-match results, and console
logs are saved with the run:

```bash
/tmp/legal-grammar-venv/bin/python tools/run_reference_experiment.py
```

Install `requirements-grammar.txt` into that environment first if needed.
Each directory is named with its UTC start time and contains:

- `run.json`: commands, timestamps, exit codes, Python and dependency versions,
  platform information, and SHA-256 hashes of the saved inputs and scripts.
- `reference-grammar.bnf` and `grammar-examples.json`: the exact input snapshots.
- `reference-grammar.lark`: the generated Lark grammar.
- `tools/` and `requirements-grammar.txt`: script and dependency snapshots.
- `grammar-analysis.md` and `lark-grammar-analysis.md`: detailed results,
  including derivation counts, ambiguity witnesses and the LALR diagnostic.
- `*.stdout.log` and `*.stderr.log`: captured console output for each analyzer.

The runner executes the saved scripts against the saved inputs. It creates
a new directory each time; previous runs remain available. A successful run
means the acceptance suite passed and corpus evaluation completed. Exact-match
misses are recorded measurements rather than runner failures. Strict LALR
rejection is an observed grammar result, rather than a runner failure.

`prior-reports/` preserves the reports produced before console logging was
introduced. Their original run timestamps and stdout/stderr were not retained.
Those files are historical reports, not reconstructed execution logs.

The experiment procedure and its limits are explained in
[grammar-experiment-method.md](../../docs/grammar-experiment-method.md).

Reference analyzer runs use `reference-*` directories and snapshot the parser,
grammar, alias dictionary, requirements, golden corpus, acceptance tests, and
runner. They include `golden-evaluation.json` with each expected and predicted
response, exact-match status, and per-example duration. Their `run.json` records
hashes, dependency versions, and timing; stdout and stderr are saved separately.
