# Netbone

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](docs/start/install.md)
[![Total PyPI downloads](https://api.pepy.tech/personalized-badge/netbone?period=TOTAL&units=NONE&left_text=Total%20PyPI%20downloads&left_color=grey&right_color=blue)](https://pepy.tech/projects/netbone)
[![MIT license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Netbone extracts smaller graphs from networks and measures what the reduction
preserves. Work in Python with NetworkX graphs and pandas tables, or launch the
local browser app. Score and select edges or nodes, compare backbones, sweep
settings, and export the results with their analysis configuration.

## Install and run

From a checkout of this repository, using Python 3.11 or later:

```bash
python -m pip install .
netbone-web
```

Open [127.0.0.1:8765](http://127.0.0.1:8765/) or follow the
[Python tutorial](docs/start/first-backbone.md). This repository contains the
0.3.0 source tree. The [0.2.3 PyPI release](https://pypi.org/project/netbone/0.2.3/)
points to the [earlier GitLab codebase](https://gitlab.liris.cnrs.fr/coregraphie/netbone).

## Documentation

- [Read the documentation online](https://al1yass2n.github.io/netbone/)
- [Documentation home](docs/index.md)
- [Install and choose extras](docs/start/install.md)
- [Extract a backbone in the browser](docs/browser/first-session.md)
- [Choose a scoring method](docs/reference/methods.md)
- [Look up Python objects](docs/reference/pipelines.md)
- [Run the documentation site locally](docs/develop.md#preview-and-build)

## Citation and license

If you use or adapt Netbone in published work, cite Yassin, A., Haidar, A.,
Cherifi, H., Seba, H., & Togni, O. (2023), *An evaluation tool for backbone
extraction techniques in weighted complex networks*, Scientific Reports,
13, Article 17000. [Journal article](https://doi.org/10.1038/s41598-023-42076-3)

Ali Yassin authored Netbone. Abbas Haidar and Ali Yassin are the maintainers.
The package uses the [MIT License](LICENSE). See the
[contribution guide](CONTRIBUTING.md) for development information.
