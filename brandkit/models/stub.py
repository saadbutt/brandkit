"""Two offline models that behave differently on purpose.

They disagree about ordering, they add keys the schema does not know, they
assert hexes the source never used, and one of them is far chattier than the
other. The kit they produce is still identical, and the test suite asserts that
without a network call or an API key.

If a real provider is wired in later and the fingerprints diverge, the gap is
in assemble_kit, not in the prompt.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

TERSE = "terse"
VERBOSE = "verbose"


class StubModel:
    """A deterministic stand-in for an OpenAI-compatible model at temperature 0."""

    def __init__(self, style: str = TERSE) -> None:
        if style not in (TERSE, VERBOSE):
            raise ValueError(f"unknown stub style: {style}")
        self.style = style
        self.id = f"stub-{style}"
        self.label = f"Stub model ({style})"
        self.provider = "offline"

    def draft(self, metrics_json: str) -> Dict[str, Any]:
        m = json.loads(metrics_json)
        colors: List[str] = m.get("colors", [])
        fonts: List[str] = m.get("fonts", [])
        sizes: List[float] = m.get("type_scale_px", [])
        text: Dict[str, List[str]] = m.get("text", {})

        if self.style == TERSE:
            return {
                "colors": {
                    "canvas": _at(colors, 0),
                    "ink": _at(colors, 1),
                    "primary": _at(colors, 2),
                },
                "fonts": {"family": _at(fonts, 0)},
                "type_scale": {"display": _at(sizes, 0), "body": _at(sizes, 4)},
                "copy": {"h1": text.get("h1", [])[:1]},
            }

        # The verbose model guesses more, reorders, and invents a brand colour
        # that the source never used. None of it should reach the kit.
        return {
            "colors": {
                "primary": "#7b3fe4",          # never measured: must be rejected
                "ink": _at(colors, 1),
                "canvas": _at(colors, 0),
                "scrim": _at(colors, 3),
                "footer": _at(colors, 2),
            },
            "fonts": {"family": "Comic Sans MS"},  # never loaded: must be rejected
            "type_scale": {
                "body": _at(sizes, 4),
                "display": _at(sizes, 0),
                "meta": 9999.0,                 # not a measured size: rejected
            },
            "radius": {"cta": "42px"},          # not a measured radius: rejected
            "spacing": ["1000rem"],             # not measured: rejected
            "copy": {"h1": text.get("h1", [])[:1]},
        }


def _at(values: List[Any], index: int) -> Any:
    if not values:
        return None
    return values[min(index, len(values) - 1)]
