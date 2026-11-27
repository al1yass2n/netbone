"""MkDocs hook that renders LaTeX math as MathML when the site is built.

``pymdownx.arithmatex`` in generic mode wraps each formula in a span or div
and keeps its LaTeX source. This hook converts that source to MathML, so the
pages show typeset math without loading a JavaScript renderer.
"""

from __future__ import annotations

import html
import re
from typing import Any

from latex2mathml.converter import convert

_BLOCK = re.compile(r'<div class="arithmatex">\\\[(?P<tex>.*?)\\\]</div>', re.S)
_INLINE = re.compile(r'<span class="arithmatex">\\\((?P<tex>.*?)\\\)</span>', re.S)


def _render(match: re.Match[str], *, display: str) -> str:
    tex = html.unescape(match.group("tex")).strip()
    mathml = convert(tex, display=display)
    if display == "block":
        return f'<div class="math-block">{mathml}</div>'
    return mathml


def on_page_content(html_text: str, **_kwargs: Any) -> str:
    html_text = _BLOCK.sub(lambda match: _render(match, display="block"), html_text)
    return _INLINE.sub(lambda match: _render(match, display="inline"), html_text)
