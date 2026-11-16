"""Run the basic Netbone extraction workflow."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import netbone as nb


def main() -> dict[str, object]:
    """Run a small CSV-to-backbone example and return inspectable outputs."""

    with TemporaryDirectory() as directory:
        edge_list_path = Path(directory) / "network.csv"
        edge_list_path.write_text(
            "\n".join(
                [
                    "source,target,strength",
                    "alice,bob,3",
                    "bob,carol,1",
                    "carol,dana,2",
                ]
            ),
            encoding="utf-8",
        )

        network = nb.from_edgelist(edge_list_path, weight="strength")
        pipeline = (
            nb.pipeline()
            .score("edge_weight", weight="weight")
            .filter(
                "threshold",
                value=2.0,
                operator="greater_equal",
                drop_isolates=False,
            )
        )

        method_result = pipeline.compute(network)
        result = pipeline.run(network)

    output = {
        "scores": method_result.statistics[["source", "target", "score"]].to_dict(
            orient="records"
        ),
        "summary": result.summary(),
        "edges": sorted(result.graph.edges()),
    }
    print(output)
    return output


if __name__ == "__main__":
    main()
