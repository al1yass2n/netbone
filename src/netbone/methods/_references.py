"""Literature references for the registered scoring methods.

Each method lists the paper that defines it first, followed by papers for the
measure or algorithm it builds on. The first entry also fills the method's
``reference`` and ``doi`` metadata keys.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType


def _reference(citation: str, doi: str) -> Mapping[str, str]:
    return MappingProxyType(
        {"citation": citation, "doi": doi, "url": f"https://doi.org/{doi}"}
    )


METHOD_REFERENCES: Mapping[str, tuple[Mapping[str, str], ...]] = MappingProxyType(
    {
        "edge_weight": (),
        "edge_betweenness": (
            _reference(
                "Girvan, M., & Newman, M. E. J. (2002). Community structure in "
                "social and biological networks. Proceedings of the National "
                "Academy of Sciences, 99(12), 7821–7826.",
                "10.1073/pnas.122653799",
            ),
        ),
        "disparity": (
            _reference(
                "Serrano, M. Á., Boguñá, M., & Vespignani, A. (2009). Extracting "
                "the multiscale backbone of complex weighted networks. "
                "Proceedings of the National Academy of Sciences, 106(16), "
                "6483–6488.",
                "10.1073/pnas.0808904106",
            ),
        ),
        "lans": (
            _reference(
                "Foti, N. J., Hughes, J. M., & Rockmore, D. N. (2011). "
                "Nonparametric sparsification of complex multiscale networks. "
                "PLoS ONE, 6(2), e16431.",
                "10.1371/journal.pone.0016431",
            ),
        ),
        "link_salience": (
            _reference(
                "Grady, D., Thiemann, C., & Brockmann, D. (2012). Robust "
                "classification of salient links in complex networks. Nature "
                "Communications, 3, 864.",
                "10.1038/ncomms1847",
            ),
        ),
        "link_prediction": (
            _reference(
                "Yassin, A., Cherifi, H., Seba, H., & Togni, O. (2025). High and "
                "low similarity backbone extraction using similarity-based link "
                "prediction. Applied Network Science, 10(1).",
                "10.1007/s41109-025-00705-y",
            ),
        ),
        "link_prediction_iforest": (
            _reference(
                "Yassin, A., Cherifi, H., Seba, H., & Togni, O. (2025). "
                "Integrating link prediction and isolation forest for backbone "
                "extraction. In Modelling and Mining Networks (WAW 2025), Lecture "
                "Notes in Computer Science 15699, 189–204. Springer.",
                "10.1007/978-3-031-92898-7_13",
            ),
            _reference(
                "Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation forest. "
                "In 2008 Eighth IEEE International Conference on Data Mining, "
                "413–422. IEEE.",
                "10.1109/ICDM.2008.17",
            ),
        ),
        "gspar": (
            _reference(
                "Satuluri, V., Parthasarathy, S., & Ruan, Y. (2011). Local graph "
                "sparsification for scalable clustering. In Proceedings of the "
                "2011 ACM SIGMOD International Conference on Management of Data, "
                "721–732. ACM.",
                "10.1145/1989323.1989399",
            ),
        ),
        "maximum_spanning_forest": (
            _reference(
                "Kruskal, J. B. (1956). On the shortest spanning subtree of a "
                "graph and the traveling salesman problem. Proceedings of the "
                "American Mathematical Society, 7(1), 48–50.",
                "10.1090/S0002-9939-1956-0078686-7",
            ),
            _reference(
                "Mantegna, R. N. (1999). Hierarchical structure in financial "
                "markets. The European Physical Journal B, 11(1), 193–197.",
                "10.1007/s100510050929",
            ),
        ),
        "primary_linkage": (
            _reference(
                "Nystuen, J. D., & Dacey, M. F. (1961). A graph theory "
                "interpretation of nodal regions. Papers of the Regional Science "
                "Association, 7(1), 29–42.",
                "10.1111/j.1435-5597.1961.tb01769.x",
            ),
        ),
        "multiple_linkage": (
            _reference(
                "Van Nuffel, N. (2007). Determination of the number of "
                "significant flows in origin–destination specific analysis: The "
                "case of commuting in Flanders. Regional Studies, 41(4), 509–524.",
                "10.1080/00343400701281808",
            ),
        ),
        "planar_maximally_filtered_graph": (
            _reference(
                "Tumminello, M., Aste, T., Di Matteo, T., & Mantegna, R. N. "
                "(2005). A tool for filtering information in complex systems. "
                "Proceedings of the National Academy of Sciences, 102(30), "
                "10421–10426.",
                "10.1073/pnas.0500298102",
            ),
        ),
        "h_backbone": (
            _reference(
                "Zhang, R. J., Stanley, H. E., & Ye, F. Y. (2018). Extracting "
                "h-backbone as a core structure in weighted networks. Scientific "
                "Reports, 8, 14356.",
                "10.1038/s41598-018-32430-1",
            ),
        ),
        "doubly_stochastic": (
            _reference(
                "Slater, P. B. (2009). A two-stage algorithm for extracting the "
                "multiscale backbone of complex weighted networks. Proceedings of "
                "the National Academy of Sciences, 106(26), E66.",
                "10.1073/pnas.0904725106",
            ),
        ),
        "marginal_likelihood": (
            _reference(
                "Dianati, N. (2016). Unwinding the hairball graph: Pruning "
                "algorithms for weighted complex networks. Physical Review E, "
                "93(1), 012304.",
                "10.1103/PhysRevE.93.012304",
            ),
        ),
        "noise_corrected": (
            _reference(
                "Coscia, M., & Neffke, F. M. H. (2017). Network backboning with "
                "noisy data. In 2017 IEEE 33rd International Conference on Data "
                "Engineering (ICDE), 425–436. IEEE.",
                "10.1109/ICDE.2017.100",
            ),
        ),
        "glanb": (
            _reference(
                "Zhang, X., Zhang, Z., Zhao, H., Wang, Q., & Zhu, J. (2014). "
                "Extracting the globally and locally adaptive backbone of "
                "complex networks. PLoS ONE, 9(6), e100428.",
                "10.1371/journal.pone.0100428",
            ),
        ),
        "node_degree": (
            _reference(
                "Freeman, L. C. (1978). Centrality in social networks: "
                "Conceptual clarification. Social Networks, 1(3), 215–239.",
                "10.1016/0378-8733(78)90021-7",
            ),
        ),
        "node_strength": (
            _reference(
                "Barrat, A., Barthélemy, M., Pastor-Satorras, R., & Vespignani, A. "
                "(2004). The architecture of complex weighted networks. "
                "Proceedings of the National Academy of Sciences, 101(11), "
                "3747–3752.",
                "10.1073/pnas.0400087101",
            ),
        ),
        "node_betweenness": (
            _reference(
                "Freeman, L. C. (1977). A set of measures of centrality based on "
                "betweenness. Sociometry, 40(1), 35–41.",
                "10.2307/3033543",
            ),
            _reference(
                "Brandes, U. (2001). A faster algorithm for betweenness "
                "centrality. Journal of Mathematical Sociology, 25(2), 163–177.",
                "10.1080/0022250X.2001.9990249",
            ),
        ),
    }
)

REFERENCE_NOTES: Mapping[str, str] = MappingProxyType(
    {
        "edge_weight": (
            "Edge Weight is a baseline that ranks edges by their own weight, so "
            "it has no single source paper."
        ),
    }
)


def reference_metadata(name: str) -> dict[str, object]:
    """Return the reference metadata keys for one registered method.

    ``reference`` and ``doi`` describe the defining paper, and ``references``
    lists every paper as ``citation``, ``doi``, and ``url`` entries.
    """

    references = METHOD_REFERENCES[name]
    primary = references[0] if references else None
    metadata: dict[str, object] = {
        "reference": primary["citation"] if primary else None,
        "doi": primary["doi"] if primary else None,
        "references": tuple(dict(reference) for reference in references),
    }
    if name in REFERENCE_NOTES:
        metadata["reference_note"] = REFERENCE_NOTES[name]
    return metadata
