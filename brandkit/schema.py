"""The closed schema the model must answer in.

Two properties matter more than the field list:

1. Unknown keys are rejected, not dropped. A model that invents a key is a
   model that has misunderstood the contract, and silently discarding it hides
   the drift instead of surfacing it.
2. Every value is typed and bounded here, so assemble_kit never has to guess
   what it was handed.

The schema describes a *draft*. A draft is a proposal, not a kit. Nothing here
is trusted against a measured fact.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Colour roles the kit paints into :root. The draft assigns measured hexes to
# these roles. It does not get to invent the hexes themselves.
COLOR_ROLES: Tuple[str, ...] = (
    "canvas", "canvas-warm", "hairline", "hairline-soft", "surface-cool",
    "scrim", "footer", "ink", "ink-soft", "graphite", "slate", "mute",
    "stone", "ash", "primary", "on-primary",
)

TYPE_STEPS: Tuple[str, ...] = (
    "display", "heading-md", "heading-sm", "subtitle", "body", "eyebrow",
    "meta", "button",
)

COPY_LISTS: Tuple[str, ...] = (
    "h1", "h2s", "leads", "bodies", "ctas", "wordmark", "links", "helpers",
    "crumbs", "fields",
)

RADIUS_KEYS: Tuple[str, ...] = ("cta", "card")
ELEVATION_KEYS: Tuple[str, ...] = ("card", "featured", "shadow")

_TOP_LEVEL: Tuple[str, ...] = (
    "colors", "fonts", "type_scale", "radius", "elevation", "spacing", "copy",
)


class SchemaError(ValueError):
    """Raised when a draft violates the schema. Never swallowed."""


def validate_draft(draft: Any) -> Dict[str, Any]:
    """Validate and normalise a model draft. Raises SchemaError on any violation.

    Returns a new dict. The input is never mutated, so a caller holding the
    draft cannot change what was validated after the fact.
    """
    if not isinstance(draft, dict):
        raise SchemaError(f"draft must be an object, got {type(draft).__name__}")

    unknown = sorted(set(draft) - set(_TOP_LEVEL))
    if unknown:
        raise SchemaError(f"unknown top-level key(s): {unknown}")

    out: Dict[str, Any] = {}
    out["colors"] = _map_of_strings(draft.get("colors", {}), COLOR_ROLES, "colors")
    out["fonts"] = _fonts(draft.get("fonts", {}))
    out["type_scale"] = _type_scale(draft.get("type_scale", {}))
    out["radius"] = _map_of_strings(draft.get("radius", {}), RADIUS_KEYS, "radius")
    out["elevation"] = _map_of_strings(
        draft.get("elevation", {}), ELEVATION_KEYS, "elevation"
    )
    out["spacing"] = _string_list(draft.get("spacing", []), "spacing")
    out["copy"] = _copy(draft.get("copy", {}))
    return out


def _map_of_strings(value: Any, allowed: Tuple[str, ...], where: str) -> Dict[str, str]:
    if not isinstance(value, dict):
        raise SchemaError(f"{where} must be an object, got {type(value).__name__}")
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        raise SchemaError(f"{where}: unknown key(s) {unknown}")
    out: Dict[str, str] = {}
    for key in allowed:
        if key in value:
            v = value[key]
            if not isinstance(v, str):
                raise SchemaError(f"{where}.{key} must be a string, got {type(v).__name__}")
            if not v.strip():
                raise SchemaError(f"{where}.{key} must not be empty")
            out[key] = v.strip()
    return out


def _fonts(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaError(f"fonts must be an object, got {type(value).__name__}")
    unknown = sorted(set(value) - {"family", "faces"})
    if unknown:
        raise SchemaError(f"fonts: unknown key(s) {unknown}")
    out: Dict[str, Any] = {}
    if "family" in value:
        if not isinstance(value["family"], str) or not value["family"].strip():
            raise SchemaError("fonts.family must be a non-empty string")
        out["family"] = value["family"].strip()
    faces = value.get("faces", [])
    if not isinstance(faces, list):
        raise SchemaError("fonts.faces must be a list")
    clean_faces = []
    for i, face in enumerate(faces):
        if not isinstance(face, dict):
            raise SchemaError(f"fonts.faces[{i}] must be an object")
        extra = sorted(set(face) - {"family", "src"})
        if extra:
            raise SchemaError(f"fonts.faces[{i}]: unknown key(s) {extra}")
        if not isinstance(face.get("family"), str) or not isinstance(face.get("src"), str):
            raise SchemaError(f"fonts.faces[{i}] needs string family and src")
        clean_faces.append({"family": face["family"].strip(), "src": face["src"].strip()})
    out["faces"] = clean_faces
    return out


def _type_scale(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        raise SchemaError(f"type_scale must be an object, got {type(value).__name__}")
    unknown = sorted(set(value) - set(TYPE_STEPS))
    if unknown:
        raise SchemaError(f"type_scale: unknown key(s) {unknown}")
    out: Dict[str, float] = {}
    for step in TYPE_STEPS:
        if step not in value:
            continue
        raw = value[step]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise SchemaError(f"type_scale.{step} must be a number, got {raw!r}")
        if raw <= 0:
            raise SchemaError(f"type_scale.{step} must be positive, got {raw}")
        out[step] = round(float(raw), 2)
    return out


def _string_list(value: Any, where: str) -> List[str]:
    if not isinstance(value, list):
        raise SchemaError(f"{where} must be a list, got {type(value).__name__}")
    out: List[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise SchemaError(f"{where}[{i}] must be a string, got {type(item).__name__}")
        item = " ".join(item.split())
        if item and item not in out:
            out.append(item)
    return out


def _copy(value: Any) -> Dict[str, List[str]]:
    if not isinstance(value, dict):
        raise SchemaError(f"copy must be an object, got {type(value).__name__}")
    unknown = sorted(set(value) - set(COPY_LISTS))
    if unknown:
        raise SchemaError(f"copy: unknown key(s) {unknown}")
    return {k: _string_list(value[k], f"copy.{k}") for k in COPY_LISTS if k in value}
