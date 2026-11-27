"""MkDocs hooks for the site chrome and page layout.

``on_config`` records the package version for the footer, and
``on_page_content`` wraps every table in a scroll container so wide tables
scroll sideways instead of squeezing their words.
"""

from __future__ import annotations

import re
from typing import Any

from netbone import __version__

_TABLE = re.compile(r"<table\b[^>]*>.*?</table>", re.S)


def on_config(config: Any, **_kwargs: Any) -> Any:
    config.extra["version"] = __version__
    return config


def on_page_content(html_text: str, **_kwargs: Any) -> str:
    return _TABLE.sub(
        lambda match: f'<div class="table-scroll">{match.group(0)}</div>', html_text
    )
