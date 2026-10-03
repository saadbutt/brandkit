"""The model boundary.

Everything behind this interface is untrusted. An adapter returns a draft: a
plain dict that still has to survive the schema and then lose every argument it
has with a measured fact. Swapping adapters must not change the kit, and the
determinism test is what proves it.
"""

from __future__ import annotations

from typing import Any, Dict, Protocol

Draft = Dict[str, Any]


class ModelAdapter(Protocol):
    id: str
    label: str
    provider: str

    def draft(self, metrics_json: str) -> Draft:
        """Return a draft for these measurements. Must not raise on odd input."""
        ...
