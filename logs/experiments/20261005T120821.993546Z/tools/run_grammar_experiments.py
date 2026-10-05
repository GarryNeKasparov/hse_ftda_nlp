"""Run both grammar analyzers and retain their inputs, reports and console logs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from time import perf_counter

from analyze_grammar import read_grammar, grammar_properties
from analyze_with_lark import lark_grammar


def utc_now() -> str:
    """Return a UTC timestamp for the experiment record."""
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    """Save a new run directory and execute both analyzers with captured output."""
    root = Path(__file__).resolve().parents[1]
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--log-root', type=Path, default=root / 'logs/experiments')
    args = cli.parse_args()
    run_name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run_dir = args.log_root.resolve() / run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        'started_at_utc': utc_now(),
        'invocation': [sys.executable, *sys.argv],
        'workspace': str(root),
        'python_executable': sys.executable,
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'dependencies': {name: version(name) for name in ('lark', 'interegular')},
        'files': {},
        'commands': [],
        'status': 'running',
    }
    snapshot_paths = [
        'docs/reference-grammar.bnf', 'docs/grammar-examples.json',
        'requirements-grammar.txt', 'tools/analyze_grammar.py',
        'tools/analyze_with_lark.py', 'tools/run_grammar_experiments.py',
    ]
    for relative in snapshot_paths:
        source = root / relative
        destination = run_dir / (source.name if relative.startswith('docs/') else relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        metadata['files'][str(destination.relative_to(run_dir))] = {
            'source': relative,
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
    productions = read_grammar(run_dir / 'reference-grammar.bnf')
    properties = grammar_properties(productions)
    generated = run_dir / 'reference-grammar.lark'
    generated.write_text(lark_grammar(productions, properties['terminals']))
    metadata['files'][generated.name] = {
        'source': 'generated from reference-grammar.bnf',
        'sha256': hashlib.sha256(generated.read_bytes()).hexdigest(),
    }
    record = run_dir / 'run.json'
    record.write_text(json.dumps(metadata, indent=2) + '\n')
    # Execute the saved scripts against the saved inputs so later workspace
    # edits cannot change the recorded experiment.
    for script, report in [('analyze_grammar.py', 'grammar-analysis.md'),
                           ('analyze_with_lark.py', 'lark-grammar-analysis.md')]:
        command = [sys.executable, str(run_dir / 'tools' / script),
                   '--grammar', str(run_dir / 'reference-grammar.bnf'),
                   '--examples', str(run_dir / 'grammar-examples.json'),
                   '--output', str(run_dir / report)]
        started = utc_now()
        timer = perf_counter()
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        duration = perf_counter() - timer
        log_name = Path(script).stem
        (run_dir / f'{log_name}.stdout.log').write_text(result.stdout)
        (run_dir / f'{log_name}.stderr.log').write_text(result.stderr)
        metadata['commands'].append({
            'argv': command, 'cwd': str(root), 'started_at_utc': started,
            'finished_at_utc': utc_now(), 'duration_seconds': duration,
            'exit_code': result.returncode,
            'stdout': f'{log_name}.stdout.log', 'stderr': f'{log_name}.stderr.log',
            'report': report,
        })
        record.write_text(json.dumps(metadata, indent=2) + '\n')
        print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
    metadata['finished_at_utc'] = utc_now()
    metadata['status'] = ('passed' if all(command['exit_code'] == 0
                                        for command in metadata['commands']) else 'failed')
    record.write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Run log: {run_dir}')
    return 0 if metadata['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
