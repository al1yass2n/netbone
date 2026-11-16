# Contributing

Keep changes focused and aligned with the public API. For bug reports, include
the Netbone version and a small example that reproduces the issue.

Before opening a change, run:

```bash
pytest
ruff check .
ruff format --check .
mypy src
python -m build
```

Public behavior changes should include tests and README or docstring updates.
