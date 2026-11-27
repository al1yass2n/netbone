"""Method references stay complete and consistent across code, docs, and app."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pytest

import netbone as nb
from netbone.webapp.bridge import ui_schema_payload

DOCS = Path(__file__).resolve().parents[1] / "docs" / "methods"
BASELINES = {"edge_weight"}


@pytest.mark.parametrize("name", nb.list_methods())
def test_every_method_cites_its_source(name: str) -> None:
    metadata = nb.describe_method(name)
    references = metadata["references"]

    if name in BASELINES:
        assert references == ()
        assert metadata["reference"] is None
        assert metadata["doi"] is None
        assert metadata["reference_note"]
        return

    assert references
    assert metadata["reference"] == references[0]["citation"]
    assert metadata["doi"] == references[0]["doi"]
    for reference in references:
        assert reference["citation"].strip()
        assert reference["doi"].startswith("10.")
        assert reference["url"] == f"https://doi.org/{reference['doi']}"
    json.dumps(metadata)


@pytest.mark.parametrize("name", nb.list_methods())
def test_every_method_page_lists_the_metadata_references(name: str) -> None:
    page = (DOCS / f"{name}.md").read_text(encoding="utf-8")
    metadata = nb.describe_method(name)

    assert "\n## References\n" in page
    for reference in metadata["references"]:
        assert reference["citation"] in page
        assert f"({reference['url']})" in page
    if metadata.get("reference_note"):
        assert str(metadata["reference_note"]) in page


def test_web_method_cards_carry_the_references() -> None:
    cards = {card["name"]: card for card in ui_schema_payload()["methods"]}

    for name in nb.list_methods():
        metadata = nb.describe_method(name)
        assert cards[name]["references"] == [
            dict(reference) for reference in metadata["references"]
        ]
        assert cards[name]["reference_note"] == metadata.get("reference_note")


def test_report_lists_every_method_reference() -> None:
    graph = nx.Graph()
    graph.add_weighted_edges_from([("a", "b", 3.0), ("b", "c", 2.0), ("c", "a", 1.0)])
    result = (
        nb.pipeline().score("node_betweenness").filter("fraction", fraction=0.5)
    ).run(graph)
    method = nb.report(result).to_dict()["sections"]["method"]

    assert [reference["doi"] for reference in method["references"]] == [
        "10.2307/3033543",
        "10.1080/0022250X.2001.9990249",
    ]
    assert "Brandes, U. (2001)" in nb.report(result).to_markdown()


def test_docs_and_app_share_one_bibtex_entry() -> None:
    root = Path(__file__).resolve().parents[1]
    page = (root / "docs" / "index.md").read_text(encoding="utf-8")
    docs_entry = page.split("```bibtex\n", 1)[1].split("```", 1)[0]
    footer = (root / "web" / "src" / "components" / "CitationFooter.tsx").read_text(
        encoding="utf-8"
    )
    doi = footer.split('const doi = "', 1)[1].split('"', 1)[0]
    app_entry = footer.split("const bibtex = `", 1)[1].split("`;", 1)[0]

    assert docs_entry == app_entry.replace("${doi}", doi)
