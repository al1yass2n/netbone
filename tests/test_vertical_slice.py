from __future__ import annotations

import pandas as pd

import netbone as nb


def test_csv_to_backbone_vertical_slice(tmp_path) -> None:
    path = tmp_path / "network.csv"
    pd.DataFrame(
        [
            {"source": "alice", "target": "bob", "weight": 3},
            {"source": "bob", "target": "carol", "weight": 1},
            {"source": "carol", "target": "dana", "weight": 2},
        ]
    ).to_csv(path, index=False)

    network = nb.from_edgelist(path, source="source", target="target", weight="weight")
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

    assert method_result.statistics[["source", "target", "score"]].to_dict(
        orient="records"
    ) == [
        {"source": "alice", "target": "bob", "score": 3.0},
        {"source": "bob", "target": "carol", "score": 1.0},
        {"source": "carol", "target": "dana", "score": 2.0},
    ]
    assert sorted(result.graph.edges()) == [("alice", "bob"), ("carol", "dana")]
    assert sorted(result.graph.nodes()) == ["alice", "bob", "carol", "dana"]
    assert result.to_dict()["method_result"]["statistics"]["row_count"] == 3
