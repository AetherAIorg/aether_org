# Margin SDK

Python client for the Margin MetricGraph API — ingest sources, declare context, and query the Neo4j knowledge graph.

## Install

```bash
pip install margin
```

Or from source:

```bash
cd margin_sdk && pip install -e ".[dev]"
```

## Quickstart

```python
import margin
import os

margin.configure(
    api_key=os.environ["MARGIN_API_KEY"],
    base_url=os.environ.get("MARGIN_BASE_URL", "https://margin-api.onrender.com"),
)

client = margin.Client()
client.ingest("./fund_models")
client.declare(owner="Investment Ops", team="investment-operations")
client.context.link("Fund-Level Net IRR", uses_table="fund_cashflows_v2")
client.sync()
print(client.graph.context("Fund-Level Net IRR"))
```

## Publish to PyPI

Tag a release to trigger CI:

```bash
git tag margin-v0.1.0 && git push origin margin-v0.1.0
```

Or manually:

```bash
cd margin_sdk && python -m build && twine upload dist/*
```
