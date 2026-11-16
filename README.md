# Netbone

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](docs/start/install.md)
[![Total PyPI downloads](https://api.pepy.tech/personalized-badge/netbone?period=TOTAL&units=NONE&left_text=Total%20PyPI%20downloads&left_color=grey&right_color=blue)](https://pepy.tech/projects/netbone)
[![MIT license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Extract, compare, and export network backbones with Python or a local web app.

[**Try the web demo**](https://al1yass2n.github.io/netbone/demo/) · [Documentation](https://al1yass2n.github.io/netbone/)

## Use the web app

Install from the current repository and launch the app.

```bash
git clone https://github.com/al1yass2n/netbone.git
cd netbone
python -m pip install .
netbone-web
```

Open [127.0.0.1:8765](http://127.0.0.1:8765/). Pick a built-in example or
open your own network, choose a method and filter, then inspect the backbone.
See the [browser guide](https://al1yass2n.github.io/netbone/browser/first-session/) for a walkthrough.

## Use Python

With the same installation, extract the strongest 25% of links in the
Karate Club network and print a summary.

```python
import networkx as nx
import netbone as nb

backbone = (
    nb.pipeline()
    .score("edge_weight", weight="weight")
    .filter("fraction", fraction=0.25, tie_policy="exact_stable")
    .run(nx.karate_club_graph())
)
print(backbone.summary())
```

## Citation and license

If you use Netbone in published work, cite Yassin, A., Haidar, A.,
Cherifi, H., Seba, H., & Togni, O. (2023), *An evaluation tool for
backbone extraction techniques in weighted complex networks*.
[Journal article](https://doi.org/10.1038/s41598-023-42076-3)

Netbone is distributed under the [MIT License](LICENSE).
