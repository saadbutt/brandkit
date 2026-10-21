"""assemble_kit is the only writer of a kit.

Templates read the kit. DESIGN.md renders from the kit. Nothing downstream
reads the draft, and nothing downstream writes to the kit. That single rule is
what stops the markdown and the page disagreeing.

The draft only ever *selects among* measured facts. A hex the source never
used cannot reach the kit, whatever the model asserts, because every value
goes through a coercion that falls back to a deterministic function of the
measurements. That is why two different models produce the same kit: the
draft's remaining freedom is narrow enough to be collapsed.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .measure import Metrics
from .schema import (
    COPY_LISTS,
    TYPE_STEPS,
    validate_draft,
)

# Fallback palette if the source yields fewer colours than roles. Derived from
# the measured set by position, so it is still a function of the source.
_DEFAULT_TYPE_PX = {
    "display": 48.0, "heading-md": 32.0, "heading-sm": 24.0, "subtitle": 20.0,
    "body": 16.0, "eyebrow": 13.0, "meta": 12.0, "button": 15.0,
}
_DEFAULT_RADIUS = {"cta": "none", "card": "none"}
_DEFAULT_ELEVATION = {"card": "flat", "featured": "none", "shadow": "none"}


class AssemblyError(ValueError):
    """Raised when a kit cannot be assembled from the measurements given."""


def assemble_kit(
    draft: Any,
    metrics: Metrics,
    *,
    model_id: str = "",
    model_label: str = "",
    provider: str = "",
) -> dict[str, Any]:
    """Build the kit. The single writer.

    draft is a proposal and is validated first. metrics are facts and win every
    disagreement. The result is ordered so that serialising it is stable.
    """
    clean = validate_draft(draft)
    if not metrics.colors:
        raise AssemblyError("source yielded no colours; nothing to build a kit from")

    kit: dict[str, Any] = {}
    kit["colors"] = _colors(clean.get("colors", {}), metrics)
    kit["fonts"] = _fonts(clean.get("fonts", {}), metrics)
    kit["type_scale"] = _type_scale(clean.get("type_scale", {}), metrics)
    kit["radius"] = _radius(clean.get("radius", {}), metrics)
    kit["elevation"] = _elevation(clean.get("elevation", {}), metrics)
    kit["spacing"] = _spacing(clean.get("spacing", []), metrics)
    kit["copy"] = _copy(clean.get("copy", {}), metrics)
    kit["model"] = {"id": model_id, "label": model_label, "provider": provider}
    kit["fingerprint"] = fingerprint(kit)
    return kit


_TOKEN_KEYS = ("colors", "fonts", "type_scale", "radius", "elevation", "spacing")


def fingerprint(kit: dict[str, Any]) -> str:
    """Stable hash of the design tokens: the part that must not drift.

    Copy and the model block are excluded on purpose. Two models may write
    different words for the same brand, and that is not drift. Two models
    producing different hexes, typefaces, sizes, radii or elevation is.
    """
    payload = {k: v for k, v in kit.items() if k in _TOKEN_KEYS}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _luminance(hexv: str) -> float:
    r, g, b = (int(hexv[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _chroma(hexv: str) -> float:
    r, g, b = (int(hexv[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b)


def _pick(palette: list[str], index: int) -> str:
    """Deterministic choice from the measured palette, never out of range."""
    return palette[index % len(palette)]


def _colors(_proposed: dict[str, str], metrics: Metrics) -> dict[str, str]:
    """Roles are derived from the measurements, not chosen by the model.

    This is the decision the whole repo turns on. Role assignment is a function
    of the source, so two models cannot disagree about it. A draft's colour
    opinions are read and discarded: if a model could nudge a role, the kit
    would depend on which model ran, which is the drift we are paid to remove.

    Ordering is by (luminance, hex) and (chroma, hex), so ties never fall back
    to dict order.
    """
    palette = metrics.colors
    by_light = sorted(palette, key=lambda c: (_luminance(c), c))
    lightest = by_light[-1]
    darkest = by_light[0]
    # Primary is the most saturated colour that is neither paper nor ink.
    mid = [c for c in palette if 0.08 < _luminance(c) < 0.92] or palette
    primary = min(mid, key=lambda c: (-_chroma(c), c))
    neutrals = [c for c in by_light if c != primary]

    def neutral(position: float) -> str:
        if not neutrals:
            return _pick(palette, 0)
        idx = min(len(neutrals) - 1, max(0, round(position * (len(neutrals) - 1))))
        return neutrals[idx]

    on_primary = lightest if _luminance(primary) < 0.5 else darkest
    return {
        "canvas": lightest,
        "canvas-warm": neutral(0.92),
        "hairline": neutral(0.78),
        "hairline-soft": neutral(0.85),
        "surface-cool": neutral(0.70),
        "scrim": neutral(0.10),
        "footer": darkest,
        "ink": darkest,
        "ink-soft": neutral(0.18),
        "graphite": neutral(0.26),
        "slate": neutral(0.34),
        "mute": neutral(0.46),
        "stone": neutral(0.58),
        "ash": neutral(0.66),
        "primary": primary,
        "on-primary": on_primary,
    }


def _fonts(_proposed: dict[str, Any], metrics: Metrics) -> dict[str, Any]:
    """The family the page actually loads. A model cannot assert a typeface."""
    family = metrics.fonts[0] if metrics.fonts else "system-ui"
    return {"family": family, "faces": list(metrics.faces)}


_RAMP = ("display", "heading-md", "heading-sm", "subtitle", "body", "eyebrow", "meta")


def _type_scale(_proposed: dict[str, float], metrics: Metrics) -> dict[str, float]:
    """Anchor the scale to real markup, then fill from the remaining sizes.

    Assigning sizes by position is the obvious implementation and it is wrong:
    it gives a 17px page a 13px body simply because 13 is the fifth largest
    number in the stylesheet. So display, heading-md and body are anchored to
    the h1, h2 and p rules the source actually declares, and the rest are
    filled from the measured sizes above and below body.

    Where the source has fewer sizes than the scale has steps, steps repeat.
    A page that declares six sizes does not contain eight steps of information,
    and repeating a measured size is honest in a way that interpolating a new
    one is not. Every value returned here appears in metrics.type_scale_px.
    """
    measured = metrics.type_scale_px
    if not measured:
        return dict(_DEFAULT_TYPE_PX)
    by_tag = metrics.sizes_by_tag

    def anchor(tag: str, fallback_index: int) -> float:
        px = by_tag.get(tag)
        if px is not None and px in measured:
            return px
        return measured[min(fallback_index, len(measured) - 1)]

    display = anchor("h1", 0)
    body = anchor("p", min(4, len(measured) - 1))
    if body > display:
        display, body = body, display

    upper = [s for s in measured if body < s < display]
    lower = [s for s in measured if s < body]

    heading_md = by_tag.get("h2")
    if heading_md is not None and heading_md in upper:
        upper = [heading_md] + [s for s in upper if s != heading_md]

    mid = _pad_head(upper, 3, body)          # heading-md, heading-sm, subtitle
    small = _pad_tail(lower, 2, body)        # eyebrow, meta

    ramp = [display, *mid, body, *small]
    scale = dict(zip(_RAMP, ramp))
    # Button text is not part of a descending ramp. It is the step just under
    # body, which is where every one of these sources actually puts it.
    scale["button"] = lower[0] if lower else body
    return {step: round(float(scale[step]), 2) for step in TYPE_STEPS}


def _pad_head(values: list[float], count: int, pad: float) -> list[float]:
    """First `count` values, largest first, padded toward `pad`."""
    out = list(values[:count])
    while len(out) < count:
        out.append(pad)
    return out


def _pad_tail(values: list[float], count: int, pad: float) -> list[float]:
    """Last `count` values, so the small end of the scale stays small."""
    out = list(values[-count:]) if values else []
    while len(out) < count:
        out.insert(0, pad)
    return out


def _radius(_proposed: dict[str, str], metrics: Metrics) -> dict[str, str]:
    if not metrics.radii:
        return dict(_DEFAULT_RADIUS)
    ordered = sorted(metrics.radii, key=lambda r: (_radius_px(r), r))
    return {"cta": ordered[0], "card": ordered[-1]}


def _radius_px(value: str) -> float:
    match = re.search(r"([\d.]+)\s*px", value)
    if match:
        return float(match.group(1))
    return 9999.0 if "%" in value or "full" in value else 0.0


def _elevation(_proposed: dict[str, str], metrics: Metrics) -> dict[str, str]:
    shadows = sorted(metrics.shadows)
    return {
        "card": "raised" if shadows else "flat",
        "featured": "plane" if len(shadows) > 1 else "none",
        "shadow": shadows[0] if shadows else _DEFAULT_ELEVATION["shadow"],
    }


def _spacing(_proposed: list[str], metrics: Metrics) -> list[str]:
    return sorted(set(metrics.spacing))


def _copy(proposed: dict[str, list[str]], metrics: Metrics) -> dict[str, list[str]]:
    """Copy is the one place a model earns its keep, so it is allowed through.

    It is deliberately outside the token fingerprint: two models may write
    different words for the same brand, and that is not drift. Where a model
    said nothing we fall back to text measured off the source rather than
    inventing any.
    """
    measured = metrics.text
    fallback = {
        "h1": measured.get("h1", [])[:1],
        "h2s": measured.get("h2", []),
        "leads": measured.get("p", [])[:2],
        "bodies": measured.get("p", []),
        "ctas": measured.get("button", []) + measured.get("a", [])[:2],
        "wordmark": [],
        "links": measured.get("a", []),
        "helpers": [],
        "crumbs": [],
        "fields": [],
    }
    out: dict[str, list[str]] = {}
    for key in COPY_LISTS:
        value = proposed.get(key)
        out[key] = list(value) if value else list(fallback.get(key, []))
    return out
