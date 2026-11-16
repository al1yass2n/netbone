"""Run a small deterministic Netbone reporting workflow."""

from __future__ import annotations

from tempfile import TemporaryDirectory

import networkx as nx

import netbone as nb


def main() -> dict[str, object]:
    """Generate and save a Markdown report, returning inspectable outputs."""

    graph = nx.Graph()
    graph.add_edge("alice", "bob", weight=4.0)
    graph.add_edge("bob", "carol", weight=2.0)
    graph.add_edge("carol", "dana", weight=1.0)

    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("threshold", value=2.0, operator="greater_equal")
        .run(graph)
    )
    report = nb.report(result)

    with TemporaryDirectory() as directory:
        report_path = report.write_markdown(f"{directory}/backbone_report.md")
        markdown = report_path.read_text(encoding="utf-8")

    output = {
        "subject_type": report.to_dict()["subject_type"],
        "title": report.to_dict()["title"],
        "markdown_heading": markdown.splitlines()[0],
    }
    print(output)
    return output


if __name__ == "__main__":
    main()
