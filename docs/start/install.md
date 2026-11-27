# Install Netbone

Use Python 3.11 or later. The distribution and import are both named
`netbone`. The core dependencies are NetworkX and pandas.

!!! note "Install from source"
    These instructions target the 0.3.0 source tree. Install from a checkout
    to get the pipeline API and local web app described here. The
    [0.2.3 PyPI release](https://pypi.org/project/netbone/0.2.3/) belongs to
    the earlier GitLab codebase.

## Install from source

Clone the [GitHub repository](https://github.com/al1yass2n/netbone) and run the
following from its root.

```bash
python -m venv .venv
```

Activate the environment for your shell.

| Shell | Activation command |
| --- | --- |
| PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Bash or Zsh | `source .venv/bin/activate` |
| Command Prompt | `.venv\Scripts\activate.bat` |

```bash
python -m pip install .
python -c "import netbone; print(netbone.__version__)"
```

You should see `0.3.0` when installing this version of the source tree. The
browser app is included in this install.

## Optional tools

Run the command for the extra you need from the same checkout.

| Extra | Install command | Provides |
| --- | --- | --- |
| `viz` | `python -m pip install ".[viz]"` | Matplotlib plotting helpers |
| `ml` | `python -m pip install ".[ml]"` | scikit-learn for Link Prediction Isolation Forest |
| `dev` | `python -m pip install -e ".[dev]"` | Development and validation tools |
| `docs` | `python -m pip install -e ".[docs]"` | The documentation builder and Python API handler |

Continue with [your first Python backbone](first-backbone.md) or
[launch the browser app](../browser/launch.md).
