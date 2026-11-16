# Installation

Netbone installs as the Python package `netbone`.

## User Install

Install the package from a local checkout:

```bash
pip install .
```

For editable development against the current source tree:

```bash
pip install -e .
```

The core package depends on NetworkX and pandas.

## Optional Visualization

Plotting helpers use Matplotlib and are intentionally optional:

```bash
pip install -e .[viz]
```

Without the `viz` extra, Netbone still returns plot-ready comparison and sweep
tables. Only calls to `netbone.viz` plotting helpers require Matplotlib.

## Optional Machine Learning

The `link_prediction_iforest` method uses scikit-learn and is intentionally
optional:

```bash
pip install -e .[ml]
```

All other built-in methods remain available without the `ml` extra.

## Development Install

Install development tools for tests, linting, type checking, and builds:

```bash
pip install -e .[dev]
```

Run the project quality gates from the repository root:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
```

## Documentation Install

Install documentation tooling:

```bash
pip install -e .[docs]
```

Serve the documentation locally:

```bash
mkdocs serve
```

Build the static documentation site:

```bash
mkdocs build
```

## Local Web App

The local web app uses the core package dependencies:

```bash
python -m netbone.webapp
```

The installed package also exposes the command:

```bash
netbone-web
```

## Python Versions

Netbone requires Python 3.11 or newer. The package metadata advertises Python
3.11, 3.12, 3.13, and 3.14.
