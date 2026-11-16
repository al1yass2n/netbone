# Develop and publish the documentation

Use a checkout of the source repository from its root. Install the extras
in an active [virtual environment](start/install.md).

```bash
python -m pip install -e ".[dev,docs]"
```

## Preview and build

```bash
python -m mkdocs serve --strict
```

Open [127.0.0.1:8000](http://127.0.0.1:8000/). MkDocs reloads changes to the
Markdown and navigation while the server runs. For the same strict build
used in GitHub Actions, run this command.

```bash
python -m mkdocs build --strict
```

The build writes to `site/`. Add pages through `mkdocs.yml` and link to
relative Markdown paths in the source. The Python reference uses
mkdocstrings directives that read signatures and docstrings from `src/`.
Update docstrings when the corresponding public contract changes and run
new examples from an installed environment.

## Run project checks

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
```

The [examples directory](https://github.com/al1yass2n/netbone/tree/HEAD/examples)
contains runnable workflows for extraction, comparison, sweeps, temporal
aggregation, reporting, experiment bundles, and plotting. From the checkout,
run individual examples with Python, for instance
`python examples/parameter_sweep.py`.

If working on the frontend, CI uses Node.js 24. Use `npm ci --prefix web` to
install frontend dependencies and `npm run build --prefix web` to build the
packaged assets. Build assets only if working on the UI or preparing a
package release.

## Publish the static site

From a clean checkout of the revision to publish, build and review the site.
Deploy the contents of `site/` to a static host or use GitHub Pages. Set
`NETBONE_DOCS_SITE_URL` to the public URL, including any path prefix, before
building for publication. This sets the canonical URL and the links on the
404 page.

For GitHub Pages, ensure the `origin` remote points to the publishing
repository. Run these commands with credentials that can push to its
`gh-pages` branch. Substitute your site's URL when publishing from a fork
or to a custom domain.

```bash
export NETBONE_DOCS_SITE_URL=https://al1yass2n.github.io/netbone/
python -m mkdocs gh-deploy --strict
```

In PowerShell, set the variable with
`$env:NETBONE_DOCS_SITE_URL = "https://al1yass2n.github.io/netbone/"`, then
run the same MkDocs command.

The command builds the site and pushes the generated files to `gh-pages`.
For the first deployment, open **Settings → Pages** in the GitHub repository
after the branch has been pushed. Select **Deploy from a branch** and set
the source to `gh-pages` and `/(root)`. The CI documentation job verifies
a build on pushes and pull requests.
[GitHub Pages deployment in MkDocs](https://www.mkdocs.org/user-guide/deploying-your-docs/#project-pages)
