"""Bridge functions between the local web UI and the public netbone API."""

from __future__ import annotations

import csv
import json
import math
import warnings
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, replace
from heapq import nsmallest
from io import BytesIO, StringIO
from itertools import combinations, count
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Any, Literal, cast
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import networkx as nx

import netbone as nb
from netbone._json import JsonValue, json_mapping, json_records, json_value
from netbone.exceptions import NetboneError, ValidationError

MAX_STATISTICS_ROWS = 250
MAX_GRAPH_EDGES = 1000
MAX_LIVE_GRAPH_NODES = 80
MAX_PREVIEW_ROWS = 5
MAX_SCORE_CACHE_ENTRIES = 8
MAX_RESULT_CACHE_ENTRIES = 32
MAX_EXPERIMENT_CACHE_ENTRIES = 4

SOURCE_COLUMN_CANDIDATES = ("source", "from", "src", "origin")
TARGET_COLUMN_CANDIDATES = ("target", "to", "dst", "destination")
WEIGHT_COLUMN_CANDIDATES = (
    "weight",
    "strength",
    "value",
    "capacity",
    "flow",
    "volume",
    "amount",
)
TIME_COLUMN_CANDIDATES = (
    "time",
    "timestamp",
    "datetime",
    "date",
    "snapshot",
    "step",
)
EVENT_WEIGHT_COLUMN_CANDIDATES = (
    "event_weight",
    "magnitude",
    *WEIGHT_COLUMN_CANDIDATES,
)

METHOD_DESCRIPTIONS: dict[str, str] = {
    "disparity": "Local p-value backbone for weighted directed or undirected networks.",
    "doubly_stochastic": "Connected backbone from doubly stochastic edge weights.",
    "edge_betweenness": "Ranks edges by shortest-path betweenness.",
    "edge_weight": "Uses the edge weight directly as the score.",
    "glanb": "Globally and locally adaptive statistical backbone.",
    "gspar": "Jaccard-style sparsification using open neighborhoods.",
    "h_backbone": "Structural h-index style edge selection.",
    "lans": "Locally adaptive network sparsification.",
    "link_prediction": "Scores existing links with a selected similarity index.",
    "link_prediction_iforest": (
        "Finds anomalous links across one or more similarity indices."
    ),
    "link_salience": "Ranks edges by salience across shortest-path trees.",
    "marginal_likelihood": "Marginal-likelihood statistical backbone.",
    "noise_corrected": "Find edges that carry more interactions than expected.",
    "maximum_spanning_forest": "Keeps a maximum spanning forest per component.",
    "multiple_linkage": "Selects globally strongest linkage levels by COD.",
    "node_betweenness": "Scores nodes by shortest-path betweenness.",
    "node_degree": "Scores nodes by incident edge count.",
    "node_strength": "Scores nodes by incident edge weight.",
    "planar_maximally_filtered_graph": (
        "Keeps high-weight edges under planar constraints."
    ),
    "primary_linkage": "Keeps primary strongest links.",
}

METHOD_SCORE_MEANING_TEMPLATES: dict[str, str] = {
    "disparity": (
        "Lower p-values identify {edges} whose {weight} makes up an unusually large "
        "share of the total at the connected {nodes}, compared with the {weight} of "
        "their other {edges}; higher values mean less evidence of local importance. "
        "On directed networks, the source uses outgoing weights and the target uses "
        "incoming weights."
    ),
    "doubly_stochastic": (
        "Higher scores mean {edges} retain greater relative importance after "
        "balancing how the {weight} is distributed across the {nodes}; lower scores "
        "mean less importance after that balancing."
    ),
    "edge_betweenness": (
        "Higher scores mean {edges} carry a larger share of shortest routes between "
        "pairs of {nodes}; lower scores mean most shortest routes avoid them."
    ),
    "edge_weight": (
        "Higher scores mean larger original {weight} on the {edges}; lower scores "
        "mean smaller original {weight}."
    ),
    "glanb": (
        "Lower p-values mean {edges} participate in an unusually large share of "
        "shortest paths starting from one or both connected {nodes}, after accounting "
        "for how many connections they have; higher values mean weaker path-based "
        "importance."
    ),
    "gspar": (
        "Higher scores mean the connected {nodes} share many neighbors relative to "
        "their total distinct neighbors; lower scores mean little or no "
        "neighborhood overlap."
    ),
    "h_backbone": (
        "Values of 1 identify {edges} considered important because they are either "
        "strong or help connect otherwise separated parts of the network; values of "
        "0 mean neither type of importance was high enough. This is a binary "
        "selection indicator, not a continuous ranking."
    ),
    "lans": (
        "Lower p-values mean {edges} take an unusually large share of the {weight} "
        "of the connected {nodes}, compared with their other {edges}; higher values "
        "mean their local share is less exceptional."
    ),
    "link_prediction": (
        "Higher scores mean the surrounding network provides stronger structural "
        "support for the observed {edges}; lower scores mean weaker structural "
        "support."
    ),
    "link_prediction_iforest": (
        "Higher scores mean the selected similarity values of the {edges} are more "
        "unusual than those of other {edges}; an anomaly may be unusually high, low, "
        "or unusual in combination. Lower scores mean more typical similarities."
    ),
    "link_salience": (
        "Higher scores mean {edges} appear in shortest-path trees from a larger share "
        "of the {nodes}; lower scores mean they matter to fewer starting {nodes}."
    ),
    "marginal_likelihood": (
        "Lower p-values mean the {edges} carry more activity, measured as {weight}, "
        "than expected from the total activity of the connected {nodes}; higher "
        "values mean the observed activity is less surprising."
    ),
    "noise_corrected": (
        "Higher scores mean {edges} carry more {weight} than expected from the "
        "total interactions at both endpoints, relative to estimated uncertainty."
    ),
    "maximum_spanning_forest": (
        "Values of 1 identify {edges} used to preserve connectivity with the strongest "
        "available links and without redundant cycles; values of 0 identify those "
        "outside that skeleton. This is a binary indicator, not a ranking."
    ),
    "multiple_linkage": (
        "Values of 1 identify {edges} included in the locally strongest set of one or "
        "both connected {nodes}; values of 0 mean neither includes them. This is a "
        "binary indicator, not a ranking."
    ),
    "node_betweenness": (
        "Higher scores mean the {nodes} lie on a larger share of shortest routes "
        "between other {nodes}; lower scores mean they provide less shortest-path "
        "bridging."
    ),
    "node_degree": (
        "Higher scores mean the {nodes} have more direct {edges}; lower scores mean "
        "fewer direct {edges}."
    ),
    "node_strength": (
        "Higher scores mean the {nodes} have a larger total {weight} across their "
        "direct {edges}; lower scores mean a smaller total {weight}."
    ),
    "planar_maximally_filtered_graph": (
        "Values of 1 identify {edges} retained among the strongest links while keeping "
        "the simplified network planar, meaning it can be drawn without crossing "
        "links; values of 0 identify those not retained. This is a binary indicator, "
        "not a ranking."
    ),
    "primary_linkage": (
        "Values of 1 identify {edges} carrying the greatest {weight} for one or both "
        "connected {nodes}; values of 0 mean they are not the primary connection of "
        "either. This is a binary indicator, not a ranking."
    ),
}

METHOD_APPROACHES: dict[str, tuple[str, ...]] = {
    "disparity": ("statistical",),
    "doubly_stochastic": ("structural",),
    "edge_betweenness": ("structural", "shortest_paths"),
    "edge_weight": ("direct_measure",),
    "glanb": ("statistical", "shortest_paths"),
    "gspar": ("structural",),
    "h_backbone": ("structural", "shortest_paths"),
    "lans": ("statistical",),
    "link_prediction": ("link_prediction",),
    "link_prediction_iforest": ("link_prediction", "anomaly_detection"),
    "link_salience": ("structural", "shortest_paths"),
    "marginal_likelihood": ("statistical",),
    "noise_corrected": ("statistical",),
    "maximum_spanning_forest": ("structural",),
    "multiple_linkage": ("structural",),
    "node_betweenness": ("structural", "shortest_paths"),
    "node_degree": ("direct_measure",),
    "node_strength": ("direct_measure",),
    "planar_maximally_filtered_graph": ("structural",),
    "primary_linkage": ("structural",),
}

METHOD_APPROACH_OPTIONS = (
    {"value": "statistical", "label": "Statistical"},
    {"value": "structural", "label": "Structural"},
    {"value": "shortest_paths", "label": "Shortest paths"},
    {"value": "direct_measure", "label": "Direct measure"},
    {"value": "link_prediction", "label": "Link prediction"},
    {"value": "anomaly_detection", "label": "Anomaly detection"},
)

STRUCTURAL_DEFAULT_METHODS = {
    "doubly_stochastic",
    "maximum_spanning_forest",
    "primary_linkage",
    "multiple_linkage",
    "planar_maximally_filtered_graph",
    "h_backbone",
}

BINARY_SELECTION_METHODS = {
    "h_backbone",
    "maximum_spanning_forest",
    "multiple_linkage",
    "planar_maximally_filtered_graph",
    "primary_linkage",
}

WEIGHT_PARAMETER_METHODS = {
    "disparity",
    "doubly_stochastic",
    "edge_betweenness",
    "edge_weight",
    "glanb",
    "h_backbone",
    "lans",
    "link_prediction",
    "link_prediction_iforest",
    "link_salience",
    "marginal_likelihood",
    "noise_corrected",
    "maximum_spanning_forest",
    "multiple_linkage",
    "node_betweenness",
    "node_strength",
    "planar_maximally_filtered_graph",
    "primary_linkage",
}

DISTANCE_TRANSFORM_METHODS = {
    "edge_betweenness",
    "h_backbone",
    "link_prediction",
    "link_prediction_iforest",
    "link_salience",
    "node_betweenness",
}

P_VALUE_AGGREGATION_METHODS = {"disparity", "lans"}
FILTER_NAMES = {"default", "fraction", "significance", "threshold"}

METHOD_CONTROL_GUIDANCE: dict[str, dict[str, object]] = {
    "pvalue_aggregation": {
        "description": (
            "Choose how the two endpoint p-values become one edge p-value."
        ),
        "options": {
            "min": {
                "description": (
                    "Use the smaller endpoint value. One endpoint can provide enough "
                    "evidence for the edge."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "i",
                    "left_value": "p = 0.02",
                    "rule": "MIN",
                    "right": "j",
                    "right_value": "p = 0.40",
                    "result": "edge p = 0.02",
                },
            },
            "max": {
                "description": (
                    "Use the larger endpoint value. Both endpoints must provide "
                    "strong evidence for the edge."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "i",
                    "left_value": "p = 0.02",
                    "rule": "MAX",
                    "right": "j",
                    "right_value": "p = 0.40",
                    "result": "edge p = 0.40",
                },
            },
            "average": {
                "description": (
                    "Average both endpoint values to balance their evidence."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "i",
                    "left_value": "p = 0.02",
                    "rule": "MEAN",
                    "right": "j",
                    "right_value": "p = 0.40",
                    "result": "edge p = 0.21",
                },
            },
        },
    },
    "leaf_policy": {
        "description": (
            "Choose how a degree-one node contributes through its only edge."
        ),
        "options": {
            "zero": {
                "description": (
                    "Give the leaf endpoint p-value 0, so its only edge is locally "
                    "significant from that endpoint."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "i",
                    "left_value": "degree 1",
                    "rule": "p_i = 0",
                    "right": "j",
                    "right_value": "p_j = 0.40",
                    "result": "inputs: 0, 0.40",
                },
            },
            "ignore": {
                "description": (
                    "Ignore the leaf endpoint and use the other endpoint when it is "
                    "available."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "i",
                    "left_value": "degree 1",
                    "rule": "ignore p_i",
                    "right": "j",
                    "right_value": "p_j = 0.40",
                    "result": "edge p = 0.40",
                },
            },
        },
    },
    "similarity": {
        "description": (
            "Choose the structural signal used to score each observed edge after "
            "temporarily removing it."
        ),
        "options": {
            "preferential_attachment": {
                "description": (
                    "High values connect endpoints with large degree or weighted "
                    "strength."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "u",
                    "left_value": "degree 4",
                    "rule": "4 x 3",
                    "right": "v",
                    "right_value": "degree 3",
                    "result": "similarity = 12",
                },
            },
            "shortest_path": {
                "description": (
                    "High values mean the endpoints remain close through another "
                    "short route after their edge is removed."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "u",
                    "left_value": "edge removed",
                    "rule": "alternate d = 2",
                    "right": "v",
                    "right_value": "still reachable",
                    "result": "similarity = 0.50",
                },
            },
            "local_path": {
                "description": (
                    "Combine two-step paths with epsilon-weighted three-step paths."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "u",
                    "left_value": "N2 = 2",
                    "rule": "N2=2, N3=1",
                    "right": "v",
                    "right_value": "N3 = 1",
                    "result": "score = 2 + eps",
                },
            },
        },
    },
    "link_prediction_mode": {
        "description": (
            "Choose which end of the similarity ranking fraction and threshold "
            "filters will retain. Similarity scores do not change."
        ),
        "options": {
            "high_similarity": {
                "description": ("Retain edges with the strongest structural support."),
                "illustration": {
                    "kind": "rank",
                    "active": "high",
                    "left": "low",
                    "right": "high retained",
                },
            },
            "low_similarity": {
                "description": ("Retain edges with the weakest structural support."),
                "illustration": {
                    "kind": "rank",
                    "active": "low",
                    "left": "low retained",
                    "right": "high",
                },
            },
        },
    },
    "distance_transform": {
        "description": (
            "Tell shortest-path calculations whether larger weights mean stronger "
            "connections or longer distances."
        ),
        "options": {
            "inverse": {
                "description": (
                    "Treat weight as connection strength and use its reciprocal as "
                    "path distance."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "u",
                    "left_value": "source",
                    "rule": "w=5 -> 1/w",
                    "right": "v",
                    "right_value": "target",
                    "result": "distance = 0.20",
                },
            },
            "identity": {
                "description": (
                    "Treat the selected weight attribute as an existing path distance."
                ),
                "illustration": {
                    "kind": "endpoint",
                    "left": "u",
                    "left_value": "source",
                    "rule": "w=5 -> as-is",
                    "right": "v",
                    "right_value": "target",
                    "result": "distance = 5",
                },
            },
        },
    },
}

METHOD_PARAMETER_GUIDANCE: dict[tuple[str, str], dict[str, object]] = {
    ("disparity", "pvalue_aggregation"): {
        "description": (
            "Combine the two endpoint tests. On directed graphs these are the "
            "source-outgoing and target-incoming p-values."
        ),
    },
    ("disparity", "leaf_policy"): {
        "description": (
            "Control source out-degree-one and target in-degree-one endpoint tests "
            "on directed graphs, or ordinary degree-one endpoints on undirected "
            "graphs."
        ),
    },
    ("lans", "pvalue_aggregation"): {
        "description": (
            "Combine the two endpoint tests. On directed graphs these are the "
            "source-outgoing and target-incoming p-values."
        ),
    },
    ("lans", "leaf_policy"): {
        "description": (
            "Control source out-degree-one and target in-degree-one endpoint tests "
            "on directed graphs, or ordinary degree-one endpoints on undirected "
            "graphs."
        ),
    },
    ("node_strength", "direction"): {
        "description": (
            "On directed graphs, choose which arcs count toward a node's "
            "strength: incoming, outgoing, or both."
        ),
        "options": {
            "total": {
                "description": "Add incoming and outgoing arc weights.",
                "illustration": {
                    "kind": "equation",
                    "left": "in 3",
                    "center": "+ out 1",
                    "right": "node b",
                    "result": "strength = 4",
                },
            },
            "in": {
                "description": "Add only the weights of arcs that point to the node.",
                "illustration": {
                    "kind": "equation",
                    "left": "in 3",
                    "center": "ignore out 1",
                    "right": "node b",
                    "result": "strength = 3",
                },
            },
            "out": {
                "description": "Add only the weights of arcs that leave the node.",
                "illustration": {
                    "kind": "equation",
                    "left": "out 1",
                    "center": "ignore in 3",
                    "right": "node b",
                    "result": "strength = 1",
                },
            },
        },
    },
    ("glanb", "c"): {
        "description": (
            "Controls how strongly endpoint degree affects GLANB significance. "
            "It does not change shortest paths or involvement."
        ),
        "illustration": {
            "kind": "scale",
            "left": "c = 0",
            "center": "degree effect",
            "right": "stronger as c grows",
        },
    },
    ("link_prediction_iforest", "n_estimators"): {
        "description": (
            "More isolation trees usually stabilize anomaly scores but take longer."
        ),
        "illustration": {
            "kind": "stack",
            "left": "fewer / faster",
            "center": "T1 T2 T3",
            "right": "more / steadier",
        },
    },
    ("link_prediction_iforest", "random_state"): {
        "description": (
            "Use the same seed to reproduce the same isolation-forest scores."
        ),
        "illustration": {
            "kind": "repeat",
            "left": "seed 7",
            "center": "run again",
            "right": "same scores",
        },
    },
    ("link_prediction_iforest", "bootstrap"): {
        "description": ("When enabled, each tree samples edges with replacement."),
        "illustration": {
            "kind": "toggle",
            "left": "off: no replacement",
            "right": "on: repeats allowed",
        },
    },
    ("edge_betweenness", "normalized"): {
        "description": (
            "Scale betweenness by graph size for easier cross-graph comparison."
        ),
        "illustration": {
            "kind": "equation",
            "left": "raw = 4",
            "center": "/ graph scale 10",
            "right": "normalized",
            "result": "0.40",
        },
    },
    ("node_betweenness", "normalized"): {
        "description": (
            "Scale betweenness by graph size for easier cross-graph comparison."
        ),
        "illustration": {
            "kind": "equation",
            "left": "raw = 6",
            "center": "/ graph scale 6",
            "right": "normalized",
            "result": "1.00",
        },
    },
    ("node_betweenness", "endpoints"): {
        "description": (
            "Include path endpoints in each node's betweenness contribution."
        ),
        "illustration": {
            "kind": "path",
            "left": "s: endpoint",
            "rule": "m: middle",
            "right": "t: endpoint",
            "result": "off: m | on: s, m, t",
        },
    },
    ("link_prediction", "epsilon"): {
        "description": (
            "Sets how much three-step paths contribute to Local Path similarity."
        ),
        "illustration": {
            "kind": "equation",
            "left": "N2 = 2",
            "center": "+ eps x N3 (1)",
            "right": "eps = 0.5",
            "result": "score = 2.5",
        },
    },
    ("link_prediction_iforest", "epsilon"): {
        "description": (
            "Sets how much three-step paths contribute when Local Path is selected."
        ),
        "illustration": {
            "kind": "equation",
            "left": "N2 = 2",
            "center": "+ eps x N3 (1)",
            "right": "eps = 0.5",
            "result": "score = 2.5",
        },
    },
    ("doubly_stochastic", "epsilon"): {
        "description": (
            "Adds positive scale-relative smoothing before Sinkhorn balancing."
        ),
        "illustration": {
            "kind": "equation",
            "left": "mean weight = 10",
            "rule": "x eps (0.0001)",
            "right": "smoothing = 0.001",
            "result": "add, then balance",
        },
    },
}

IFOREST_FEATURE_GUIDANCE: dict[str, dict[str, object]] = {
    "iforest_similarity_preferential_attachment": {
        "description": (
            "Include endpoint degree or strength product as an anomaly feature."
        ),
        "illustration": {
            "kind": "endpoint",
            "left": "u",
            "left_value": "degree 4",
            "rule": "4 x 3",
            "right": "v",
            "right_value": "degree 3",
            "result": "feature = 12",
        },
    },
    "iforest_similarity_shortest_path": {
        "description": (
            "Include alternate shortest-path closeness as an anomaly feature."
        ),
        "illustration": {
            "kind": "endpoint",
            "left": "u",
            "left_value": "edge removed",
            "rule": "alternate d = 2",
            "right": "v",
            "right_value": "still reachable",
            "result": "feature = 0.50",
        },
    },
    "iforest_similarity_local_path": {
        "description": (
            "Include local two-step and three-step path support as a feature."
        ),
        "illustration": {
            "kind": "endpoint",
            "left": "u",
            "left_value": "N2 = 2",
            "rule": "N2=2, N3=1",
            "right": "v",
            "right_value": "N3 = 1",
            "result": "feature = 2 + eps",
        },
    },
}


@dataclass(frozen=True)
class _ScoreCacheEntry:
    network: nb.Network
    scores: nb.MethodResult
    pipeline: nb.Pipeline
    weight: str | None


@dataclass(frozen=True)
class _Download:
    content: bytes
    content_type: str
    filename: str


@dataclass(frozen=True)
class _WebExperiment:
    subject: nb.Comparison | nb.SweepResult
    files: Mapping[str, object]
    kind: Literal["comparison", "sweep"]


_SCORE_CACHE: OrderedDict[str, _ScoreCacheEntry] = OrderedDict()
_SCORE_CACHE_LOCK = Lock()
_SCORE_COUNTER = count(1)
_RESULT_CACHE: OrderedDict[str, nb.BackboneResult] = OrderedDict()
_RESULT_CACHE_LOCK = Lock()
_RESULT_COUNTER = count(1)
_EXPERIMENT_CACHE: OrderedDict[str, _WebExperiment] = OrderedDict()
_EXPERIMENT_CACHE_LOCK = Lock()


def registry_payload() -> dict[str, JsonValue]:
    """Return raw method, filter, and temporal metadata for advanced consumers."""

    return {
        "methods": {
            name: json_mapping(nb.describe_method(name))
            for name in sorted(nb.list_methods())
        },
        "filters": {
            name: json_mapping(nb.describe_filter(name))
            for name in sorted(nb.list_filters())
        },
        "temporal_weightings": {
            name: json_mapping(nb.describe_temporal_weighting(name))
            for name in sorted(nb.list_temporal_weightings())
        },
    }


def ui_schema_payload() -> dict[str, JsonValue]:
    """Return guided web UI metadata derived from the registered package API."""

    methods = {name: nb.describe_method(name) for name in sorted(nb.list_methods())}
    cards = {name: _method_card(name, metadata) for name, metadata in methods.items()}

    return {
        "methods": json_value([cards[name] for name in sorted(cards)]),
        "method_filters": json_value({"approaches": list(METHOD_APPROACH_OPTIONS)}),
        "filters": json_value(_filter_cards()),
        "comparison": json_value(
            {
                "single_metrics": [
                    nb.describe_metric(name) for name in nb.list_metrics(scope="single")
                ],
                "pairwise_metrics": [
                    nb.describe_metric(name)
                    for name in nb.list_metrics(scope="pairwise")
                ],
            }
        ),
        "temporal": json_value(_temporal_schema()),
        "controls": json_value(
            {
                "data": _data_controls(),
                "filters": _filter_controls(),
                "methods": {
                    name: _method_controls(name, metadata)
                    for name, metadata in methods.items()
                },
            }
        ),
        "defaults": {
            "method": "edge_weight" if "edge_weight" in methods else sorted(methods)[0],
            "filter": "threshold",
        },
        "capabilities": {
            "graph_export": True,
            "graphml_import": True,
            "directed_to_undirected": True,
            "directed_temporal": True,
            "comparison": True,
        },
    }


def run_pipeline_from_payload(payload: object) -> dict[str, JsonValue]:
    """Run a pipeline from guided web controls or a raw pipeline payload."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    network = _network_from_payload(payload)
    configured_pipeline = _pipeline_from_payload(payload)
    result = configured_pipeline.run(network)
    response = _result_payload(result, weight=_input_weight(payload))
    response["result_id"] = _cache_result(result)
    return response


def score_payload(payload: object) -> dict[str, JsonValue]:
    """Compute method statistics and cache them for subsequent filtering."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    network = _network_from_payload(payload)
    if isinstance(payload.get("guided"), Mapping):
        method_name, method_parameters = _guided_score_config(payload)
    else:
        method_config = _named_config(payload, "method")
        method_name = method_config["name"]
        method_parameters = method_config["parameters"]

    configured_pipeline = nb.pipeline().score(method_name, **method_parameters)
    scores = configured_pipeline.compute(network)
    score_id = _cache_scores(
        network, scores, configured_pipeline, weight=_input_weight(payload)
    )
    pipeline_config = configured_pipeline.to_dict()
    temporal_aggregation = _temporal_aggregation_metadata(network.metadata)
    direction_conversion = _direction_conversion_metadata(network.metadata)
    return {
        "status": "ok",
        "score_id": score_id,
        "network": {
            "node_count": network.graph.number_of_nodes(),
            "edge_count": network.graph.number_of_edges(),
            "directed": network.directed,
        },
        "score_summary": json_mapping(_score_summary(network, scores)),
        "pipeline": json_mapping(pipeline_config),
        "resolved_config": json_value(
            _resolved_web_config(
                pipeline_config,
                temporal_aggregation,
                direction_conversion,
            )
        ),
        "temporal_aggregation": json_value(temporal_aggregation),
        "direction_conversion": json_value(direction_conversion),
        "method_result": json_mapping(scores.to_dict()),
        "extraction": json_mapping(_score_extraction_payload(scores)),
        "warnings": json_value(_network_warnings(network.metadata) + scores.warnings),
        "statistics": json_value(_statistics_payload(scores)),
        "score_ranges": json_mapping(_score_ranges(scores)),
    }


def filter_payload(payload: object) -> dict[str, JsonValue]:
    """Apply a filter to cached method statistics."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    result, score_id, entry = _filtered_result(payload)
    response = _result_payload(result, weight=entry.weight)
    response["score_id"] = score_id
    response["result_id"] = _cache_result(result)
    return response


def comparison_payload(payload: object) -> dict[str, JsonValue]:
    """Compare cached extraction results through the public comparison API."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    entries = payload.get("results")
    if not isinstance(entries, list | tuple) or len(entries) < 2:
        raise ValidationError(
            "Comparison requires at least two saved extraction results."
        )

    named_results: dict[str, nb.BackboneResult] = {}
    normalized_labels: set[str] = set()
    result_summaries: list[dict[str, object]] = []
    for index, raw_entry in enumerate(entries):
        field = f"results[{index}]"
        if not isinstance(raw_entry, Mapping):
            raise ValidationError(f"{field} must be a JSON object.")
        result_id = _required_text(
            raw_entry.get("result_id"), field=f"{field}.result_id"
        )
        label = _required_text(raw_entry.get("label"), field=f"{field}.label").strip()
        if not label:
            raise ValidationError(f"{field}.label cannot be empty.")
        if len(label) > 120:
            raise ValidationError(f"{field}.label cannot exceed 120 characters.")
        normalized_label = label.casefold()
        if normalized_label in normalized_labels:
            raise ValidationError(
                f"Comparison labels must be unique; got {label!r} twice."
            )
        result = _cached_result(result_id)
        normalized_labels.add(normalized_label)
        named_results[label] = result
        result_summaries.append(
            {
                "result_id": result_id,
                "label": label,
                "summary": _web_result_summary(result),
                "extraction": _extraction_payload(result),
            }
        )

    comparison = nb.compare(named_results)
    single_metrics = comparison.table(metrics=nb.list_metrics(scope="single"))
    pairwise_metrics = comparison.pairwise(metrics=nb.list_metrics(scope="pairwise"))
    alignments: list[dict[str, object]] = []
    for result_a, result_b in combinations(named_results, 2):
        try:
            alignment = comparison.score_alignment(result_a, result_b)
        except NetboneError as error:
            alignments.append(
                {
                    "result_a": result_a,
                    "result_b": result_b,
                    "status": "invalid",
                    "explanation": str(error),
                    "points": [],
                }
            )
            continue

        points: list[dict[str, object]] = []
        for row in alignment.to_dict(orient="records"):
            point: dict[str, object] = {
                "value_a": row["value_a"],
                "value_b": row["value_b"],
                "importance_rank_a": row["importance_rank_a"],
                "importance_rank_b": row["importance_rank_b"],
            }
            if row["target"] == "edge":
                point["source"] = row["source_a"]
                point["target"] = row["target_a"]
            else:
                point["node"] = row.get("node", row.get("node_id"))
            points.append(point)
        method_a = named_results[result_a].method_result
        method_b = named_results[result_b].method_result
        alignments.append(
            {
                "result_a": result_a,
                "result_b": result_b,
                "status": "ok",
                "explanation": "",
                "target": method_a.target,
                "output_type_a": method_a.output_type,
                "output_type_b": method_b.output_type,
                "preferred_direction_a": method_a.preferred_direction,
                "preferred_direction_b": method_b.preferred_direction,
                "points": points,
            }
        )
    records = {
        "single_metrics": json_records(single_metrics),
        "pairwise_metrics": json_records(pairwise_metrics),
        "alignments": json_value(alignments),
    }
    settings = {
        "results": [
            {
                "label": label,
                **_web_extraction_settings(result),
                "warnings": result.warnings,
            }
            for label, result in named_results.items()
        ]
    }
    experiment_id = _remember_experiment(
        _WebExperiment(
            comparison,
            {"web_settings.json": settings, "web_comparison_records.json": records},
            "comparison",
        )
    )
    return {
        "status": "ok",
        "experiment_id": experiment_id,
        "results": json_value(result_summaries),
        **records,
    }


def sweep_payload(payload: object) -> dict[str, JsonValue]:
    """Run a reproducible parameter sweep on a cached scored network."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    raw_score_id = payload.get("score_id")
    if raw_score_id is None:
        score_id: str | None = None
        network = _network_from_payload(payload)
    else:
        score_id = _required_text(raw_score_id, field="score_id")
        network = _cached_scores(score_id).network
    variation = _optional_mapping(payload.get("variation"), field="variation")
    scope = _option(
        variation.get("scope"),
        allowed={"configurations", "filter", "grid", "method"},
        default="filter",
        field="variation.scope",
    )

    raw_metrics = payload.get("metrics")
    if not isinstance(raw_metrics, list | tuple) or not raw_metrics:
        raise ValidationError("metrics must contain at least one metric name.")
    metrics = [
        _required_text(metric, field=f"metrics[{index}]")
        for index, metric in enumerate(raw_metrics)
    ]

    variation_payload: dict[str, object]
    setup_names: dict[str, str] = {}
    if scope == "configurations":
        raw_configurations = payload.get("configurations")
        if not isinstance(raw_configurations, list | tuple) or not raw_configurations:
            raise ValidationError(
                "configurations must contain at least one pipeline configuration."
            )
        configured = nb.sweep(network)
        configuration_labels: list[str] = []
        for index, raw_configuration in enumerate(raw_configurations):
            if not isinstance(raw_configuration, Mapping):
                raise ValidationError(f"configurations[{index}] must be a JSON object.")
            label = _required_text(
                raw_configuration.get("name"), field=f"configurations[{index}].name"
            )
            method_config = _named_config(raw_configuration, "method")
            filter_config = _named_config(raw_configuration, "filter")
            if (
                method_config["name"] in WEIGHT_PARAMETER_METHODS
                and "weight" not in method_config["parameters"]
            ):
                method_config["parameters"]["weight"] = (
                    "weight"
                    if _data_mode(payload) == "temporal"
                    else _optional_text(payload.get("weight"), field="weight")
                )
            existing_names = set(
                cast(Mapping[str, object], configured.describe()["configurations"])
            )
            configured = configured.grid(
                methods={method_config["name"]: method_config["parameters"]},
                filters={filter_config["name"]: filter_config["parameters"]},
            )
            generated_names = cast(
                Mapping[str, object], configured.describe()["configurations"]
            )
            setup_names.update(
                {name: label for name in generated_names if name not in existing_names}
            )
            configuration_labels.append(label)
        variation_payload = {
            "scope": "configurations",
            "configurations": configuration_labels,
        }
    elif scope == "grid":
        grid = _optional_mapping(payload.get("grid"), field="grid")
        methods = _sweep_grid_entries(grid.get("methods"), field="grid.methods")
        filters = _sweep_grid_entries(grid.get("filters"), field="grid.filters")
        configured = nb.sweep(network).grid(methods=methods, filters=filters)
        variation_payload = {
            "scope": "grid",
            "methods": list(methods),
            "filters": list(filters),
        }
    else:
        parameter = _required_text(
            variation.get("parameter"), field="variation.parameter"
        )
        raw_values = variation.get("values")
        if not isinstance(raw_values, list | tuple) or len(raw_values) < 2:
            raise ValidationError("variation.values must contain at least two values.")
        if len(raw_values) > 100:
            raise ValidationError(
                "variation.values cannot contain more than 100 values."
            )
        values = list(raw_values)
        if score_id is None:
            raise ValidationError(
                "Legacy one-parameter sweeps require score_id. Use configuration-based "
                "sweeps when starting directly from a dataset."
            )
        entry = _cached_scores(score_id)
        method_name = entry.scores.method_name
        filter_name, filter_parameters = _guided_filter_config(
            payload,
            method_name,
            nb.describe_method(method_name),
        )
        configured = (
            nb.sweep(entry.network)
            .score(method_name, **entry.pipeline.method_parameters)
            .filter(filter_name, **filter_parameters)
        )
        if scope == "filter":
            configured = configured.vary_filter(None, **{parameter: values})
        else:
            configured = configured.vary_method(None, **{parameter: values})
        variation_payload = {
            "scope": scope,
            "parameter": parameter,
            "values": values,
        }
    configured = configured.measure(metrics)
    configuration = configured.describe()
    configuration_count = len(
        cast(Mapping[str, object], configuration["configurations"])
    )
    if configuration_count > 100:
        raise ValidationError(
            "Sweep cannot generate more than 100 configurations in the web app."
        )
    if payload.get("preview_only") is True:
        return {
            "status": "preview",
            "score_id": score_id,
            "variation": json_value(variation_payload),
            "configuration": json_value(configuration),
            "setup_names": json_value(setup_names),
            "score_cache_hits": 0,
            "score_cache_misses": 0,
            "runs": [],
            "metrics": [],
        }
    result = configured.run()
    settings = {
        "context": network.context,
        "resolved_config": _resolved_web_config(
            configuration,
            _temporal_aggregation_metadata(network.metadata),
            _direction_conversion_metadata(network.metadata),
        ),
        "variation": variation_payload,
        "setup_names": setup_names,
        "network_warnings": _network_warnings(network.metadata),
    }
    experiment_id = _remember_experiment(
        _WebExperiment(result, {"web_settings.json": settings}, "sweep")
    )

    return {
        "status": "ok",
        "experiment_id": experiment_id,
        "score_id": score_id,
        "variation": json_value(variation_payload),
        "configuration": json_value(configuration),
        "setup_names": json_value(setup_names),
        "score_cache_hits": result.score_cache_hits,
        "score_cache_misses": result.score_cache_misses,
        "runs": json_records(result.runs),
        "metrics": json_records(result.table()),
    }


def _sweep_grid_entries(
    value: object,
    *,
    field: str,
) -> dict[str, dict[str, object]]:
    if not isinstance(value, Mapping) or not value:
        raise ValidationError(f"{field} must be a non-empty JSON object.")
    entries: dict[str, dict[str, object]] = {}
    for raw_name, raw_parameters in value.items():
        name = _required_text(raw_name, field=f"{field} name")
        if not isinstance(raw_parameters, Mapping):
            raise ValidationError(f"{field}.{name} must be a JSON object.")
        entries[name] = dict(raw_parameters)
    return entries


def filter_preview_payload(payload: object) -> dict[str, JsonValue]:
    """Return exact retention counts, a sampled graph, and the draft configuration."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    result, score_id, _ = _filtered_result(payload)
    original_node_count = result.original_graph.number_of_nodes()
    backbone_node_count = result.graph.number_of_nodes()
    node_coverage_count, node_coverage_fraction = _node_coverage(result)
    total_item_count = len(result.method_result.statistics)
    selected_item_count = len(result.selection.selected_ids)
    return {
        "status": "ok",
        "score_id": score_id,
        "target": result.selection.target,
        "selected_item_count": selected_item_count,
        "total_item_count": total_item_count,
        "selected_item_fraction": (
            selected_item_count / total_item_count if total_item_count else 0.0
        ),
        "node_coverage_count": node_coverage_count,
        "node_coverage_fraction": node_coverage_fraction,
        "backbone_node_count": backbone_node_count,
        "backbone_edge_count": result.graph.number_of_edges(),
        "original_edge_count": result.original_graph.number_of_edges(),
        "backbone_component_count": (
            nx.number_weakly_connected_components(result.graph)
            if result.graph.is_directed()
            else nx.number_connected_components(result.graph)
        ),
        "original_node_count": original_node_count,
        "backbone_node_fraction": (
            backbone_node_count / original_node_count if original_node_count else 0.0
        ),
        "drop_isolates": bool(result.selection.parameters.get("drop_isolates", False)),
        "warnings": json_value(result.warnings),
        "graph": _graph_payload(
            result.original_graph, result.graph, node_limit=MAX_LIVE_GRAPH_NODES
        ),
        "resolved_config": json_mapping(
            _resolved_web_config(
                result.pipeline_config,
                _temporal_aggregation_metadata(result.network_metadata),
                _direction_conversion_metadata(result.network_metadata),
            )
        ),
    }


def graph_export_payload(payload: object) -> _Download:
    """Build an annotated GraphML or GEXF download from cached scores."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    export = _optional_mapping(payload.get("export"), field="export")
    file_format = _option(
        export.get("format"),
        allowed={"graphml", "gexf"},
        default="graphml",
        field="export.format",
    )
    scope = _option(
        export.get("scope"),
        allowed={"annotated", "backbone"},
        default="annotated",
        field="export.scope",
    )
    raw_result_id = payload.get("result_id")
    if raw_result_id is None:
        result, _, _ = _filtered_result(payload)
    else:
        result_id = _required_text(raw_result_id, field="result_id")
        result = _cached_result(result_id)
    graph_name = "original_annotated" if scope == "annotated" else "backbone"
    content_types = {
        "graphml": "application/graphml+xml",
        "gexf": "application/gexf+xml",
    }

    with TemporaryDirectory(prefix="netbone-web-export-") as directory:
        bundle_path = nb.save_experiment(result, Path(directory) / "bundle")
        content = (bundle_path / "graphs" / f"{graph_name}.{file_format}").read_bytes()

    method_name = result.method_result.method_name.replace("_", "-")
    return _Download(
        content=content,
        content_type=content_types[file_format],
        filename=f"netbone-{method_name}-{scope}.{file_format}",
    )


def result_export_payload(payload: object) -> _Download:
    """Download a report or experiment bundle for a completed extraction."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")
    file_format = _required_text(payload.get("format"), field="format")
    if file_format not in {"markdown", "zip"}:
        raise ValidationError("format must be 'markdown' or 'zip'.")
    result_id = _required_text(payload.get("result_id"), field="result_id")
    result = _cached_result(result_id)
    method = result.method_result.method_name.replace("_", "-")

    if file_format == "markdown":
        return _Download(
            content=nb.report(result).to_markdown().encode("utf-8"),
            content_type="text/markdown; charset=utf-8",
            filename=f"netbone-{method}-report.md",
        )

    return _experiment_zip(
        result,
        f"netbone-{method}-experiment.zip",
        {"web_settings.json": _web_extraction_settings(result)},
    )


def _web_extraction_settings(result: nb.BackboneResult) -> dict[str, object]:
    return {
        "context": result.context,
        "resolved_config": _resolved_web_config(
            result.pipeline_config,
            _temporal_aggregation_metadata(result.network_metadata),
            _direction_conversion_metadata(result.network_metadata),
        ),
    }


def _remember_experiment(experiment: _WebExperiment) -> str:
    with _EXPERIMENT_CACHE_LOCK:
        experiment_id = uuid4().hex
        _EXPERIMENT_CACHE[experiment_id] = experiment
        while len(_EXPERIMENT_CACHE) > MAX_EXPERIMENT_CACHE_ENTRIES:
            _EXPERIMENT_CACHE.popitem(last=False)
    return experiment_id


def experiment_export_payload(payload: object) -> _Download:
    """Download the saved snapshot of a completed comparison or sweep."""
    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")
    experiment_id = _required_text(payload.get("experiment_id"), field="experiment_id")
    with _EXPERIMENT_CACHE_LOCK:
        experiment = _EXPERIMENT_CACHE.get(experiment_id)
        if experiment is None:
            raise ValidationError(
                "This experiment is no longer available. Run the comparison or sweep "
                "again, then download its ZIP."
            )
        _EXPERIMENT_CACHE.move_to_end(experiment_id)
    return _experiment_zip(
        experiment.subject,
        f"netbone-{experiment.kind}-experiment.zip",
        experiment.files,
    )


def _experiment_zip(
    subject: nb.BackboneResult | nb.Comparison | nb.SweepResult,
    filename: str,
    files: Mapping[str, object],
) -> _Download:
    content = BytesIO()
    with TemporaryDirectory(prefix="netbone-web-experiment-") as directory:
        bundle = nb.save_experiment(subject, Path(directory) / "bundle")
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name in files:
            manifest["files"][name.replace(".", "_")] = name
        for name, value in {**files, "manifest.json": manifest}.items():
            path = bundle / name
            path.write_text(
                json.dumps(
                    json_value(value), indent=2, ensure_ascii=False, sort_keys=True
                )
                + "\n",
                encoding="utf-8",
            )
        with ZipFile(content, "w") as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    archive.writestr(
                        ZipInfo(path.relative_to(bundle).as_posix()),
                        path.read_bytes(),
                        compress_type=ZIP_DEFLATED,
                    )
    return _Download(
        content=content.getvalue(),
        content_type="application/zip",
        filename=filename,
    )


def _filtered_result(
    payload: Mapping[object, object],
) -> tuple[nb.BackboneResult, str, _ScoreCacheEntry]:
    score_id = _required_text(payload.get("score_id"), field="score_id")
    entry = _cached_scores(score_id)
    if isinstance(payload.get("guided"), Mapping):
        metadata = nb.describe_method(entry.scores.method_name)
        filter_name, filter_parameters = _guided_filter_config(
            payload,
            entry.scores.method_name,
            metadata,
        )
    else:
        filter_config = _named_config(payload, "filter")
        filter_name = filter_config["name"]
        filter_parameters = filter_config["parameters"]

    result = nb.filter_scores(
        entry.network,
        entry.scores,
        strategy=filter_name,
        **filter_parameters,
    )
    config = entry.pipeline.filter(filter_name, **filter_parameters).to_dict()
    return replace(result, pipeline_config=config), score_id, entry


def _result_payload(
    result: nb.BackboneResult, *, weight: str | None
) -> dict[str, JsonValue]:
    statistics = _statistics_payload(
        result.method_result,
        result.selection,
        graph=result.original_graph,
        weight=weight,
    )
    temporal_aggregation = _temporal_aggregation_metadata(result.network_metadata)
    direction_conversion = _direction_conversion_metadata(result.network_metadata)
    return {
        "status": "ok",
        "network": {
            "node_count": result.original_graph.number_of_nodes(),
            "edge_count": result.original_graph.number_of_edges(),
            "directed": result.original_graph.is_directed(),
        },
        "summary": json_mapping(_web_result_summary(result)),
        "pipeline": json_mapping(result.pipeline_config),
        "resolved_config": json_value(
            _resolved_web_config(
                result.pipeline_config,
                temporal_aggregation,
                direction_conversion,
            )
        ),
        "temporal_aggregation": json_value(temporal_aggregation),
        "direction_conversion": json_value(direction_conversion),
        "selection": json_mapping(result.selection.to_dict()),
        "extraction": json_mapping(_extraction_payload(result)),
        "warnings": json_value(result.warnings),
        "statistics": json_value(statistics),
        "graph": _graph_payload(result.original_graph, result.graph),
    }


def _web_result_summary(result: nb.BackboneResult) -> dict[str, object]:
    summary = result.summary()
    node_coverage_count, node_coverage_fraction = _node_coverage(result)
    summary.update(
        {
            "target": result.selection.target,
            "node_coverage_count": node_coverage_count,
            "node_coverage_fraction": node_coverage_fraction,
        }
    )
    return summary


def _node_coverage(result: nb.BackboneResult) -> tuple[int, float]:
    node_count = result.original_graph.number_of_nodes()
    count = result.graph.number_of_nodes()
    if result.selection.target == "edge":
        count -= sum(1 for _ in nx.isolates(result.graph))
    return count, count / node_count if node_count else 0.0


def _extraction_payload(result: nb.BackboneResult) -> dict[str, object]:
    return {
        "method": result.method_result.method_name,
        "filter": result.selection.parameters.get("strategy"),
        "target": result.method_result.target,
        "output_type": result.method_result.output_type,
        "primary_statistic": result.method_result.primary_statistic,
        "filter_statistic": result.selection.statistic,
        "preferred_direction": result.method_result.preferred_direction,
        "selected_count": len(result.selection.selected_ids),
        "rejected_count": len(result.selection.rejected_ids),
        "method_parameters": dict(result.method_result.parameters),
        "filter_parameters": dict(result.selection.parameters),
    }


def _score_extraction_payload(scores: nb.MethodResult) -> dict[str, object]:
    return {
        "method": scores.method_name,
        "filter": None,
        "target": scores.target,
        "output_type": scores.output_type,
        "primary_statistic": scores.primary_statistic,
        "filter_statistic": None,
        "preferred_direction": scores.preferred_direction,
        "method_parameters": dict(scores.parameters),
        "filter_parameters": {},
    }


def _score_summary(network: nb.Network, scores: nb.MethodResult) -> dict[str, object]:
    return {
        "method": scores.method_name,
        "target": scores.target,
        "score_row_count": len(scores.statistics),
        "original_node_count": network.graph.number_of_nodes(),
        "original_edge_count": network.graph.number_of_edges(),
        "directed": network.directed,
    }


def _cache_scores(
    network: nb.Network,
    scores: nb.MethodResult,
    pipeline: nb.Pipeline,
    *,
    weight: str | None,
) -> str:
    score_id = f"score-{next(_SCORE_COUNTER)}"
    with _SCORE_CACHE_LOCK:
        _SCORE_CACHE[score_id] = _ScoreCacheEntry(network, scores, pipeline, weight)
        _SCORE_CACHE.move_to_end(score_id)
        while len(_SCORE_CACHE) > MAX_SCORE_CACHE_ENTRIES:
            _SCORE_CACHE.popitem(last=False)
    return score_id


def _cached_scores(score_id: str) -> _ScoreCacheEntry:
    with _SCORE_CACHE_LOCK:
        try:
            entry = _SCORE_CACHE[score_id]
        except KeyError as exc:
            raise ValidationError(
                f"Score id {score_id!r} is not available. "
                "Compute scores again before filtering."
            ) from exc
        _SCORE_CACHE.move_to_end(score_id)
        return entry


def _cache_result(result: nb.BackboneResult) -> str:
    result_id = f"result-{next(_RESULT_COUNTER)}"
    with _RESULT_CACHE_LOCK:
        _RESULT_CACHE[result_id] = result
        _RESULT_CACHE.move_to_end(result_id)
        while len(_RESULT_CACHE) > MAX_RESULT_CACHE_ENTRIES:
            _RESULT_CACHE.popitem(last=False)
    return result_id


def _cached_result(result_id: str) -> nb.BackboneResult:
    with _RESULT_CACHE_LOCK:
        try:
            result = _RESULT_CACHE[result_id]
        except KeyError as exc:
            raise ValidationError(
                f"Result id {result_id!r} is not available. "
                "Extract the backbone again before comparing or exporting it."
            ) from exc
        _RESULT_CACHE.move_to_end(result_id)
        return result


def _weight_sign(graph: nx.Graph, weight: str | None) -> str | None:
    """Summarize selected weights as positive, nonnegative, or mixed."""

    if weight is None or graph.number_of_edges() == 0:
        return None
    values = [
        float(attributes[weight])
        for _, _, attributes in graph.edges(data=True)
        if _is_finite_number(attributes.get(weight))
    ]
    if len(values) != graph.number_of_edges():
        return "mixed"
    if all(value > 0 for value in values):
        return "positive"
    if all(value >= 0 for value in values):
        return "nonnegative"
    return "mixed"


def preview_payload(payload: object) -> dict[str, JsonValue]:
    """Return parsed CSV readiness metadata for the guided web UI."""

    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    data_mode = _data_mode(payload)
    try:
        if data_mode == "temporal":
            parsed = _temporal_data_from_payload(payload)
        elif data_mode == "graphml":
            parsed = _graphml_data_from_payload(payload)
        else:
            parsed = _csv_graph_from_payload(payload)
    except NetboneError as exc:
        return {
            "status": "ok",
            "valid": False,
            "errors": [str(exc)],
            "warnings": [],
        }

    method_name = _optional_guided_method_name(payload)
    method_metadata = (
        nb.describe_method(method_name) if method_name is not None else None
    )
    warnings, errors = _readiness_messages(
        method_name,
        method_metadata,
        selected_weight="weight" if data_mode == "temporal" else parsed["weight"],
        likely_weight_columns=parsed["likely_weight_columns"],
        directed=parsed["graph"].is_directed(),
    )
    warnings = [*parsed.get("warnings", []), *warnings]
    can_run = not errors
    graph = parsed["graph"]
    selected_weight = "weight" if data_mode == "temporal" else parsed["weight"]
    directed = graph.is_directed()
    component_count = (
        nx.number_weakly_connected_components(graph)
        if directed
        else nx.number_connected_components(graph)
    )
    response: dict[str, JsonValue] = {
        "status": "ok",
        "data_mode": data_mode,
        "valid": True,
        "can_run": can_run,
        "errors": json_value(errors),
        "warnings": json_value(warnings),
        "headers": json_value(parsed["headers"]),
        "suggested_columns": {
            "source": parsed["suggested_source"],
            "target": parsed["suggested_target"],
            "weight": parsed["suggested_weight"],
        },
        "selected_columns": {
            "source": parsed["source"],
            "target": parsed["target"],
            "weight": "weight" if data_mode == "temporal" else parsed["weight"],
        },
        "row_count": parsed["row_count"],
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "directed": directed,
        "source_directed": bool(parsed.get("source_directed", directed)),
        "direction_handling": json_value(parsed.get("direction_handling")),
        "component_count": component_count,
        "weighted": data_mode == "temporal" or parsed["weight"] is not None,
        "positive_integer_weights": selected_weight is not None
        and all(
            _is_finite_number(value) and value > 0 and float(value).is_integer()
            for _, _, attributes in graph.edges(data=True)
            for value in (attributes.get(selected_weight),)
        ),
        "weight_sign": _weight_sign(graph, selected_weight),
        "likely_weight_columns": json_value(parsed["likely_weight_columns"]),
        "records": json_value(parsed["records"]),
    }
    if directed:
        response["weakly_connected_component_count"] = component_count
        response["strongly_connected_component_count"] = (
            nx.number_strongly_connected_components(graph)
        )
    if data_mode == "temporal":
        response["event_count"] = parsed["event_count"]
        response["selected_columns"] = {
            "source": parsed["source"],
            "target": parsed["target"],
            "time": parsed["time"],
            "event_weight": parsed["event_weight"],
            "weight": "weight",
        }
        response["suggested_columns"] = {
            "source": parsed["suggested_source"],
            "target": parsed["suggested_target"],
            "time": parsed["suggested_time"],
            "event_weight": parsed["suggested_event_weight"],
        }
        response["temporal_aggregation"] = json_value(parsed["temporal_aggregation"])
    elif data_mode == "graphml":
        response["edge_attributes"] = json_value(parsed["edge_attributes"])
        response["numeric_edge_attributes"] = json_value(
            parsed["numeric_edge_attributes"]
        )
        response["node_attributes"] = json_value(parsed["node_attributes"])
    return response


def error_payload(error: Exception) -> dict[str, JsonValue]:
    """Return a deterministic error payload for the web API."""

    return {
        "status": "error",
        "error": error.__class__.__name__,
        "message": str(error),
    }


def _method_card(name: str, metadata: Mapping[str, object]) -> dict[str, object]:
    output_type = _metadata_text(metadata, "output_type", default="custom")
    default_filter = _recommended_filter(name, metadata)
    primary_statistic = _primary_statistic(metadata)
    score_meaning_template = METHOD_SCORE_MEANING_TEMPLATES.get(
        name,
        "Higher values mean greater importance under the registered method "
        "semantics; lower values mean less importance.",
    )
    default_filter_parameters = metadata.get("default_filter_parameters", {})
    if not isinstance(default_filter_parameters, Mapping):
        default_filter_parameters = {}
    return {
        "name": name,
        "label": _friendly_label(name),
        "description": METHOD_DESCRIPTIONS.get(name, _friendly_label(name)),
        "meaning_template": score_meaning_template,
        "score_meaning_template": score_meaning_template,
        "score_interpretation": (
            "binary_selection" if name in BINARY_SELECTION_METHODS else output_type
        ),
        "approaches": list(METHOD_APPROACHES.get(name, ("structural",))),
        "target": _metadata_text(metadata, "target", default="edge"),
        "output_type": output_type,
        "preferred_direction": _metadata_text(
            metadata,
            "preferred_direction",
            default="higher",
        ),
        "primary_statistic": primary_statistic,
        "requires_weights": bool(metadata.get("requires_weights", False)),
        "requires_integer_weights": bool(
            metadata.get("requires_integer_weights", False)
        ),
        "requires_positive_weights": bool(
            metadata.get("requires_positive_weights", False)
        ),
        "requires_nonnegative_weights": bool(
            metadata.get("requires_nonnegative_weights", False)
        ),
        "supports_weighted": bool(metadata.get("supports_weighted", False)),
        "supports_directed": bool(metadata.get("supports_directed", False)),
        "directed_semantics": metadata.get("directed_semantics"),
        "recommended_filter": default_filter,
        "default_filter_parameters": dict(default_filter_parameters),
        "filter_reason": _filter_reason(default_filter, output_type, name),
    }


def _filter_cards() -> list[dict[str, object]]:
    return [
        {
            "name": "threshold",
            "label": "Threshold",
            "description": "Keep values that pass a numeric cutoff.",
        },
        {
            "name": "fraction",
            "label": "Retained Fraction",
            "description": (
                "Keep the strongest selected fraction, with explicit tie policy."
            ),
        },
        {
            "name": "significance",
            "label": "Significance",
            "description": "Keep p-values strictly below alpha.",
        },
        {
            "name": "default",
            "label": "Method Default",
            "description": "Use the method's registered default extraction rule.",
        },
    ]


def _data_controls() -> list[dict[str, object]]:
    return [
        {
            "name": "source",
            "label": "Source column",
            "control": "column_select",
            "required": True,
        },
        {
            "name": "target",
            "label": "Target column",
            "control": "column_select",
            "required": True,
        },
        {
            "name": "weight",
            "label": "Weight column",
            "control": "optional_column_select",
            "required": False,
        },
        {
            "name": "delimiter",
            "label": "Delimiter",
            "control": "select",
            "default": ",",
            "options": [
                {"value": ",", "label": "Comma"},
                {"value": ";", "label": "Semicolon"},
                {"value": "\t", "label": "Tab"},
            ],
        },
        {
            "name": "direction_mode",
            "label": "Direction handling",
            "control": "select",
            "default": "preserve",
            "options": [
                {"value": "preserve", "label": "Keep directed arcs"},
                {"value": "undirected", "label": "Convert to undirected"},
            ],
        },
        {
            "name": "reciprocal_merge",
            "label": "Reciprocal weights",
            "control": "select",
            "default": "sum",
            "options": [
                {"value": "sum", "label": "Sum"},
                {"value": "mean", "label": "Mean"},
                {"value": "max", "label": "Maximum"},
                {"value": "min", "label": "Minimum"},
            ],
        },
    ]


def _temporal_schema() -> dict[str, object]:
    weightings = []
    controls: dict[str, list[dict[str, object]]] = {}
    for name in nb.list_temporal_weightings():
        metadata = nb.describe_temporal_weighting(name)
        default_parameters = metadata.get("default_parameters", {})
        required_parameters = metadata.get("required_parameters", ())
        weightings.append(
            {
                "name": name,
                "label": _temporal_weighting_label(name),
                "description": metadata.get("description", ""),
                "formula": metadata.get("formula", ""),
                "uses_age": bool(metadata.get("uses_age", False)),
                "age_basis": metadata.get("age_basis", "snapshot"),
                "default_parameters": (
                    dict(default_parameters)
                    if isinstance(default_parameters, Mapping)
                    else {}
                ),
                "required_parameters": (
                    list(required_parameters)
                    if isinstance(required_parameters, list | tuple)
                    else []
                ),
            }
        )
        controls[name] = _temporal_weighting_controls(name)
    return {
        "default_weighting": "baseline",
        "weightings": weightings,
        "controls": controls,
    }


def _temporal_weighting_controls(name: str) -> list[dict[str, object]]:
    if name == "asf":
        return [
            _number_control("p", "Decay scale (p)", 3.0, minimum=1e-12, step=0.1),
            _number_control("q", "Long-term floor (q)", 0.0, minimum=0.0, step=0.01),
            _number_control("a", "Midpoint (a)", 5.0, step=0.1),
        ]
    if name == "persistent_exponential":
        return [
            _required_number_control(
                "persistent_level",
                "Persistent level",
                minimum=0.0,
                maximum=1.0,
                step=0.01,
                description="Long-term relevance retained by old interactions.",
            ),
            _required_number_control(
                "decay_rate",
                "Decay rate",
                minimum=0.0,
                step=0.01,
                description="Proportional transient forgetting per time unit.",
            ),
        ]
    if name in {"persistent_weibull", "persistent_log_logistic"}:
        return [
            _required_number_control(
                "persistent_level",
                "Persistent level",
                minimum=0.0,
                maximum=1.0,
                step=0.01,
                description="Long-term relevance retained by old interactions.",
            ),
            _required_number_control(
                "scale",
                "Temporal scale",
                minimum=0.0,
                step=0.1,
                description="Elapsed-time scale at which transient memory changes.",
            ),
            _required_number_control(
                "shape",
                "Shape",
                minimum=0.0,
                step=0.1,
                description="Controls the shape of transient forgetting.",
            ),
        ]
    return []


def _filter_controls() -> dict[str, list[dict[str, object]]]:
    return {
        "default": [
            _checkbox_control("drop_isolates", "Drop isolated nodes", False),
        ],
        "threshold": [
            _range_control(
                "threshold_value",
                "Cutoff",
                0.0,
                minimum=0.0,
                maximum=1.0,
                step=0.01,
            ),
            _select_control(
                "operator",
                "Keep when value is",
                "greater_equal",
                (
                    ("greater_equal", "greater than or equal"),
                    ("greater", "greater than"),
                    ("less_equal", "less than or equal"),
                    ("less", "less than"),
                    ("equal", "equal"),
                    ("not_equal", "not equal"),
                ),
            ),
            _checkbox_control("drop_isolates", "Drop isolated nodes", False),
        ],
        "fraction": [
            _range_control(
                "fraction",
                "Retained fraction",
                0.1,
                minimum=0.0,
                maximum=1.0,
                step=0.01,
            ),
            _select_control(
                "tie_policy",
                "Tie policy",
                "include_all_ties",
                (
                    ("include_all_ties", "include all ties"),
                    ("exact_stable", "exact stable count"),
                    ("raise_on_tie", "raise on tie"),
                ),
                advanced=True,
            ),
            _checkbox_control("drop_isolates", "Drop isolated nodes", False),
        ],
        "significance": [
            _range_control("alpha", "Alpha", 0.05, minimum=0.0, maximum=1.0, step=0.01),
            _select_control(
                "correction",
                "Correction",
                "none",
                (
                    ("none", "none"),
                    ("bonferroni", "Bonferroni"),
                    ("fdr_bh", "FDR BH"),
                ),
                advanced=True,
            ),
            _checkbox_control("drop_isolates", "Drop isolated nodes", False),
        ],
    }


def _method_controls(
    name: str, metadata: Mapping[str, object]
) -> list[dict[str, object]]:
    controls: list[dict[str, object]] = []
    if name in P_VALUE_AGGREGATION_METHODS:
        pvalue_aggregation = _select_control(
            "pvalue_aggregation",
            "Endpoint p-value",
            "min",
            (
                ("min", "minimum"),
                ("max", "maximum"),
                ("average", "average"),
            ),
            advanced=True,
        )
        leaf_policy = _select_control(
            "leaf_policy",
            "Leaf policy",
            "zero",
            (
                ("zero", "zero"),
                ("ignore", "ignore leaf endpoint"),
            ),
            advanced=True,
        )
        controls.extend([pvalue_aggregation, leaf_policy])
    if name == "glanb":
        controls.append(
            _number_control(
                "c",
                "Degree influence",
                1.0,
                minimum=0.0,
                step=0.1,
                advanced=True,
            )
        )
    if name == "link_prediction":
        controls.extend(
            [
                _select_control(
                    "similarity",
                    "Similarity index",
                    "preferential_attachment",
                    (
                        ("preferential_attachment", "preferential attachment"),
                        ("shortest_path", "shortest path"),
                        ("local_path", "local path"),
                    ),
                ),
                _select_control(
                    "link_prediction_mode",
                    "Extraction target",
                    "high_similarity",
                    (
                        ("high_similarity", "high similarity"),
                        ("low_similarity", "low similarity"),
                    ),
                ),
            ]
        )
    if name == "link_prediction_iforest":
        controls.extend(
            [
                _checkbox_control(
                    "iforest_similarity_preferential_attachment",
                    "Preferential attachment",
                    True,
                ),
                _checkbox_control(
                    "iforest_similarity_shortest_path",
                    "Shortest path",
                    False,
                ),
                _checkbox_control(
                    "iforest_similarity_local_path",
                    "Local path",
                    False,
                ),
                _number_control(
                    "n_estimators",
                    "Isolation trees",
                    100,
                    minimum=1.0,
                    step=1.0,
                    advanced=True,
                ),
                _number_control(
                    "random_state",
                    "Random seed",
                    0,
                    minimum=0.0,
                    step=1.0,
                    advanced=True,
                ),
                _checkbox_control(
                    "bootstrap",
                    "Bootstrap samples",
                    False,
                    advanced=True,
                ),
            ]
        )
    if name in DISTANCE_TRANSFORM_METHODS:
        controls.append(
            _select_control(
                "distance_transform",
                "Weight means",
                "inverse",
                (
                    ("inverse", "larger weight is closer"),
                    ("identity", "weight is already distance"),
                ),
                advanced=True,
            )
        )
    if name in {"edge_betweenness", "node_betweenness"}:
        controls.append(
            _checkbox_control(
                "normalized",
                "Normalize betweenness",
                True,
                advanced=True,
            )
        )
    if name == "node_betweenness":
        controls.append(
            _checkbox_control("endpoints", "Count endpoints", False, advanced=True)
        )
    if name == "node_strength":
        direction = _select_control(
            "direction",
            "Strength direction",
            "total",
            (
                ("total", "total (in + out)"),
                ("in", "in-strength"),
                ("out", "out-strength"),
            ),
        )
        direction.update(
            {
                "ignored_when_undirected": True,
                "ignored_when_undirected_reason": (
                    "Undirected graphs have a single strength per node."
                ),
            }
        )
        controls.append(direction)
    if name in {"link_prediction", "link_prediction_iforest"}:
        controls.append(
            _number_control(
                "epsilon",
                "Local-path epsilon",
                1.0,
                minimum=0.0,
                step=0.01,
                advanced=True,
            )
        )
    if name == "doubly_stochastic":
        controls.append(
            _number_control(
                "epsilon",
                "Sinkhorn smoothing",
                1e-4,
                minimum=0.0,
                step=1e-5,
                advanced=True,
            )
        )

    if bool(metadata.get("requires_weights", False)):
        controls.insert(
            0,
            {
                "name": "weight_requirement",
                "label": "Requires a weight column",
                "control": "notice",
                "default": "",
            },
        )
    return [_guided_method_control(name, control) for control in controls]


def _guided_method_control(
    method_name: str,
    control: Mapping[str, object],
) -> dict[str, object]:
    enriched = dict(control)
    control_name = str(control.get("name", ""))
    guidance: dict[str, object] = {}
    for candidate in (
        METHOD_CONTROL_GUIDANCE.get(control_name),
        METHOD_PARAMETER_GUIDANCE.get((method_name, control_name)),
        IFOREST_FEATURE_GUIDANCE.get(control_name),
    ):
        if candidate is not None:
            guidance.update(candidate)
    if not guidance:
        return enriched

    for key in ("description", "illustration"):
        if key in guidance:
            enriched[key] = guidance[key]

    option_guidance = guidance.get("options")
    options = control.get("options")
    if isinstance(option_guidance, Mapping) and isinstance(options, list):
        enriched_options: list[dict[str, object]] = []
        for option in options:
            if not isinstance(option, Mapping):
                continue
            enriched_option = dict(option)
            details = option_guidance.get(option.get("value"))
            if isinstance(details, Mapping):
                enriched_option.update(details)
            enriched_options.append(enriched_option)
        enriched["options"] = enriched_options
    return enriched


def _pipeline_from_payload(payload: Mapping[object, object]) -> nb.Pipeline:
    if isinstance(payload.get("guided"), Mapping):
        (
            method_name,
            method_parameters,
            filter_name,
            filter_parameters,
        ) = _guided_config(payload)
    else:
        method_config = _named_config(payload, "method")
        filter_config = _named_config(payload, "filter")
        method_name = method_config["name"]
        method_parameters = method_config["parameters"]
        filter_name = filter_config["name"]
        filter_parameters = filter_config["parameters"]

    return (
        nb.pipeline()
        .score(method_name, **method_parameters)
        .filter(filter_name, **filter_parameters)
    )


def _guided_config(
    payload: Mapping[object, object],
) -> tuple[str, dict[str, object], str, dict[str, object]]:
    method_name, method_parameters = _guided_score_config(payload)
    metadata = nb.describe_method(method_name)
    filter_name, filter_parameters = _guided_filter_config(
        payload,
        method_name,
        metadata,
    )
    return method_name, method_parameters, filter_name, filter_parameters


def _guided_score_config(
    payload: Mapping[object, object],
) -> tuple[str, dict[str, object]]:
    guided = _required_mapping(payload.get("guided"), field="guided")
    method_name = _required_text(guided.get("method"), field="guided.method")
    metadata = nb.describe_method(method_name)
    controls = _optional_mapping(guided.get("controls"), field="guided.controls")

    method_parameters = _guided_method_parameters(
        method_name,
        metadata,
        controls,
        weight_column=_input_weight(payload),
    )
    return method_name, method_parameters


def _input_weight(payload: Mapping[object, object]) -> str | None:
    if _data_mode(payload) == "temporal":
        return "weight"
    return _optional_text(payload.get("weight"), field="weight")


def _guided_filter_config(
    payload: Mapping[object, object],
    method_name: str,
    metadata: Mapping[str, object],
) -> tuple[str, dict[str, object]]:
    guided = _required_mapping(payload.get("guided"), field="guided")
    requested_method = _required_text(guided.get("method"), field="guided.method")
    if requested_method != method_name:
        raise ValidationError(
            "Cached scores were computed with method "
            f"{method_name!r}, but guided.method is {requested_method!r}. "
            "Compute scores again before filtering."
        )
    controls = _optional_mapping(guided.get("controls"), field="guided.controls")
    requested_filter = _text_or_default(
        guided.get("filter"),
        default=_recommended_filter(method_name, metadata),
        field="guided.filter",
    )
    filter_name = (
        requested_filter
        if requested_filter != "recommended"
        else _recommended_filter(method_name, metadata)
    )
    if filter_name not in FILTER_NAMES:
        raise ValidationError(
            f"guided.filter must be one of {sorted(FILTER_NAMES)}, got {filter_name!r}."
        )

    filter_parameters = _guided_filter_parameters(
        method_name,
        metadata,
        controls,
        filter_name=filter_name,
    )
    return filter_name, filter_parameters


def _guided_method_parameters(
    method_name: str,
    metadata: Mapping[str, object],
    controls: Mapping[str, object],
    *,
    weight_column: str | None,
) -> dict[str, object]:
    parameters: dict[str, object] = {}
    requires_weights = bool(metadata.get("requires_weights", False))
    if method_name in WEIGHT_PARAMETER_METHODS:
        if requires_weights and weight_column is None:
            raise ValidationError(f"Method {method_name!r} requires a weight column.")
        parameters["weight"] = weight_column
    elif requires_weights and weight_column is None:
        raise ValidationError(f"Method {method_name!r} requires a weight column.")

    if method_name in P_VALUE_AGGREGATION_METHODS:
        parameters["pvalue_aggregation"] = _option(
            controls.get("pvalue_aggregation"),
            allowed={"min", "max", "average"},
            default="min",
            field="pvalue_aggregation",
        )
        parameters["leaf_policy"] = _option(
            controls.get("leaf_policy"),
            allowed={"zero", "ignore"},
            default="zero",
            field="leaf_policy",
        )
    if method_name == "glanb":
        parameters["c"] = _number(controls.get("c"), default=1.0, field="c")
    if method_name == "link_prediction":
        parameters["similarity"] = _option(
            controls.get("similarity"),
            allowed={
                "preferential_attachment",
                "shortest_path",
                "local_path",
            },
            default="preferential_attachment",
            field="similarity",
        )
        if (
            parameters["similarity"] == "local_path"
            and controls.get("epsilon") is not None
        ):
            parameters["epsilon"] = _number(
                controls.get("epsilon"),
                default=1.0,
                field="epsilon",
            )
    if method_name == "link_prediction_iforest":
        similarities = [
            similarity
            for similarity in (
                "preferential_attachment",
                "shortest_path",
                "local_path",
            )
            if _boolean(
                controls.get(f"iforest_similarity_{similarity}"),
                default=similarity == "preferential_attachment",
                field=f"iforest_similarity_{similarity}",
            )
        ]
        if not similarities:
            raise ValidationError(
                "Select at least one similarity for link_prediction_iforest."
            )
        parameters["similarities"] = similarities
        parameters["n_estimators"] = _integer_number(
            controls.get("n_estimators"),
            default=100,
            field="n_estimators",
        )
        parameters["random_state"] = _integer_number(
            controls.get("random_state"),
            default=0,
            field="random_state",
        )
        parameters["bootstrap"] = _boolean(
            controls.get("bootstrap"),
            default=False,
            field="bootstrap",
        )
        if "local_path" in similarities and controls.get("epsilon") is not None:
            parameters["epsilon"] = _number(
                controls.get("epsilon"),
                default=1.0,
                field="epsilon",
            )
    if method_name in DISTANCE_TRANSFORM_METHODS and weight_column is not None:
        parameters["distance_transform"] = _option(
            controls.get("distance_transform"),
            allowed={"inverse", "identity"},
            default="inverse",
            field="distance_transform",
        )
    if method_name in {"edge_betweenness", "node_betweenness"}:
        parameters["normalized"] = _boolean(
            controls.get("normalized"),
            default=True,
            field="normalized",
        )
    if method_name == "node_strength":
        parameters["direction"] = _option(
            controls.get("direction"),
            allowed={"total", "in", "out"},
            default="total",
            field="direction",
        )
    if method_name == "node_betweenness":
        parameters["endpoints"] = _boolean(
            controls.get("endpoints"),
            default=False,
            field="endpoints",
        )
    if method_name == "doubly_stochastic" and controls.get("epsilon") is not None:
        parameters["epsilon"] = _number(
            controls.get("epsilon"),
            default=1e-4,
            field="epsilon",
        )
    return parameters


def _guided_filter_parameters(
    method_name: str,
    metadata: Mapping[str, object],
    controls: Mapping[str, object],
    *,
    filter_name: str,
) -> dict[str, object]:
    parameters: dict[str, object] = {}
    target = _metadata_text(metadata, "target", default="edge")
    if target == "edge":
        parameters["drop_isolates"] = _boolean(
            controls.get("drop_isolates"),
            default=False,
            field="drop_isolates",
        )

    if filter_name == "default":
        if method_name == "link_prediction":
            parameters["direction"] = _link_prediction_direction(controls)
        return parameters

    if filter_name == "threshold":
        parameters["value"] = _number(
            controls.get("threshold_value", controls.get("value")),
            default=_default_threshold_value(metadata),
            field="threshold_value",
        )
        if method_name == "link_prediction":
            direction = _link_prediction_direction(controls)
            allowed_operators = (
                {"greater", "greater_equal"}
                if direction == "higher"
                else {"less", "less_equal"}
            )
            default_operator = (
                "greater_equal" if direction == "higher" else "less_equal"
            )
        else:
            allowed_operators = {
                "greater",
                "greater_equal",
                "less",
                "less_equal",
                "equal",
                "not_equal",
            }
            default_operator = _default_threshold_operator(metadata)
        parameters["operator"] = _option(
            controls.get("operator"),
            allowed=allowed_operators,
            default=default_operator,
            field="operator",
        )
        return parameters

    if filter_name == "fraction":
        parameters["fraction"] = _number(
            controls.get("fraction"),
            default=0.1,
            field="fraction",
        )
        parameters["tie_policy"] = _option(
            controls.get("tie_policy"),
            allowed={"include_all_ties", "exact_stable", "raise_on_tie"},
            default="include_all_ties",
            field="tie_policy",
        )
        if method_name == "link_prediction":
            parameters["direction"] = _link_prediction_direction(controls)
        return parameters

    if filter_name == "significance":
        parameters["alpha"] = _number(
            controls.get("alpha"),
            default=0.05,
            field="alpha",
        )
        parameters["correction"] = _option(
            controls.get("correction"),
            allowed={"none", "bonferroni", "fdr_bh"},
            default="none",
            field="correction",
        )
        return parameters

    raise ValidationError(f"Unsupported guided filter {filter_name!r}.")


def _network_from_payload(payload: Mapping[object, object]) -> nb.Network:
    data_mode = _data_mode(payload)
    if data_mode == "temporal":
        return _temporal_data_from_payload(payload)["network"]
    if data_mode == "graphml":
        return _graphml_data_from_payload(payload)["network"]
    parsed = _csv_graph_from_payload(payload)
    return parsed["network"]


def _graphml_data_from_payload(payload: Mapping[object, object]) -> dict[str, Any]:
    graphml_text = _required_text(payload.get("graphml_text"), field="graphml_text")
    weight = _optional_text(payload.get("weight"), field="weight")
    context = _text_or_default(
        payload.get("context"), default="webapp GraphML upload", field="context"
    )

    with TemporaryDirectory(prefix="netbone-web-") as directory:
        graphml_path = Path(directory) / "network.graphml"
        graphml_path.write_text(graphml_text, encoding="utf-8")
        network = nb.from_graphml(graphml_path, context=context)

    source_directed = network.directed
    network, direction_handling = _apply_direction_handling(network, payload)
    graph = network.to_original_graph()
    if graph.number_of_edges() == 0:
        raise ValidationError("GraphML input must contain at least one edge.")

    edge_attributes = sorted(
        {
            str(name)
            for _, _, attributes in graph.edges(data=True)
            for name in attributes
        }
    )
    numeric_edge_attributes = [
        name
        for name in edge_attributes
        if all(
            name in attributes and _is_finite_number(attributes[name])
            for _, _, attributes in graph.edges(data=True)
        )
    ]
    if weight is not None and weight not in edge_attributes:
        raise ValidationError(
            f"GraphML edge weight attribute {weight!r} does not exist."
        )
    if weight is not None and weight not in numeric_edge_attributes:
        raise ValidationError(
            f"GraphML edge weight attribute {weight!r} must contain a finite "
            "numeric value on every edge."
        )

    node_attributes = sorted(
        {str(name) for _, attributes in graph.nodes(data=True) for name in attributes}
    )
    records: list[dict[str, JsonValue]] = []
    for source, target, attributes in graph.edges(data=True):
        if len(records) >= MAX_PREVIEW_ROWS:
            break
        record: dict[str, JsonValue] = {
            "source": json_value(source),
            "target": json_value(target),
        }
        for name in edge_attributes:
            preview_name = f"edge.{name}" if name in record else name
            record[preview_name] = json_value(attributes.get(name))
        records.append(record)

    suggested_weight = _guess_column(
        numeric_edge_attributes,
        WEIGHT_COLUMN_CANDIDATES,
        None,
    )
    return {
        "network": network,
        "graph": graph,
        "source_directed": source_directed,
        "direction_handling": direction_handling,
        "context": context,
        "source": None,
        "target": None,
        "weight": weight,
        "headers": ["source", "target", *edge_attributes],
        "row_count": graph.number_of_edges(),
        "records": records,
        "suggested_source": None,
        "suggested_target": None,
        "suggested_weight": suggested_weight,
        "likely_weight_columns": _likely_columns(
            numeric_edge_attributes,
            WEIGHT_COLUMN_CANDIDATES,
        ),
        "edge_attributes": edge_attributes,
        "numeric_edge_attributes": numeric_edge_attributes,
        "node_attributes": node_attributes,
        "warnings": _network_warnings(network.metadata),
    }


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _temporal_data_from_payload(payload: Mapping[object, object]) -> dict[str, Any]:
    csv_text = _required_text(payload.get("csv_text"), field="csv_text")
    source = _required_text(payload.get("source"), field="source")
    target = _required_text(payload.get("target"), field="target")
    time = _required_text(payload.get("time"), field="time")
    event_weight = _optional_text(payload.get("event_weight"), field="event_weight")
    delimiter = _delimiter(
        _text_or_default(payload.get("delimiter"), default=",", field="delimiter")
    )
    context = _text_or_default(
        payload.get("context"), default="webapp temporal upload", field="context"
    )
    directed = _boolean(payload.get("directed"), default=False, field="directed")
    preview = _csv_records_preview(
        csv_text,
        delimiter=delimiter,
        required_columns=(source, target, time, event_weight),
    )
    config = _temporal_config_from_payload(payload)

    with TemporaryDirectory(prefix="netbone-web-") as directory:
        event_path = Path(directory) / "events.csv"
        event_path.write_text(csv_text, encoding="utf-8")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            temporal_network = nb.from_temporal_edgelist(
                event_path,
                source=source,
                target=target,
                time=time,
                event_weight=event_weight,
                delimiter=delimiter,
                context=context,
                directed=directed,
            )
            network = nb.aggregate_temporal(temporal_network, config=config)

    source_directed = temporal_network.directed
    network, direction_handling = _apply_direction_handling(network, payload)
    temporal_aggregation = _temporal_aggregation_metadata(network.metadata)
    return {
        **preview,
        "network": network,
        "graph": network.graph,
        "source": source,
        "target": target,
        "time": time,
        "event_weight": event_weight,
        "weight": "weight",
        "source_directed": source_directed,
        "direction_handling": direction_handling,
        "event_count": temporal_network.event_count,
        "suggested_source": _guess_column(
            preview["headers"], SOURCE_COLUMN_CANDIDATES, 0
        ),
        "suggested_target": _guess_column(
            preview["headers"], TARGET_COLUMN_CANDIDATES, 1
        ),
        "suggested_time": _guess_column(preview["headers"], TIME_COLUMN_CANDIDATES, 2),
        "suggested_event_weight": _guess_column(
            preview["headers"], EVENT_WEIGHT_COLUMN_CANDIDATES, None
        ),
        "suggested_weight": "weight",
        "likely_weight_columns": _likely_columns(
            preview["headers"], EVENT_WEIGHT_COLUMN_CANDIDATES
        ),
        "warnings": _network_warnings(network.metadata),
        "temporal_aggregation": temporal_aggregation,
    }


def _csv_records_preview(
    csv_text: str,
    *,
    delimiter: str,
    required_columns: tuple[str | None, ...],
) -> dict[str, Any]:
    reader = csv.DictReader(StringIO(csv_text), delimiter=delimiter)
    if reader.fieldnames is None:
        raise ValidationError("CSV input must include a header row.")
    headers = [field.strip() for field in reader.fieldnames if field is not None]
    # Look rows up by the stripped names so "source, target, weight" works.
    reader.fieldnames = headers
    missing_columns = [
        column
        for column in required_columns
        if column is not None and column not in headers
    ]
    if missing_columns:
        raise ValidationError(
            "CSV input is missing required columns: " + ", ".join(missing_columns)
        )
    records: list[dict[str, JsonValue]] = []
    row_count = 0
    for row in reader:
        row_count += 1
        if len(records) < MAX_PREVIEW_ROWS:
            records.append(
                {header: json_value(row.get(header, "")) for header in headers}
            )
    if row_count == 0:
        raise ValidationError("CSV input must contain at least one data row.")
    return {
        "headers": headers,
        "row_count": row_count,
        "records": records,
    }


def _temporal_config_from_payload(
    payload: Mapping[object, object],
) -> nb.TemporalAggregationConfig:
    temporal = _optional_mapping(payload.get("temporal"), field="temporal")
    weighting = _text_or_default(
        temporal.get("weighting"),
        default="baseline",
        field="temporal.weighting",
    )
    parameters = _optional_mapping(
        temporal.get("parameters"),
        field="temporal.parameters",
    )
    zero_weight_policy = _option(
        temporal.get("zero_weight_policy"),
        allowed={"drop", "keep"},
        default="drop",
        field="temporal.zero_weight_policy",
    )
    return nb.TemporalAggregationConfig(
        weighting=weighting,
        parameters=parameters,
        evaluation_time=_optional_temporal_value(
            temporal.get("evaluation_time"), field="temporal.evaluation_time"
        ),
        time_unit=_optional_temporal_value(
            temporal.get("time_unit"), field="temporal.time_unit"
        ),
        snapshot_size=_optional_temporal_value(
            temporal.get("snapshot_size"), field="temporal.snapshot_size"
        ),
        snapshot_origin=_optional_temporal_value(
            temporal.get("snapshot_origin"), field="temporal.snapshot_origin"
        ),
        zero_weight_policy=zero_weight_policy,
    )


def _csv_graph_from_payload(payload: Mapping[object, object]) -> dict[str, Any]:
    csv_text = _required_text(payload.get("csv_text"), field="csv_text")
    source = _required_text(payload.get("source"), field="source")
    target = _required_text(payload.get("target"), field="target")
    weight = _optional_text(payload.get("weight"), field="weight")
    delimiter = _delimiter(
        _text_or_default(payload.get("delimiter"), default=",", field="delimiter")
    )
    context = _text_or_default(
        payload.get("context"), default="webapp upload", field="context"
    )
    directed = _boolean(payload.get("directed"), default=False, field="directed")

    graph = nx.DiGraph() if directed else nx.Graph()
    seen_edges: set[tuple[str, str]] = set()
    reader = csv.DictReader(StringIO(csv_text), delimiter=delimiter)
    if reader.fieldnames is None:
        raise ValidationError("CSV input must include a header row.")
    headers = [field.strip() for field in reader.fieldnames if field is not None]
    # Look rows up by the stripped names so "source, target, weight" works.
    reader.fieldnames = headers
    missing_columns = [
        column
        for column in (source, target, weight)
        if column is not None and column not in headers
    ]
    if missing_columns:
        raise ValidationError(
            "CSV input is missing required columns: " + ", ".join(missing_columns)
        )

    records: list[dict[str, JsonValue]] = []
    row_count = 0
    for row_number, row in enumerate(reader, start=2):
        row_count += 1
        source_value = (row.get(source) or "").strip()
        target_value = (row.get(target) or "").strip()
        if not source_value or not target_value:
            raise ValidationError(
                f"CSV row {row_number} must include non-empty source and target values."
            )
        edge_key = (
            (source_value, target_value)
            if directed
            else (
                (source_value, target_value)
                if source_value <= target_value
                else (target_value, source_value)
            )
        )
        if edge_key in seen_edges:
            edge_label = "arc" if directed else "edge"
            raise ValidationError(
                f"CSV row {row_number} duplicates simple-graph {edge_label} "
                f"({source_value!r}, {target_value!r})."
            )
        seen_edges.add(edge_key)
        if source_value == target_value:
            raise ValidationError(
                f"CSV row {row_number} is a self-loop on {source_value!r}. "
                "Self-loops are not supported; remove the row or load the file as "
                "a temporal event list, which drops them."
            )
        attributes: dict[str, object] = {}
        if weight is not None:
            raw_weight = (row.get(weight) or "").strip()
            if raw_weight == "":
                raise ValidationError(
                    f"CSV row {row_number} has an empty weight value."
                )
            try:
                numeric_weight = float(raw_weight)
            except ValueError as exc:
                raise ValidationError(
                    f"CSV row {row_number} weight {raw_weight!r} is not numeric."
                ) from exc
            if not math.isfinite(numeric_weight):
                raise ValidationError(
                    f"CSV row {row_number} weight {raw_weight!r} must be a finite "
                    "number."
                )
            attributes[weight] = numeric_weight
        graph.add_edge(source_value, target_value, **attributes)
        if len(records) < MAX_PREVIEW_ROWS:
            records.append(
                {header: json_value(row.get(header, "")) for header in headers}
            )

    if graph.number_of_edges() == 0:
        raise ValidationError("CSV input must contain at least one edge.")
    network = nb.from_graph(graph, context=context)
    network, direction_handling = _apply_direction_handling(network, payload)
    graph = network.to_original_graph()
    return {
        "network": network,
        "graph": graph,
        "context": context,
        "source": source,
        "target": target,
        "weight": weight,
        "directed": graph.is_directed(),
        "source_directed": directed,
        "direction_handling": direction_handling,
        "headers": headers,
        "row_count": row_count,
        "records": records,
        "suggested_source": _guess_column(headers, SOURCE_COLUMN_CANDIDATES, 0),
        "suggested_target": _guess_column(headers, TARGET_COLUMN_CANDIDATES, 1),
        "suggested_weight": _guess_column(headers, WEIGHT_COLUMN_CANDIDATES, None),
        "likely_weight_columns": _likely_columns(headers, WEIGHT_COLUMN_CANDIDATES),
        "warnings": _network_warnings(network.metadata),
    }


def _apply_direction_handling(
    network: nb.Network,
    payload: Mapping[object, object],
) -> tuple[nb.Network, dict[str, object]]:
    mode = _option(
        payload.get("direction_mode"),
        allowed={"preserve", "undirected"},
        default="preserve",
        field="direction_mode",
    )
    source_directed = network.directed
    if mode == "preserve":
        return network, {
            "mode": mode,
            "source_directed": source_directed,
            "output_directed": source_directed,
        }
    if not source_directed:
        raise ValidationError(
            "direction_mode='undirected' requires a directed CSV or GraphML input."
        )

    weight = (
        "weight"
        if _data_mode(payload) == "temporal"
        else _optional_text(payload.get("weight"), field="weight")
    )
    reciprocal_merge = (
        cast(
            Literal["sum", "mean", "max", "min"],
            _option(
                _required_text(
                    payload.get("reciprocal_merge"),
                    field="reciprocal_merge",
                ),
                allowed={"sum", "mean", "max", "min"},
                default="sum",
                field="reciprocal_merge",
            ),
        )
        if weight is not None
        else None
    )
    projected = nb.to_undirected(
        network,
        weight=weight,
        reciprocal_merge=reciprocal_merge,
    )
    conversion = projected.metadata.get("direction_conversion", {})
    details = dict(conversion) if isinstance(conversion, Mapping) else {}
    return projected, {
        **details,
        "mode": mode,
        "source_directed": True,
        "output_directed": False,
    }


def _named_config(
    payload: Mapping[object, object],
    key: str,
) -> dict[str, Any]:
    raw = payload.get(key)
    if not isinstance(raw, Mapping):
        raise ValidationError(f"{key!r} must be a JSON object.")
    name = _required_text(raw.get("name"), field=f"{key}.name")
    parameters_raw = raw.get("parameters", {})
    if not isinstance(parameters_raw, Mapping):
        raise ValidationError(f"{key}.parameters must be a JSON object.")
    return {
        "name": name,
        "parameters": dict(parameters_raw),
    }


def _statistics_payload(
    scores: nb.MethodResult,
    selection: nb.Selection | None = None,
    *,
    graph: nx.Graph | None = None,
    weight: str | None = None,
) -> list[JsonValue]:
    id_column = "edge_id" if scores.target == "edge" else "node_id"
    selected_ids = set(selection.selected_ids) if selection is not None else set()
    records: list[JsonValue] = []
    for row in scores.statistics.to_dict(orient="records"):
        record = dict(row)
        if graph is not None and weight is not None and scores.target == "edge":
            attributes = graph.get_edge_data(record["source"], record["target"])
            if attributes is not None and weight in attributes:
                record["weight"] = attributes[weight]
        if selection is not None:
            record["retained"] = int(record[id_column]) in selected_ids
        records.append(json_mapping(record))
    return records[:MAX_STATISTICS_ROWS]


def _score_ranges(scores: nb.MethodResult) -> dict[str, JsonValue]:
    ranges: dict[str, JsonValue] = {}
    identity_columns = {
        "edge_id",
        "source_id",
        "target_id",
        "node_id",
        "source",
        "target",
        "node",
    }
    for column in scores.statistics.columns:
        if column in identity_columns:
            continue
        values = [
            number
            for value in scores.statistics[column].tolist()
            if (number := _finite_number(value)) is not None
        ]
        if not values:
            continue
        ranges[str(column)] = json_mapping(
            {
                "min": min(values),
                "max": max(values),
                "count": len(values),
            }
        )
    return ranges


def _finite_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, int | float | str):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _graph_payload(
    graph: nx.Graph,
    backbone: nx.Graph,
    *,
    node_limit: int | None = None,
) -> dict[str, JsonValue]:
    if node_limit is None:
        node_ids = sorted(graph, key=str)
        sampled_graph = graph
    else:
        node_ids = nsmallest(node_limit, graph, key=str)
        sampled_graph = graph.subgraph(node_ids)

    components = (
        nx.weakly_connected_components(backbone)
        if backbone.is_directed()
        else nx.connected_components(backbone)
    )
    component_by_node = {
        node: index
        for index, members in enumerate(components, start=1)
        for node in members
    }
    nodes: list[JsonValue] = [
        {
            "id": str(node),
            "retained": node in component_by_node,
            "component": component_by_node.get(node),
            "isolated": node in component_by_node and backbone.degree[node] == 0,
        }
        for node in node_ids
    ]
    edges: list[JsonValue] = []
    for source, target, data in sorted(
        sampled_graph.edges(data=True), key=_edge_sort_key
    ):
        if len(edges) >= MAX_GRAPH_EDGES:
            break
        edge: dict[str, JsonValue] = {
            "source": str(source),
            "target": str(target),
            "retained": backbone.has_edge(source, target),
        }
        weight = data.get("weight")
        if isinstance(weight, int | float) and math.isfinite(float(weight)):
            edge["weight"] = float(weight)
        edges.append(edge)
    return {
        "nodes": nodes,
        "edges": edges,
        "directed": graph.is_directed(),
        "truncated": (
            len(nodes) < graph.number_of_nodes() or len(edges) < graph.number_of_edges()
        ),
    }


def _optional_guided_method_name(payload: Mapping[object, object]) -> str | None:
    guided = payload.get("guided")
    if not isinstance(guided, Mapping):
        return None
    method_name = guided.get("method")
    return method_name if isinstance(method_name, str) and method_name else None


def _readiness_messages(
    method_name: str | None,
    method_metadata: Mapping[str, object] | None,
    *,
    selected_weight: str | None,
    likely_weight_columns: list[str],
    directed: bool,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    if (
        directed
        and method_metadata is not None
        and not bool(method_metadata.get("supports_directed", False))
    ):
        method_label = _friendly_label(method_name or "method")
        errors.append(
            f"{method_label} does not support directed graphs. Choose a method "
            "marked as directed-compatible, or use an explicitly aggregated "
            "undirected graph."
        )
    if selected_weight is not None:
        return warnings, errors

    likely_text = ", ".join(likely_weight_columns)
    if method_metadata is not None and bool(method_metadata.get("requires_weights")):
        method_label = _friendly_label(method_name or "method")
        errors.append(f"{method_label} requires a weight column.")
        return warnings, errors

    if likely_weight_columns and _method_can_use_weight(method_name, method_metadata):
        warnings.append(
            "No weight column is selected, but likely weight column(s) were "
            f"detected: {likely_text}. This run will treat the graph as unweighted."
        )
    return warnings, errors


def _method_can_use_weight(
    method_name: str | None,
    method_metadata: Mapping[str, object] | None,
) -> bool:
    if method_name is None:
        return True
    if method_name in WEIGHT_PARAMETER_METHODS:
        return True
    return bool(
        method_metadata is not None and method_metadata.get("supports_weighted")
    )


def _guess_column(
    headers: list[str],
    candidates: tuple[str, ...],
    fallback_index: int | None,
) -> str | None:
    lowered = {header.lower(): header for header in headers}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    if fallback_index is None:
        return None
    return headers[fallback_index] if fallback_index < len(headers) else None


def _likely_columns(headers: list[str], candidates: tuple[str, ...]) -> list[str]:
    candidate_set = set(candidates)
    return [header for header in headers if header.lower() in candidate_set]


def _required_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field} must be a JSON object.")
    return {str(key): item for key, item in value.items()}


def _optional_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if value is None:
        return {}
    return _required_mapping(value, field=field)


def _data_mode(payload: Mapping[object, object]) -> str:
    return _option(
        payload.get("data_mode"),
        allowed={"graphml", "static", "temporal"},
        default="static",
        field="data_mode",
    )


def _optional_temporal_value(value: object, *, field: str) -> object | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValidationError(
            f"{field} must be numeric, datetime-like, duration-like, or empty."
        )
    if isinstance(value, int | float):
        if not math.isfinite(float(value)):
            raise ValidationError(f"{field} must be finite.")
        return value
    if not isinstance(value, str):
        raise ValidationError(
            f"{field} must be numeric, datetime-like, duration-like, or empty."
        )
    text = value.strip()
    if not text:
        return None
    try:
        numeric = float(text)
    except ValueError:
        return text
    if not math.isfinite(numeric):
        raise ValidationError(f"{field} must be finite.")
    return int(numeric) if numeric.is_integer() else numeric


def _required_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string.")
    return value.strip()


def _text_or_default(value: object, *, default: str, field: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string.")
    text = value.strip()
    return text if text else default


def _optional_text(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string.")
    text = value.strip()
    return text if text else None


def _delimiter(value: str) -> str:
    if value == r"\t":
        return "\t"
    if value not in {",", ";", "\t"}:
        raise ValidationError("delimiter must be ',', ';', or tab.")
    return value


def _number(value: object, *, default: float, field: str) -> float:
    if value is None or value == "":
        number = default
    elif isinstance(value, bool):
        raise ValidationError(f"{field} must be numeric.")
    elif isinstance(value, str | int | float):
        try:
            number = float(value)
        except ValueError as exc:
            raise ValidationError(f"{field} must be numeric.") from exc
    else:
        raise ValidationError(f"{field} must be numeric.")
    if not math.isfinite(number):
        raise ValidationError(f"{field} must be finite.")
    return number


def _integer_number(value: object, *, default: int, field: str) -> int:
    number = _number(value, default=float(default), field=field)
    if not number.is_integer():
        raise ValidationError(f"{field} must be an integer.")
    return int(number)


def _boolean(value: object, *, default: bool, field: str) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    raise ValidationError(f"{field} must be true or false.")


def _option(
    value: object,
    *,
    allowed: set[str],
    default: str,
    field: str,
) -> str:
    text = _text_or_default(value, default=default, field=field)
    if text not in allowed:
        raise ValidationError(
            f"{field} must be one of {sorted(allowed)}, got {text!r}."
        )
    return text


def _metadata_text(
    metadata: Mapping[str, object],
    key: str,
    *,
    default: str,
) -> str:
    value = metadata.get(key)
    return value if isinstance(value, str) and value else default


def _primary_statistic(metadata: Mapping[str, object]) -> str:
    value = metadata.get("primary_statistic")
    return value if isinstance(value, str) and value else "value"


def _recommended_filter(name: str, metadata: Mapping[str, object]) -> str:
    output_type = _metadata_text(metadata, "output_type", default="custom")
    if output_type == "pvalue":
        return "significance"
    if name in {"edge_weight", "noise_corrected"}:
        return "threshold"
    if name in STRUCTURAL_DEFAULT_METHODS:
        return "default"
    return "fraction"


def _default_threshold_value(metadata: Mapping[str, object]) -> float:
    defaults = metadata.get("default_filter_parameters")
    if metadata.get("default_filter") == "threshold" and isinstance(defaults, Mapping):
        value = defaults.get("value")
        if isinstance(value, int | float):
            return float(value)
    return (
        0.05
        if _metadata_text(metadata, "output_type", default="custom") == "pvalue"
        else 0.0
    )


def _default_threshold_operator(metadata: Mapping[str, object]) -> str:
    defaults = metadata.get("default_filter_parameters")
    if metadata.get("default_filter") == "threshold" and isinstance(defaults, Mapping):
        operator = defaults.get("operator")
        if isinstance(operator, str):
            return operator
    direction = _metadata_text(metadata, "preferred_direction", default="higher")
    return "less" if direction == "lower" else "greater_equal"


def _filter_reason(filter_name: str, output_type: str, method_name: str) -> str:
    if filter_name == "significance":
        return "p-value methods are easiest to read through alpha."
    if filter_name == "default":
        return "this method has a structural default extraction rule."
    if method_name == "edge_weight":
        return "a direct weight cutoff is the clearest baseline."
    if method_name == "noise_corrected":
        return (
            "retain edges exceeding their expected strength by the chosen number "
            "of standard deviations."
        )
    if method_name == "link_prediction":
        return "choose the retained fraction of high- or low-similarity links."
    if output_type == "score":
        return "ranking methods use retained fraction by default."
    return "retained fraction is the safest generic extraction control."


def _friendly_label(name: str) -> str:
    overrides = {
        "glanb": "GLANB",
        "gspar": "GSPAR",
        "h_backbone": "h-Backbone",
        "lans": "LANS",
        "link_prediction_iforest": "Link Prediction Isolation Forest",
    }
    return overrides.get(name, name.replace("_", " ").title())


def _temporal_weighting_label(name: str) -> str:
    return "ASF" if name == "asf" else _friendly_label(name)


def _network_warnings(metadata: Mapping[str, object]) -> tuple[str, ...]:
    values = metadata.get("netbone_warnings", ())
    if not isinstance(values, list | tuple):
        return ()
    return tuple(str(value) for value in values)


def _temporal_aggregation_metadata(
    metadata: Mapping[str, object],
) -> dict[str, object] | None:
    value = metadata.get("temporal_aggregation")
    if not isinstance(value, Mapping):
        return None
    return {str(key): item for key, item in value.items()}


def _direction_conversion_metadata(
    metadata: Mapping[str, object],
) -> dict[str, object] | None:
    value = metadata.get("direction_conversion")
    if not isinstance(value, Mapping):
        return None
    return {str(key): item for key, item in value.items()}


def _resolved_web_config(
    pipeline_config: Mapping[str, object],
    temporal_aggregation: Mapping[str, object] | None,
    direction_conversion: Mapping[str, object] | None,
) -> dict[str, object]:
    if temporal_aggregation is None and direction_conversion is None:
        return dict(pipeline_config)
    resolved: dict[str, object] = {"pipeline": dict(pipeline_config)}
    if temporal_aggregation is not None:
        temporal_config = temporal_aggregation.get("config")
        resolved["temporal_aggregation"] = (
            dict(temporal_config)
            if isinstance(temporal_config, Mapping)
            else dict(temporal_aggregation)
        )
    if direction_conversion is not None:
        resolved["direction_conversion"] = {
            "mode": "undirected",
            "weight_attribute": direction_conversion.get("weight_attribute"),
            "reciprocal_merge": direction_conversion.get("reciprocal_merge"),
        }
    return resolved


def _link_prediction_direction(controls: Mapping[str, object]) -> str:
    mode = _option(
        controls.get("link_prediction_mode"),
        allowed={"high_similarity", "low_similarity"},
        default="high_similarity",
        field="link_prediction_mode",
    )
    return "higher" if mode == "high_similarity" else "lower"


def _select_control(
    name: str,
    label: str,
    default: str,
    options: tuple[tuple[str, str], ...],
    *,
    advanced: bool = False,
) -> dict[str, object]:
    return {
        "name": name,
        "label": label,
        "control": "select",
        "default": default,
        "options": [
            {"value": value, "label": option_label} for value, option_label in options
        ],
        "advanced": advanced,
    }


def _checkbox_control(
    name: str,
    label: str,
    default: bool,
    *,
    advanced: bool = False,
) -> dict[str, object]:
    return {
        "name": name,
        "label": label,
        "control": "checkbox",
        "default": default,
        "advanced": advanced,
    }


def _number_control(
    name: str,
    label: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    step: float | str = 1,
    advanced: bool = False,
) -> dict[str, object]:
    control: dict[str, object] = {
        "name": name,
        "label": label,
        "control": "number",
        "default": default,
        "step": step,
        "advanced": advanced,
    }
    if minimum is not None:
        control["min"] = minimum
    if maximum is not None:
        control["max"] = maximum
    return control


def _required_number_control(
    name: str,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    step: float,
    description: str,
) -> dict[str, object]:
    control: dict[str, object] = {
        "name": name,
        "label": f"{label} (required)",
        "control": "number",
        "default": None,
        "step": step,
        "advanced": False,
        "required": True,
        "description": description,
    }
    if minimum is not None:
        control["min"] = minimum
    if maximum is not None:
        control["max"] = maximum
    return control


def _range_control(
    name: str,
    label: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
    step: float,
) -> dict[str, object]:
    return {
        "name": name,
        "label": label,
        "control": "range",
        "default": default,
        "min": minimum,
        "max": maximum,
        "step": step,
    }


def _edge_sort_key(
    edge: tuple[object, object, Mapping[str, object]],
) -> tuple[str, str]:
    source, target, _data = edge
    source_text = str(source)
    target_text = str(target)
    return source_text, target_text
