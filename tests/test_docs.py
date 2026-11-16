from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import netbone as nb


def test_readme_documentation_links_exist() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\((docs/[^)#]+|examples/[^)#]+|mkdocs\.yml)\)", readme)

    assert links
    assert [link for link in links if not Path(link).exists()] == []


def test_documentation_internal_links_exist() -> None:
    missing_links: list[str] = []

    for path in sorted(Path("docs").rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            target_path = target.split("#", maxsplit=1)[0]
            if not target_path or _is_external_link(target_path):
                continue

            resolved_path = (path.parent / target_path).resolve()
            if not resolved_path.exists():
                missing_links.append(f"{path}: {target}")

    assert missing_links == []


def test_mkdocs_navigation_paths_exist() -> None:
    config = Path("mkdocs.yml").read_text(encoding="utf-8")
    paths = re.findall(r": ([A-Za-z0-9_./-]+\.md)$", config, flags=re.MULTILINE)

    assert paths
    assert [path for path in paths if not (Path("docs") / path).exists()] == []


def test_registered_methods_have_public_docs() -> None:
    documented_methods = {path.stem for path in Path("docs/methods").glob("*.md")}

    assert set(nb.list_methods()) <= documented_methods


def test_registered_filters_have_public_docs() -> None:
    documented_filters = {path.stem for path in Path("docs/filters").glob("*.md")}

    assert set(nb.list_filters()) <= documented_filters


def test_mkdocs_nav_includes_registered_method_and_filter_docs() -> None:
    nav_text = Path("mkdocs.yml").read_text(encoding="utf-8")

    for method_name in nb.list_methods():
        assert f"methods/{method_name}.md" in nav_text
    for filter_name in nb.list_filters():
        assert f"filters/{filter_name}.md" in nav_text


def test_docs_extra_declares_documentation_tooling() -> None:
    pyproject = _parse_toml(Path("pyproject.toml").read_text(encoding="utf-8"))
    docs_dependencies = pyproject["project"]["optional-dependencies"]["docs"]

    assert any(str(dependency).startswith("mkdocs") for dependency in docs_dependencies)
    assert any(
        str(dependency).startswith("mkdocstrings") for dependency in docs_dependencies
    )


def test_source_distribution_manifest_includes_docs_site_config() -> None:
    manifest = Path("MANIFEST.in").read_text(encoding="utf-8")

    assert "include mkdocs.yml" in manifest


def _parse_toml(content: str) -> dict[str, Any]:
    import tomllib

    return tomllib.loads(content)


def _is_external_link(target: str) -> bool:
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target))
