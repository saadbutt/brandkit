"""Apply: every artefact is rendered from the kit, never from another artefact.

kit.css, kit.json, tokens.csv and DESIGN.md are four views of one object. The
markdown cannot claim a hex that never reached :root, because both read the
same dict. We never parse DESIGN.md back onto HTML.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List

from .registry import Registry

_CSS_VAR = {
    "canvas": "--paper", "canvas-warm": "--paper-warm", "hairline": "--hairline",
    "hairline-soft": "--hairline-soft", "surface-cool": "--surface-cool",
    "scrim": "--scrim", "footer": "--footer", "ink": "--ink", "ink-soft": "--ink-soft",
    "graphite": "--graphite", "slate": "--slate", "mute": "--mute", "stone": "--stone",
    "ash": "--ash", "primary": "--primary", "on-primary": "--on-primary",
}


def kit_json(kit: Dict[str, Any]) -> str:
    return json.dumps(kit, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def kit_css(kit: Dict[str, Any]) -> str:
    """Writes :root. This is what every layout-base.html actually consumes."""
    lines: List[str] = []
    for face in kit["fonts"]["faces"]:
        lines.append("@font-face {")
        lines.append(f"  font-family: '{face['family']}';")
        lines.append(f"  src: {face['src']};")
        lines.append("}")
    lines.append(":root {")
    for role, var in _CSS_VAR.items():
        lines.append(f"  {var}: {kit['colors'][role]};")
    lines.append(f"  --heading-font: '{kit['fonts']['family']}';")
    lines.append(f"  --body-font: '{kit['fonts']['family']}';")
    for step, px in kit["type_scale"].items():
        lines.append(f"  --size-{step}: {_px(px)};")
    lines.append(f"  --radius-cta: {_radius(kit['radius']['cta'])};")
    lines.append(f"  --radius-card: {_radius(kit['radius']['card'])};")
    lines.append(f"  --shadow-card: {kit['elevation']['shadow']};")
    lines.append(f"  --elevation-card: {kit['elevation']['card']};")
    lines.append(f"  --elevation-featured: {kit['elevation']['featured']};")
    for i, space in enumerate(kit["spacing"]):
        lines.append(f"  --space-{i}: {space};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _px(value: float) -> str:
    return f"{int(value)}px" if float(value).is_integer() else f"{value}px"


def _radius(value: str) -> str:
    if value == "none":
        return "0"
    if value == "full":
        return "9999px"
    return value


def tokens_csv(kit: Dict[str, Any]) -> str:
    """Frappe Token Manager shape: Color and Font rows."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["type", "name", "value"])
    for role, hexv in kit["colors"].items():
        writer.writerow(["Color", role, hexv])
    writer.writerow(["Font", "heading", kit["fonts"]["family"]])
    writer.writerow(["Font", "body", kit["fonts"]["family"]])
    return buf.getvalue()


def design_md(kit: Dict[str, Any], registry: Registry, tree: List[str]) -> str:
    """DESIGN.md, rendered from the kit. Same source of truth as kit.css."""
    out: List[str] = ["# DESIGN", ""]
    out.append(f"Fingerprint `{kit['fingerprint']}`")
    model = kit.get("model", {})
    if model.get("label") or model.get("id"):
        label = model.get("label") or model.get("id")
        provider = model.get("provider") or "unknown provider"
        out.append(f"Draft by {label} via {provider}. Kit assembled from measured facts.")
    out.append("")

    out.append("## Colors")
    out.append("")
    out.append("| role | hex | css var |")
    out.append("| --- | --- | --- |")
    for role, hexv in kit["colors"].items():
        out.append(f"| {role} | `{hexv}` | `{_CSS_VAR[role]}` |")
    out.append("")

    out.append("## Typeface")
    out.append("")
    out.append(f"Family: **{kit['fonts']['family']}**")
    if kit["fonts"]["faces"]:
        out.append("")
        for face in kit["fonts"]["faces"]:
            out.append(f"- `{face['family']}` loaded from `{face['src']}`")
    out.append("")

    out.append("## Type scale")
    out.append("")
    out.append("| step | size |")
    out.append("| --- | --- |")
    for step, px in kit["type_scale"].items():
        out.append(f"| {step} | {_px(px)} |")
    out.append("")

    out.append("## Radius and elevation")
    out.append("")
    out.append(f"- cta radius: `{_radius(kit['radius']['cta'])}`")
    out.append(f"- card radius: `{_radius(kit['radius']['card'])}`")
    out.append(f"- card: {kit['elevation']['card']}")
    out.append(f"- featured: {kit['elevation']['featured']}")
    out.append(f"- shadow: `{kit['elevation']['shadow']}`")
    out.append("")

    if kit["spacing"]:
        out.append("## Spacing")
        out.append("")
        out.append(", ".join(f"`{s}`" for s in kit["spacing"]))
        out.append("")

    out.append("## Slot map")
    out.append("")
    out.append("Blocks in this tree, and the slots each accepts. Ids come from the")
    out.append("registry, so a new skeleton extends this table without a template fork.")
    out.append("")
    out.append("| block | geometry | required | optional | repeat |")
    out.append("| --- | --- | --- | --- | --- |")
    for block_id in dict.fromkeys(tree):
        block = registry.get(block_id)
        out.append(
            f"| `{block.id}` | {block.geometry} | "
            f"{', '.join(block.required) or '-'} | "
            f"{', '.join(block.optional) or '-'} | {block.repeat} |"
        )
    out.append("")

    out.append("## Copy")
    out.append("")
    for key, values in kit["copy"].items():
        if not values:
            continue
        out.append(f"**{key}**")
        out.append("")
        for v in values:
            out.append(f"- {v}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"
