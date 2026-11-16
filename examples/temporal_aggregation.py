from __future__ import annotations

from pathlib import Path

import netbone as nb


def main() -> dict[str, object]:
    """Run temporal weighting followed by an ordinary backbone pipeline."""

    event_path = Path(__file__).parent / "data" / "temporal_events.csv"
    temporal = nb.from_temporal_edgelist(
        event_path,
        time="time",
        event_weight="magnitude",
    )
    network = nb.aggregate_temporal(
        temporal,
        weighting="persistent_weibull",
        evaluation_time=2,
        persistent_level=0.2,
        scale=2,
        shape=2,
    )
    result = (
        nb.pipeline()
        .score("edge_weight", weight="weight")
        .filter("fraction", fraction=0.5, tie_policy="exact_stable")
        .run(network)
    )
    metadata = network.metadata["temporal_aggregation"]
    return {
        "weighting": metadata["weighting"] if isinstance(metadata, dict) else None,
        "edges": sorted(result.graph.edges()),
        "event_count": temporal.event_count,
    }


if __name__ == "__main__":
    print(main())
