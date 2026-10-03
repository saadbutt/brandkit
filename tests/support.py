"""Shared fixtures. Tests read the real example sources, not hand-written stubs.

The job this repo answers says "a few real sources", so the suite measures the
same files the CLI measures. A test that only ever sees a toy source will pass
on a pipeline that cannot read a real page.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Tuple

from brandkit.assemble import assemble_kit
from brandkit.binder import parse_tree
from brandkit.measure import Metrics, measure_html
from brandkit.models import StubModel, TERSE, VERBOSE

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
SKELETONS = ROOT / "skeletons"

SOURCE_NAMES: Tuple[str, ...] = (
    "source-acme.html",
    "source-northwind.html",
    "source-salt.html",
)

STYLES: Tuple[str, ...] = (TERSE, VERBOSE)


def source_text(name: str) -> str:
    return (EXAMPLES / name).read_text(encoding="utf-8")


def sources() -> List[Tuple[str, str]]:
    return [(name, source_text(name)) for name in SOURCE_NAMES]


def metrics_for(name: str) -> Metrics:
    return measure_html(source_text(name))


def kit_for(name: str, style: str = TERSE) -> Dict[str, Any]:
    metrics = metrics_for(name)
    model = StubModel(style)
    draft = model.draft(json.dumps(metrics.to_dict(), sort_keys=True))
    return assemble_kit(
        draft, metrics,
        model_id=model.id, model_label=model.label, provider=model.provider,
    )


def skeletons() -> List[Tuple[str, str, List[str]]]:
    """(name, layout html, tree) for every skeleton on disk."""
    out = []
    for path in sorted(p for p in SKELETONS.iterdir() if p.is_dir()):
        html = (path / "layout-base.html").read_text(encoding="utf-8")
        tree = parse_tree((path / "TREE.md").read_text(encoding="utf-8"))
        out.append((path.name, html, tree))
    return out
