"""Isolation-Forest scoring of link-prediction similarities."""

from __future__ import annotations

import math
from collections.abc import Sequence
from importlib import import_module
from numbers import Real
from typing import Any

import pandas as pd

from netbone.exceptions import ConfigurationError, ValidationError
from netbone.methods.link_prediction import (
    DIRECTED_SEMANTICS_WARNING,
    DISTANCE_TRANSFORMS,
    LINK_PREDICTION_METADATA,
    SIMILARITIES,
    compute_link_prediction,
)
from netbone.network import Network
from netbone.results import MethodResult

LINK_PREDICTION_IFOREST_METADATA: dict[str, object] = {
    "name": "link_prediction_iforest",
    "display_name": "Link Prediction Isolation Forest",
    "target": "edge",
    "output_type": "score",
    "primary_statistic": "link_prediction_iforest_score",
    "preferred_direction": "higher",
    "supports_directed": True,
    "supports_weighted": True,
    "requires_weights": False,
    "requires_positive_weights": True,
    "uses_weights": True,
    "supports_multigraph": False,
    "supports_self_loops": False,
    "default_filter": "fraction",
    "default_filter_parameters": {
        "fraction": 0.1,
    },
    "similarity_options": tuple(sorted(SIMILARITIES)),
    "default_weight": None,
    "default_weight_alpha": 1.0,
    "default_distance_transform": "inverse",
    "distance_transform_options": tuple(sorted(DISTANCE_TRANSFORMS)),
    "default_epsilon": 1.0,
    "default_n_estimators": 100,
    "default_max_samples": "auto",
    "default_max_features": 1.0,
    "default_bootstrap": False,
    "default_random_state": 0,
    "optional_dependency": "scikit-learn",
    "selection_uses_contamination": False,
    "directed_semantics": LINK_PREDICTION_METADATA["directed_semantics"],
    "reference": "Integrating Link Prediction and Isolation Forest for Backbone "
    "Extraction, WAW 2025, LNCS 15699 (2025).",
    "doi": "10.1007/978-3-031-92898-7_13",
    "isolation_forest_reference": "Isolation Forest, IEEE International Conference "
    "on Data Mining (2008).",
    "isolation_forest_doi": "10.1109/ICDM.2008.17",
}


def compute_link_prediction_iforest(
    network: Network,
    *,
    similarities: str | Sequence[str],
    epsilon: float = 1.0,
    weight: str | None = None,
    weight_alpha: float = 1.0,
    distance_transform: str = "inverse",
    n_estimators: int = 100,
    max_samples: str | int | float = "auto",
    max_features: int | float = 1.0,
    bootstrap: bool = False,
    random_state: int = 0,
) -> MethodResult:
    """Score edges by Isolation-Forest anomaly across similarity features.

    The selected link-prediction similarities are computed for every observed
    edge. Isolation Forest is then fitted to the resulting feature vectors.
    Returned scores are the negated scikit-learn ``score_samples`` values, so
    larger values indicate more anomalous edges.
    """

    similarity_names = _normalize_similarities(similarities)
    estimator_count = _positive_integer(n_estimators, field="n_estimators")
    sample_count = _max_samples(max_samples)
    feature_count = _max_features(max_features, len(similarity_names))
    if not isinstance(bootstrap, bool):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'bootstrap' must be a boolean."
        )
    seed = _integer(random_state, field="random_state")

    identity_columns = ["edge_id", "source_id", "target_id", "source", "target"]
    statistics: pd.DataFrame | None = None
    feature_columns: list[str] = []
    for similarity in similarity_names:
        result = compute_link_prediction(
            network,
            similarity=similarity,
            epsilon=epsilon,
            weight=weight,
            weight_alpha=weight_alpha,
            distance_transform=distance_transform,
        )
        if statistics is None:
            statistics = result.statistics[identity_columns].copy()
        elif result.statistics["edge_id"].tolist() != statistics["edge_id"].tolist():
            raise ValidationError(
                "Link-prediction feature results do not align by edge_id."
            )

        feature_column = f"link_prediction_iforest_{similarity}_similarity"
        values = [float(value) for value in result.statistics[result.primary_statistic]]
        if any(not math.isfinite(value) for value in values):
            raise ValidationError(
                f"Similarity {similarity!r} produced a non-finite edge score."
            )
        statistics[feature_column] = values
        feature_columns.append(feature_column)

    if statistics is None:
        raise ValidationError(
            "link_prediction_iforest requires at least one similarity feature."
        )

    # Build rows explicitly so edge order remains the deterministic edge_id order.
    features = [
        [float(statistics.at[index, column]) for column in feature_columns]
        for index in statistics.index
    ]
    anomaly_scores = _isolation_scores(
        features,
        n_estimators=estimator_count,
        max_samples=sample_count,
        max_features=feature_count,
        bootstrap=bootstrap,
        random_state=seed,
    )
    statistics["link_prediction_iforest_score"] = anomaly_scores

    warnings = _warnings(features)
    if network.directed:
        warnings = (*warnings, DIRECTED_SEMANTICS_WARNING)
    parameters: dict[str, object] = {
        "similarities": list(similarity_names),
        "n_estimators": estimator_count,
        "max_samples": sample_count,
        "max_features": feature_count,
        "bootstrap": bootstrap,
        "random_state": seed,
    }
    if weight is not None:
        parameters["weight"] = weight
        parameters["weight_alpha"] = float(weight_alpha)
        parameters["distance_transform"] = distance_transform
    if "local_path" in similarity_names:
        parameters["epsilon"] = float(epsilon)

    return MethodResult(
        method_name="link_prediction_iforest",
        target="edge",
        statistics=statistics,
        primary_statistic="link_prediction_iforest_score",
        output_type="score",
        preferred_direction="higher",
        parameters=parameters,
        metadata=LINK_PREDICTION_IFOREST_METADATA,
        warnings=warnings,
    )


def _normalize_similarities(similarities: str | Sequence[str]) -> tuple[str, ...]:
    values: tuple[str, ...]
    if isinstance(similarities, str):
        values = (similarities,)
    elif isinstance(similarities, Sequence):
        values = tuple(similarities)
    else:
        raise ConfigurationError(
            "link_prediction_iforest parameter 'similarities' must be a string or "
            "an ordered sequence of strings."
        )
    if not values:
        raise ConfigurationError(
            "link_prediction_iforest parameter 'similarities' cannot be empty."
        )
    if any(not isinstance(value, str) for value in values):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'similarities' must contain only "
            "strings."
        )
    unknown = sorted(set(values).difference(SIMILARITIES))
    if unknown:
        allowed = ", ".join(sorted(SIMILARITIES))
        raise ConfigurationError(
            "link_prediction_iforest parameter 'similarities' contains unknown "
            f"value(s): {', '.join(unknown)}. Available similarities: {allowed}."
        )
    if len(set(values)) != len(values):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'similarities' cannot contain "
            "duplicates."
        )
    return values


def _positive_integer(value: object, *, field: str) -> int:
    number = _integer(value, field=field)
    if number <= 0:
        raise ValidationError(
            f"link_prediction_iforest parameter {field!r} must be positive."
        )
    return number


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"link_prediction_iforest parameter {field!r} must be an integer."
        )
    return value


def _max_samples(value: object) -> str | int | float:
    if value == "auto":
        return "auto"
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'max_samples' must be 'auto', a "
            "positive integer, or a float in (0, 1]."
        )
    if isinstance(value, int):
        if value <= 0:
            raise ValidationError(
                "link_prediction_iforest integer parameter 'max_samples' must be "
                "positive."
            )
        return value
    number = float(value)
    if not math.isfinite(number) or not 0.0 < number <= 1.0:
        raise ValidationError(
            "link_prediction_iforest float parameter 'max_samples' must be finite "
            "and in (0, 1]."
        )
    return number


def _max_features(value: object, available_features: int) -> int | float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'max_features' must be a positive "
            "integer or a float in (0, 1]."
        )
    if isinstance(value, int):
        if value <= 0 or value > available_features:
            raise ValidationError(
                "link_prediction_iforest integer parameter 'max_features' must be "
                f"between 1 and the {available_features} selected similarities."
            )
        return value
    number = float(value)
    if not math.isfinite(number) or not 0.0 < number <= 1.0:
        raise ValidationError(
            "link_prediction_iforest float parameter 'max_features' must be finite "
            "and in (0, 1]."
        )
    return number


def _isolation_scores(
    features: list[list[float]],
    *,
    n_estimators: int,
    max_samples: str | int | float,
    max_features: int | float,
    bootstrap: bool,
    random_state: int,
) -> list[float]:
    isolation_forest = _isolation_forest_class()
    if not features:
        return []
    try:
        model = isolation_forest(
            n_estimators=n_estimators,
            max_samples=max_samples,
            max_features=max_features,
            bootstrap=bootstrap,
            contamination="auto",
            n_jobs=1,
            random_state=random_state,
        )
        model.fit(features)
        raw_scores = model.score_samples(features)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"Isolation Forest could not score the link-prediction features: {exc}"
        ) from exc
    scores = [-float(value) for value in raw_scores]
    if any(not math.isfinite(value) for value in scores):
        raise ValidationError("Isolation Forest produced a non-finite anomaly score.")
    return scores


def _isolation_forest_class() -> Any:
    try:
        module = import_module("sklearn.ensemble")
    except ImportError as exc:
        raise ConfigurationError(
            "link_prediction_iforest requires scikit-learn. Install Netbone with "
            "`netbone[ml]` to use this method."
        ) from exc
    return module.IsolationForest


def _warnings(features: list[list[float]]) -> tuple[str, ...]:
    if len(features) < 2:
        return (
            "Isolation Forest anomaly scores are not informative with fewer than "
            "two edges.",
        )
    if len({tuple(values) for values in features}) == 1:
        return (
            "All selected link-prediction feature vectors are identical; Isolation "
            "Forest anomaly scores are tied.",
        )
    return ()
