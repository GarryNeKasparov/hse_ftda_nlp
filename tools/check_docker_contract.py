"""Check that the Dockerfile includes the service files and required port."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
required_sources = (
    "main.py", "reference_parser.py", "semantic_analyzer.py",
    "contextual_resolver.py", "law_link_mapper.py", "docs/reference-grammar.bnf",
    "law_aliases.json", "requirements.txt",
)
missing = [source for source in required_sources
           if not (ROOT / source).is_file() or f"COPY {source} " not in dockerfile]
assert not missing, f"Missing Docker COPY inputs: {missing}"
assert "EXPOSE 8978" in dockerfile, "Docker image must expose port 8978"
assert '"main:app"' in dockerfile and '"--port", "8978"' in dockerfile, (
    "Docker CMD must start the app on port 8978")
print(f"Dockerfile contract: OK ({len(required_sources)} inputs, port 8978)")
