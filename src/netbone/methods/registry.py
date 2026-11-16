"""Registry for built-in scoring methods."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from netbone.exceptions import ConfigurationError
from netbone.methods.disparity import DISPARITY_METADATA, compute_disparity
from netbone.methods.doubly_stochastic import (
    DOUBLY_STOCHASTIC_METADATA,
    compute_doubly_stochastic,
)
from netbone.methods.edge_betweenness import (
    EDGE_BETWEENNESS_METADATA,
    compute_edge_betweenness,
)
from netbone.methods.edge_weight import EDGE_WEIGHT_METADATA, compute_edge_weight
from netbone.methods.glanb import GLANB_METADATA, compute_glanb
from netbone.methods.gspar import GSPAR_METADATA, compute_gspar
from netbone.methods.h_backbone import H_BACKBONE_METADATA, compute_h_backbone
from netbone.methods.lans import LANS_METADATA, compute_lans
from netbone.methods.link_prediction import (
    LINK_PREDICTION_METADATA,
    compute_link_prediction,
)
from netbone.methods.link_prediction_iforest import (
    LINK_PREDICTION_IFOREST_METADATA,
    compute_link_prediction_iforest,
)
from netbone.methods.link_salience import (
    LINK_SALIENCE_METADATA,
    compute_link_salience,
)
from netbone.methods.marginal_likelihood import (
    MARGINAL_LIKELIHOOD_METADATA,
    compute_marginal_likelihood,
)
from netbone.methods.maximum_spanning_forest import (
    MAXIMUM_SPANNING_FOREST_METADATA,
    compute_maximum_spanning_forest,
)
from netbone.methods.multiple_linkage import (
    MULTIPLE_LINKAGE_METADATA,
    compute_multiple_linkage,
)
from netbone.methods.node_betweenness import (
    NODE_BETWEENNESS_METADATA,
    compute_node_betweenness,
)
from netbone.methods.node_degree import NODE_DEGREE_METADATA, compute_node_degree
from netbone.methods.node_strength import (
    NODE_STRENGTH_METADATA,
    compute_node_strength,
)
from netbone.methods.noise_corrected import (
    NOISE_CORRECTED_METADATA,
    compute_noise_corrected,
)
from netbone.methods.planar_maximally_filtered_graph import (
    PLANAR_MAXIMALLY_FILTERED_GRAPH_METADATA,
    compute_planar_maximally_filtered_graph,
)
from netbone.methods.primary_linkage import (
    PRIMARY_LINKAGE_METADATA,
    compute_primary_linkage,
)
from netbone.network import Network
from netbone.results import MethodResult

MethodCompute = Callable[[Network, Mapping[str, object]], MethodResult]


@dataclass(frozen=True)
class MethodDefinition:
    """Registered scoring method metadata and execution hook."""

    name: str
    metadata: Mapping[str, object]
    compute: MethodCompute

    def __post_init__(self) -> None:
        """Freeze metadata for registry callers."""

        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def list_methods() -> tuple[str, ...]:
    """Return registered built-in method names."""

    return tuple(sorted(_METHODS))


def describe_method(name: str) -> dict[str, object]:
    """Return JSON-compatible metadata for a registered method."""

    return dict(get_method(name).metadata)


def get_method(name: str) -> MethodDefinition:
    """Return a registered method definition.

    Raises:
        ConfigurationError: If the method name is unknown.
    """

    try:
        return _METHODS[name]
    except KeyError as exc:
        allowed = ", ".join(list_methods())
        raise ConfigurationError(
            f"Unknown scoring method {name!r}. Available methods: {allowed}."
        ) from exc


def _reject_unknown_parameters(
    method_name: str,
    parameters: Mapping[str, object],
    allowed: set[str],
) -> None:
    unknown_parameters = set(parameters).difference(allowed)
    if unknown_parameters:
        unknown = ", ".join(sorted(str(name) for name in unknown_parameters))
        raise ConfigurationError(
            f"{method_name} does not accept parameter(s): {unknown}."
        )


def _compute_edge_weight(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("edge_weight", parameters, {"weight"})
    weight = parameters.get("weight")
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError("edge_weight parameter 'weight' must be a string.")
    return compute_edge_weight(network, weight=weight)


def _compute_disparity(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "disparity",
        parameters,
        {"leaf_policy", "pvalue_aggregation", "weight"},
    )
    weight = parameters.get("weight", "weight")
    pvalue_aggregation = parameters.get("pvalue_aggregation", "min")
    leaf_policy = parameters.get("leaf_policy", "ignore")
    if not isinstance(weight, str):
        raise ConfigurationError("disparity parameter 'weight' must be a string.")
    if not isinstance(pvalue_aggregation, str):
        raise ConfigurationError(
            "disparity parameter 'pvalue_aggregation' must be a string."
        )
    if not isinstance(leaf_policy, str):
        raise ConfigurationError("disparity parameter 'leaf_policy' must be a string.")
    return compute_disparity(
        network,
        weight=weight,
        pvalue_aggregation=pvalue_aggregation,
        leaf_policy=leaf_policy,
    )


def _compute_edge_betweenness(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "edge_betweenness",
        parameters,
        {"distance_transform", "normalized", "weight"},
    )
    weight = parameters.get("weight")
    distance_transform = parameters.get("distance_transform", "inverse")
    normalized = parameters.get("normalized", True)
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError(
            "edge_betweenness parameter 'weight' must be a string or None."
        )
    if not isinstance(distance_transform, str):
        raise ConfigurationError(
            "edge_betweenness parameter 'distance_transform' must be a string."
        )
    if not isinstance(normalized, bool):
        raise ConfigurationError(
            "edge_betweenness parameter 'normalized' must be a boolean."
        )
    return compute_edge_betweenness(
        network,
        weight=weight,
        distance_transform=distance_transform,
        normalized=normalized,
    )


def _compute_doubly_stochastic(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "doubly_stochastic",
        parameters,
        {"epsilon", "epsilon_mode", "max_iterations", "tolerance", "weight"},
    )
    weight = parameters.get("weight", "weight")
    epsilon = parameters.get("epsilon", 1e-4)
    epsilon_mode = parameters.get("epsilon_mode", "relative")
    tolerance = parameters.get("tolerance", 1e-12)
    max_iterations = parameters.get("max_iterations", 1000)
    if not isinstance(weight, str):
        raise ConfigurationError(
            "doubly_stochastic parameter 'weight' must be a string."
        )
    if not isinstance(epsilon, float | int) or isinstance(epsilon, bool):
        raise ConfigurationError(
            "doubly_stochastic parameter 'epsilon' must be numeric."
        )
    if not isinstance(epsilon_mode, str):
        raise ConfigurationError(
            "doubly_stochastic parameter 'epsilon_mode' must be a string."
        )
    if not isinstance(tolerance, float | int) or isinstance(tolerance, bool):
        raise ConfigurationError(
            "doubly_stochastic parameter 'tolerance' must be numeric."
        )
    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool):
        raise ConfigurationError(
            "doubly_stochastic parameter 'max_iterations' must be an integer."
        )
    return compute_doubly_stochastic(
        network,
        weight=weight,
        epsilon=float(epsilon),
        epsilon_mode=epsilon_mode,
        tolerance=float(tolerance),
        max_iterations=max_iterations,
    )


def _compute_glanb(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("glanb", parameters, {"c", "weight"})
    weight = parameters.get("weight")
    c = parameters.get("c")
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError("glanb parameter 'weight' must be a string or None.")
    if c is None:
        raise ConfigurationError("glanb requires numeric parameter 'c'.")
    if not isinstance(c, float | int) or isinstance(c, bool):
        raise ConfigurationError("glanb parameter 'c' must be numeric.")
    return compute_glanb(network, weight=weight, c=float(c))


def _compute_gspar(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("gspar", parameters, set())
    return compute_gspar(network)


def _compute_h_backbone(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "h_backbone",
        parameters,
        {"distance_transform", "weight"},
    )
    weight = parameters.get("weight", "weight")
    distance_transform = parameters.get("distance_transform", "inverse")
    if not isinstance(weight, str):
        raise ConfigurationError("h_backbone parameter 'weight' must be a string.")
    if not isinstance(distance_transform, str):
        raise ConfigurationError(
            "h_backbone parameter 'distance_transform' must be a string."
        )
    return compute_h_backbone(
        network,
        weight=weight,
        distance_transform=distance_transform,
    )


def _compute_link_salience(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "link_salience",
        parameters,
        {"distance_transform", "weight"},
    )
    weight = parameters.get("weight", "weight")
    distance_transform = parameters.get("distance_transform", "inverse")
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError("link_salience parameter 'weight' must be a string.")
    if not isinstance(distance_transform, str):
        raise ConfigurationError(
            "link_salience parameter 'distance_transform' must be a string."
        )
    return compute_link_salience(
        network,
        weight=weight,
        distance_transform=distance_transform,
    )


def _compute_link_prediction(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "link_prediction",
        parameters,
        {"distance_transform", "epsilon", "similarity", "weight", "weight_alpha"},
    )

    similarity = parameters.get("similarity")
    if not isinstance(similarity, str):
        raise ConfigurationError(
            "link_prediction requires string parameter 'similarity'."
        )
    epsilon = parameters.get("epsilon", 1.0)
    if not isinstance(epsilon, float | int) or isinstance(epsilon, bool):
        raise ConfigurationError("link_prediction parameter 'epsilon' must be numeric.")
    if similarity != "local_path" and "epsilon" in parameters:
        raise ConfigurationError(
            "link_prediction parameter 'epsilon' only applies when "
            "similarity='local_path'."
        )
    weight = parameters.get("weight")
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError(
            "link_prediction parameter 'weight' must be a string or None."
        )
    weight_alpha = parameters.get("weight_alpha", 1.0)
    if not isinstance(weight_alpha, float | int) or isinstance(weight_alpha, bool):
        raise ConfigurationError(
            "link_prediction parameter 'weight_alpha' must be numeric."
        )
    if weight is None and "weight_alpha" in parameters:
        raise ConfigurationError(
            "link_prediction parameter 'weight_alpha' only applies when "
            "parameter 'weight' is provided."
        )
    distance_transform = parameters.get("distance_transform", "inverse")
    if not isinstance(distance_transform, str):
        raise ConfigurationError(
            "link_prediction parameter 'distance_transform' must be a string."
        )
    if weight is None and "distance_transform" in parameters:
        raise ConfigurationError(
            "link_prediction parameter 'distance_transform' only applies when "
            "parameter 'weight' is provided."
        )
    return compute_link_prediction(
        network,
        similarity=similarity,
        epsilon=float(epsilon),
        weight=weight,
        weight_alpha=float(weight_alpha),
        distance_transform=distance_transform,
    )


def _compute_link_prediction_iforest(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "link_prediction_iforest",
        parameters,
        {
            "bootstrap",
            "distance_transform",
            "epsilon",
            "max_features",
            "max_samples",
            "n_estimators",
            "random_state",
            "similarities",
            "weight",
            "weight_alpha",
        },
    )

    similarities_value = parameters.get("similarities")
    selected_similarities: tuple[str, ...]
    if isinstance(similarities_value, str):
        similarities: str | Sequence[str] = similarities_value
        selected_similarities = (similarities_value,)
    elif isinstance(similarities_value, Sequence) and all(
        isinstance(value, str) for value in similarities_value
    ):
        similarities = [str(value) for value in similarities_value]
        selected_similarities = tuple(similarities)
    else:
        raise ConfigurationError(
            "link_prediction_iforest requires parameter 'similarities' as a string "
            "or an ordered sequence of strings."
        )

    epsilon = parameters.get("epsilon", 1.0)
    if not isinstance(epsilon, float | int) or isinstance(epsilon, bool):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'epsilon' must be numeric."
        )
    if "local_path" not in selected_similarities and "epsilon" in parameters:
        raise ConfigurationError(
            "link_prediction_iforest parameter 'epsilon' only applies when "
            "'local_path' is included in parameter 'similarities'."
        )

    weight = parameters.get("weight")
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'weight' must be a string or None."
        )
    weight_alpha = parameters.get("weight_alpha", 1.0)
    if not isinstance(weight_alpha, float | int) or isinstance(weight_alpha, bool):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'weight_alpha' must be numeric."
        )
    if weight is None and "weight_alpha" in parameters:
        raise ConfigurationError(
            "link_prediction_iforest parameter 'weight_alpha' only applies when "
            "parameter 'weight' is provided."
        )
    distance_transform = parameters.get("distance_transform", "inverse")
    if not isinstance(distance_transform, str):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'distance_transform' must be a string."
        )
    if weight is None and "distance_transform" in parameters:
        raise ConfigurationError(
            "link_prediction_iforest parameter 'distance_transform' only applies "
            "when parameter 'weight' is provided."
        )

    n_estimators = parameters.get("n_estimators", 100)
    if not isinstance(n_estimators, int) or isinstance(n_estimators, bool):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'n_estimators' must be an integer."
        )
    max_samples = parameters.get("max_samples", "auto")
    if isinstance(max_samples, bool) or not isinstance(max_samples, str | int | float):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'max_samples' must be 'auto' or numeric."
        )
    max_features = parameters.get("max_features", 1.0)
    if isinstance(max_features, bool) or not isinstance(max_features, int | float):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'max_features' must be numeric."
        )
    bootstrap = parameters.get("bootstrap", False)
    if not isinstance(bootstrap, bool):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'bootstrap' must be a boolean."
        )
    random_state = parameters.get("random_state", 0)
    if not isinstance(random_state, int) or isinstance(random_state, bool):
        raise ConfigurationError(
            "link_prediction_iforest parameter 'random_state' must be an integer."
        )

    return compute_link_prediction_iforest(
        network,
        similarities=similarities,
        epsilon=float(epsilon),
        weight=weight,
        weight_alpha=float(weight_alpha),
        distance_transform=distance_transform,
        n_estimators=n_estimators,
        max_samples=max_samples,
        max_features=max_features,
        bootstrap=bootstrap,
        random_state=random_state,
    )


def _compute_lans(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "lans",
        parameters,
        {"leaf_policy", "pvalue_aggregation", "weight"},
    )
    weight = parameters.get("weight", "weight")
    pvalue_aggregation = parameters.get("pvalue_aggregation", "min")
    leaf_policy = parameters.get("leaf_policy", "zero")
    if not isinstance(weight, str):
        raise ConfigurationError("lans parameter 'weight' must be a string.")
    if not isinstance(pvalue_aggregation, str):
        raise ConfigurationError(
            "lans parameter 'pvalue_aggregation' must be a string."
        )
    if not isinstance(leaf_policy, str):
        raise ConfigurationError("lans parameter 'leaf_policy' must be a string.")
    return compute_lans(
        network,
        weight=weight,
        pvalue_aggregation=pvalue_aggregation,
        leaf_policy=leaf_policy,
    )


def _compute_noise_corrected(
    network: Network, parameters: Mapping[str, object]
) -> MethodResult:
    _reject_unknown_parameters("noise_corrected", parameters, {"weight"})
    weight = parameters.get("weight", "weight")
    if not isinstance(weight, str):
        raise ConfigurationError("noise_corrected parameter 'weight' must be a string.")
    return compute_noise_corrected(network, weight=weight)


def _compute_marginal_likelihood(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("marginal_likelihood", parameters, {"weight"})
    weight = parameters.get("weight", "weight")
    if not isinstance(weight, str):
        raise ConfigurationError(
            "marginal_likelihood parameter 'weight' must be a string."
        )
    return compute_marginal_likelihood(network, weight=weight)


def _compute_maximum_spanning_forest(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("maximum_spanning_forest", parameters, {"weight"})
    weight = parameters.get("weight", "weight")
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError(
            "maximum_spanning_forest parameter 'weight' must be a string or None."
        )
    return compute_maximum_spanning_forest(network, weight=weight)


def _compute_multiple_linkage(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("multiple_linkage", parameters, {"weight"})
    weight = parameters.get("weight", "weight")
    if not isinstance(weight, str):
        raise ConfigurationError(
            "multiple_linkage parameter 'weight' must be a string."
        )
    return compute_multiple_linkage(network, weight=weight)


def _compute_node_degree(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("node_degree", parameters, set())
    return compute_node_degree(network)


def _compute_node_strength(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("node_strength", parameters, {"weight"})
    weight = parameters.get("weight", "weight")
    if not isinstance(weight, str):
        raise ConfigurationError("node_strength parameter 'weight' must be a string.")
    return compute_node_strength(network, weight=weight)


def _compute_node_betweenness(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "node_betweenness",
        parameters,
        {"distance_transform", "endpoints", "normalized", "weight"},
    )
    weight = parameters.get("weight")
    distance_transform = parameters.get("distance_transform", "inverse")
    normalized = parameters.get("normalized", True)
    endpoints = parameters.get("endpoints", False)
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError(
            "node_betweenness parameter 'weight' must be a string or None."
        )
    if not isinstance(distance_transform, str):
        raise ConfigurationError(
            "node_betweenness parameter 'distance_transform' must be a string."
        )
    if not isinstance(normalized, bool):
        raise ConfigurationError(
            "node_betweenness parameter 'normalized' must be a boolean."
        )
    if not isinstance(endpoints, bool):
        raise ConfigurationError(
            "node_betweenness parameter 'endpoints' must be a boolean."
        )
    return compute_node_betweenness(
        network,
        weight=weight,
        distance_transform=distance_transform,
        normalized=normalized,
        endpoints=endpoints,
    )


def _compute_planar_maximally_filtered_graph(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters(
        "planar_maximally_filtered_graph",
        parameters,
        {"weight"},
    )
    weight = parameters.get("weight", "weight")
    if weight is not None and not isinstance(weight, str):
        raise ConfigurationError(
            "planar_maximally_filtered_graph parameter 'weight' must be a string or "
            "None."
        )
    return compute_planar_maximally_filtered_graph(network, weight=weight)


def _compute_primary_linkage(
    network: Network,
    parameters: Mapping[str, object],
) -> MethodResult:
    _reject_unknown_parameters("primary_linkage", parameters, {"weight"})
    weight = parameters.get("weight", "weight")
    if not isinstance(weight, str):
        raise ConfigurationError("primary_linkage parameter 'weight' must be a string.")
    return compute_primary_linkage(network, weight=weight)


_METHODS: dict[str, MethodDefinition] = {
    "edge_weight": MethodDefinition(
        name="edge_weight",
        metadata=EDGE_WEIGHT_METADATA,
        compute=_compute_edge_weight,
    ),
    "edge_betweenness": MethodDefinition(
        name="edge_betweenness",
        metadata=EDGE_BETWEENNESS_METADATA,
        compute=_compute_edge_betweenness,
    ),
    "disparity": MethodDefinition(
        name="disparity",
        metadata=DISPARITY_METADATA,
        compute=_compute_disparity,
    ),
    "doubly_stochastic": MethodDefinition(
        name="doubly_stochastic",
        metadata=DOUBLY_STOCHASTIC_METADATA,
        compute=_compute_doubly_stochastic,
    ),
    "glanb": MethodDefinition(
        name="glanb",
        metadata=GLANB_METADATA,
        compute=_compute_glanb,
    ),
    "gspar": MethodDefinition(
        name="gspar",
        metadata=GSPAR_METADATA,
        compute=_compute_gspar,
    ),
    "h_backbone": MethodDefinition(
        name="h_backbone",
        metadata=H_BACKBONE_METADATA,
        compute=_compute_h_backbone,
    ),
    "lans": MethodDefinition(
        name="lans",
        metadata=LANS_METADATA,
        compute=_compute_lans,
    ),
    "link_salience": MethodDefinition(
        name="link_salience",
        metadata=LINK_SALIENCE_METADATA,
        compute=_compute_link_salience,
    ),
    "link_prediction": MethodDefinition(
        name="link_prediction",
        metadata=LINK_PREDICTION_METADATA,
        compute=_compute_link_prediction,
    ),
    "link_prediction_iforest": MethodDefinition(
        name="link_prediction_iforest",
        metadata=LINK_PREDICTION_IFOREST_METADATA,
        compute=_compute_link_prediction_iforest,
    ),
    "maximum_spanning_forest": MethodDefinition(
        name="maximum_spanning_forest",
        metadata=MAXIMUM_SPANNING_FOREST_METADATA,
        compute=_compute_maximum_spanning_forest,
    ),
    "marginal_likelihood": MethodDefinition(
        name="marginal_likelihood",
        metadata=MARGINAL_LIKELIHOOD_METADATA,
        compute=_compute_marginal_likelihood,
    ),
    "noise_corrected": MethodDefinition(
        name="noise_corrected",
        metadata=NOISE_CORRECTED_METADATA,
        compute=_compute_noise_corrected,
    ),
    "multiple_linkage": MethodDefinition(
        name="multiple_linkage",
        metadata=MULTIPLE_LINKAGE_METADATA,
        compute=_compute_multiple_linkage,
    ),
    "node_degree": MethodDefinition(
        name="node_degree",
        metadata=NODE_DEGREE_METADATA,
        compute=_compute_node_degree,
    ),
    "node_strength": MethodDefinition(
        name="node_strength",
        metadata=NODE_STRENGTH_METADATA,
        compute=_compute_node_strength,
    ),
    "node_betweenness": MethodDefinition(
        name="node_betweenness",
        metadata=NODE_BETWEENNESS_METADATA,
        compute=_compute_node_betweenness,
    ),
    "planar_maximally_filtered_graph": MethodDefinition(
        name="planar_maximally_filtered_graph",
        metadata=PLANAR_MAXIMALLY_FILTERED_GRAPH_METADATA,
        compute=_compute_planar_maximally_filtered_graph,
    ),
    "primary_linkage": MethodDefinition(
        name="primary_linkage",
        metadata=PRIMARY_LINKAGE_METADATA,
        compute=_compute_primary_linkage,
    ),
}
