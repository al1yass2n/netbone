"""Structured literature references rendered as citations and BibTeX.

Method and temporal weighting metadata both list their source papers through
:class:`Paper`, so every entry is stored once and rendered the same way in the
API, reports, documentation, and web app.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

_TITLE_STOPWORDS = frozenset({"a", "an", "the", "on", "of"})


@dataclass(frozen=True)
class Paper:
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


def reference_metadata(
    papers: tuple[Paper, ...], note: str | None = None
) -> dict[str, object]:
    """Return the ``reference``, ``doi``, and ``references`` metadata keys.

    ``reference`` and ``doi`` describe the first paper, and ``references``
    lists every paper as ``citation``, ``doi``, ``url``, and ``bibtex``
    entries. ``reference_note`` explains an entry without a source paper.
    """

    references = tuple(paper.as_metadata() for paper in papers)
    primary = references[0] if references else None
    metadata: dict[str, object] = {
        "reference": primary["citation"] if primary else None,
        "doi": primary["doi"] if primary else None,
        "references": references,
    }
    if note is not None:
        metadata["reference_note"] = note
    return metadata
