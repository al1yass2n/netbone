"""Built-in scoring methods."""

from netbone.methods.disparity import compute_disparity
from netbone.methods.edge_weight import compute_edge_weight
from netbone.methods.lans import compute_lans
from netbone.methods.link_salience import compute_link_salience
from netbone.methods.registry import describe_method, list_methods

__all__ = [
    "compute_disparity",
    "compute_edge_weight",
    "compute_lans",
    "compute_link_salience",
    "describe_method",
    "list_methods",
]
