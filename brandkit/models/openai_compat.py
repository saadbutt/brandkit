"""A real adapter for any OpenAI-compatible chat endpoint, at temperature 0.

Deliberately stdlib only, and deliberately thin. The prompt asks for the closed
schema and nothing else; everything that matters to determinism happens after
this returns, in schema.validate_draft and assemble_kit.

Not exercised by the test suite, because a test that needs a network and a key
is a test that stops running. The stubs cover the contract instead.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from ..schema import COLOR_ROLES, COPY_LISTS, TYPE_STEPS

SYSTEM = (
    "You assign roles to facts that were already measured from a web page. "
    "You never invent a colour, a font family, a size or a spacing value. "
    "Reply with one JSON object and nothing else."
)

TEMPLATE = """These are the measured facts:

{metrics}

Return JSON with only these top-level keys: colors, fonts, type_scale, radius,
elevation, spacing, copy.

- colors: map any of {roles} to a hex that appears in the measured colors list.
- fonts: {{"family": one of the measured fonts}}
- type_scale: map any of {steps} to a number from the measured type_scale_px.
- radius: {{"cta": ..., "card": ...}} using a measured radius, "none" or "full".
- elevation: {{"card": "raised"|"flat", "featured": "plane"|"none", "shadow": measured}}
- spacing: a subset of the measured spacing list.
- copy: map any of {copy} to a list of strings.

Any key not listed is rejected. Any value that was not measured is discarded.
"""


class OpenAICompatModel:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        label: str = "",
        provider: str = "openai-compatible",
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.id = model
        self.label = label or model
        self.provider = provider
        self.timeout = timeout

    def draft(self, metrics_json: str) -> dict[str, Any]:
        prompt = TEMPLATE.format(
            metrics=metrics_json,
            roles=list(COLOR_ROLES),
            steps=list(TYPE_STEPS),
            copy=list(COPY_LISTS),
        )
        body = json.dumps({
            "model": self.id,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
