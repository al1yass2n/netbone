"""Literature references for the registered scoring methods.

Each method lists the paper that defines it first, followed by papers for the
measure or algorithm it builds on. The first entry also fills the method's
``reference`` and ``doi`` metadata keys. Every entry is stored once, as
structured fields, and rendered both as a citation and as a BibTeX record.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

_TITLE_STOPWORDS = frozenset({"a", "an", "the", "on", "of"})


@dataclass(frozen=True)
class _Paper:
    authors: tuple[tuple[str, str], ...]
    year: int
    title: str
    doi: str
    journal: str | None = None
    volume: str | None = None
    number: str | None = None
    pages: str | None = None
    booktitle: str | None = None
    series: str | None = None
    publisher: str | None = None

    @property
    def is_article(self) -> bool:
        return self.journal is not None

    def citation(self) -> str:
        """Render an APA-style citation."""

        names = [f"{family}, {given}" for family, given in self.authors]
        if len(names) == 1:
            authors = names[0]
        elif len(names) == 2:
            authors = f"{names[0]}, & {names[1]}"
        else:
            authors = ", ".join(names[:-1]) + f", & {names[-1]}"
        head = f"{authors} ({self.year}). {self.title}."
        if self.is_article:
            source = str(self.journal)
            if self.volume:
                source += f", {self.volume}"
                if self.number:
                    source += f"({self.number})"
            if self.pages:
                source += f", {self.pages}"
            return f"{head} {source}."
        source = f"In {self.booktitle}"
        if self.series:
            source += f", {self.series} {self.volume}"
        if self.pages:
            source += f", {self.pages}"
        return f"{head} {source}. {self.publisher}."

    def bibtex_key(self) -> str:
        family = _ascii(self.authors[0][0]).lower().replace(" ", "")
        words = [
            "".join(character for character in word if character.isalnum())
            for word in _ascii(self.title).lower().split()
        ]
        first_word = next(
            word for word in words if word and word not in _TITLE_STOPWORDS
        )
        return f"{family}{self.year}{first_word}"

    def bibtex(self) -> str:
        """Render a BibTeX record."""

        authors = " and ".join(f"{family}, {given}" for family, given in self.authors)
        fields: list[tuple[str, str | None]] = [
            ("author", authors),
            ("title", self.title),
        ]
        if self.is_article:
            kind = "article"
            fields += [
                ("journal", self.journal),
                ("year", str(self.year)),
                ("volume", self.volume),
                ("number", self.number),
            ]
        else:
            kind = "inproceedings"
            fields += [
                ("booktitle", self.booktitle),
                ("series", self.series),
                ("volume", self.volume if self.series else None),
                ("year", str(self.year)),
                ("publisher", self.publisher),
            ]
        fields += [
            ("pages", self.pages.replace("–", "--") if self.pages else None),
            ("doi", self.doi),
        ]
        body = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields if value)
        return f"@{kind}{{{self.bibtex_key()},\n{body}\n}}"

    def as_metadata(self) -> dict[str, str]:
        return {
            "citation": self.citation(),
            "doi": self.doi,
            "url": f"https://doi.org/{self.doi}",
            "bibtex": self.bibtex(),
        }


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


PNAS = "Proceedings of the National Academy of Sciences"

METHOD_PAPERS: Mapping[str, tuple[_Paper, ...]] = MappingProxyType(
    {
        "edge_weight": (),
        "edge_betweenness": (
            _Paper(
                authors=(("Girvan", "M."), ("Newman", "M. E. J.")),
                year=2002,
                title="Community structure in social and biological networks",
                journal=PNAS,
                volume="99",
                number="12",
                pages="7821–7826",
                doi="10.1073/pnas.122653799",
            ),
        ),
        "disparity": (
            _Paper(
                authors=(
                    ("Serrano", "M. Á."),
                    ("Boguñá", "M."),
                    ("Vespignani", "A."),
                ),
                year=2009,
                title="Extracting the multiscale backbone of complex weighted networks",
                journal=PNAS,
                volume="106",
                number="16",
                pages="6483–6488",
                doi="10.1073/pnas.0808904106",
            ),
        ),
        "lans": (
            _Paper(
                authors=(("Foti", "N. J."), ("Hughes", "J. M."), ("Rockmore", "D. N.")),
                year=2011,
                title="Nonparametric sparsification of complex multiscale networks",
                journal="PLoS ONE",
                volume="6",
                number="2",
                pages="e16431",
                doi="10.1371/journal.pone.0016431",
            ),
        ),
        "link_salience": (
            _Paper(
                authors=(("Grady", "D."), ("Thiemann", "C."), ("Brockmann", "D.")),
                year=2012,
                title="Robust classification of salient links in complex networks",
                journal="Nature Communications",
                volume="3",
                pages="864",
                doi="10.1038/ncomms1847",
            ),
        ),
        "link_prediction": (
            _Paper(
                authors=(
                    ("Yassin", "A."),
                    ("Cherifi", "H."),
                    ("Seba", "H."),
                    ("Togni", "O."),
                ),
                year=2025,
                title=(
                    "High and low similarity backbone extraction using "
                    "similarity-based link prediction"
                ),
                journal="Applied Network Science",
                volume="10",
                number="1",
                doi="10.1007/s41109-025-00705-y",
            ),
        ),
        "link_prediction_iforest": (
            _Paper(
                authors=(
                    ("Yassin", "A."),
                    ("Cherifi", "H."),
                    ("Seba", "H."),
                    ("Togni", "O."),
                ),
                year=2025,
                title=(
                    "Integrating link prediction and isolation forest for "
                    "backbone extraction"
                ),
                booktitle="Modelling and Mining Networks (WAW 2025)",
                series="Lecture Notes in Computer Science",
                volume="15699",
                pages="189–204",
                publisher="Springer",
                doi="10.1007/978-3-031-92898-7_13",
            ),
            _Paper(
                authors=(("Liu", "F. T."), ("Ting", "K. M."), ("Zhou", "Z.-H.")),
                year=2008,
                title="Isolation forest",
                booktitle="2008 Eighth IEEE International Conference on Data Mining",
                pages="413–422",
                publisher="IEEE",
                doi="10.1109/ICDM.2008.17",
            ),
        ),
        "gspar": (
            _Paper(
                authors=(
                    ("Satuluri", "V."),
                    ("Parthasarathy", "S."),
                    ("Ruan", "Y."),
                ),
                year=2011,
                title="Local graph sparsification for scalable clustering",
                booktitle=(
                    "Proceedings of the 2011 ACM SIGMOD International Conference "
                    "on Management of Data"
                ),
                pages="721–732",
                publisher="ACM",
                doi="10.1145/1989323.1989399",
            ),
        ),
        "maximum_spanning_forest": (
            _Paper(
                authors=(("Kruskal", "J. B."),),
                year=1956,
                title=(
                    "On the shortest spanning subtree of a graph and the "
                    "traveling salesman problem"
                ),
                journal="Proceedings of the American Mathematical Society",
                volume="7",
                number="1",
                pages="48–50",
                doi="10.1090/S0002-9939-1956-0078686-7",
            ),
            _Paper(
                authors=(("Mantegna", "R. N."),),
                year=1999,
                title="Hierarchical structure in financial markets",
                journal="The European Physical Journal B",
                volume="11",
                number="1",
                pages="193–197",
                doi="10.1007/s100510050929",
            ),
        ),
        "primary_linkage": (
            _Paper(
                authors=(("Nystuen", "J. D."), ("Dacey", "M. F.")),
                year=1961,
                title="A graph theory interpretation of nodal regions",
                journal="Papers of the Regional Science Association",
                volume="7",
                number="1",
                pages="29–42",
                doi="10.1111/j.1435-5597.1961.tb01769.x",
            ),
        ),
        "multiple_linkage": (
            _Paper(
                authors=(("Van Nuffel", "N."),),
                year=2007,
                title=(
                    "Determination of the number of significant flows in "
                    "origin–destination specific analysis: The case of commuting "
                    "in Flanders"
                ),
                journal="Regional Studies",
                volume="41",
                number="4",
                pages="509–524",
                doi="10.1080/00343400701281808",
            ),
        ),
        "planar_maximally_filtered_graph": (
            _Paper(
                authors=(
                    ("Tumminello", "M."),
                    ("Aste", "T."),
                    ("Di Matteo", "T."),
                    ("Mantegna", "R. N."),
                ),
                year=2005,
                title="A tool for filtering information in complex systems",
                journal=PNAS,
                volume="102",
                number="30",
                pages="10421–10426",
                doi="10.1073/pnas.0500298102",
            ),
        ),
        "h_backbone": (
            _Paper(
                authors=(("Zhang", "R. J."), ("Stanley", "H. E."), ("Ye", "F. Y.")),
                year=2018,
                title="Extracting h-backbone as a core structure in weighted networks",
                journal="Scientific Reports",
                volume="8",
                pages="14356",
                doi="10.1038/s41598-018-32430-1",
            ),
        ),
        "doubly_stochastic": (
            _Paper(
                authors=(("Slater", "P. B."),),
                year=2009,
                title=(
                    "A two-stage algorithm for extracting the multiscale backbone "
                    "of complex weighted networks"
                ),
                journal=PNAS,
                volume="106",
                number="26",
                pages="E66",
                doi="10.1073/pnas.0904725106",
            ),
        ),
        "marginal_likelihood": (
            _Paper(
                authors=(("Dianati", "N."),),
                year=2016,
                title=(
                    "Unwinding the hairball graph: Pruning algorithms for weighted "
                    "complex networks"
                ),
                journal="Physical Review E",
                volume="93",
                number="1",
                pages="012304",
                doi="10.1103/PhysRevE.93.012304",
            ),
        ),
        "noise_corrected": (
            _Paper(
                authors=(("Coscia", "M."), ("Neffke", "F. M. H.")),
                year=2017,
                title="Network backboning with noisy data",
                booktitle=(
                    "2017 IEEE 33rd International Conference on Data Engineering (ICDE)"
                ),
                pages="425–436",
                publisher="IEEE",
                doi="10.1109/ICDE.2017.100",
            ),
        ),
        "glanb": (
            _Paper(
                authors=(
                    ("Zhang", "X."),
                    ("Zhang", "Z."),
                    ("Zhao", "H."),
                    ("Wang", "Q."),
                    ("Zhu", "J."),
                ),
                year=2014,
                title=(
                    "Extracting the globally and locally adaptive backbone of "
                    "complex networks"
                ),
                journal="PLoS ONE",
                volume="9",
                number="6",
                pages="e100428",
                doi="10.1371/journal.pone.0100428",
            ),
        ),
        "node_degree": (
            _Paper(
                authors=(("Freeman", "L. C."),),
                year=1978,
                title="Centrality in social networks: Conceptual clarification",
                journal="Social Networks",
                volume="1",
                number="3",
                pages="215–239",
                doi="10.1016/0378-8733(78)90021-7",
            ),
        ),
        "node_strength": (
            _Paper(
                authors=(
                    ("Barrat", "A."),
                    ("Barthélemy", "M."),
                    ("Pastor-Satorras", "R."),
                    ("Vespignani", "A."),
                ),
                year=2004,
                title="The architecture of complex weighted networks",
                journal=PNAS,
                volume="101",
                number="11",
                pages="3747–3752",
                doi="10.1073/pnas.0400087101",
            ),
        ),
        "node_betweenness": (
            _Paper(
                authors=(("Freeman", "L. C."),),
                year=1977,
                title="A set of measures of centrality based on betweenness",
                journal="Sociometry",
                volume="40",
                number="1",
                pages="35–41",
                doi="10.2307/3033543",
            ),
            _Paper(
                authors=(("Brandes", "U."),),
                year=2001,
                title="A faster algorithm for betweenness centrality",
                journal="Journal of Mathematical Sociology",
                volume="25",
                number="2",
                pages="163–177",
                doi="10.1080/0022250X.2001.9990249",
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
    lists every paper as ``citation``, ``doi``, ``url``, and ``bibtex``
    entries.
    """

    references = tuple(paper.as_metadata() for paper in METHOD_PAPERS[name])
    primary = references[0] if references else None
    metadata: dict[str, object] = {
        "reference": primary["citation"] if primary else None,
        "doi": primary["doi"] if primary else None,
        "references": references,
    }
    if name in REFERENCE_NOTES:
        metadata["reference_note"] = REFERENCE_NOTES[name]
    return metadata
