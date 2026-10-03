"""Command line: measure a source, draft, assemble, emit, bind.

    python -m brandkit.cli build examples/source-acme.html --out build
    python -m brandkit.cli verify examples/source-acme.html
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import List, Optional

from .assemble import assemble_kit
from .binder import bind, parse_tree
from .measure import measure_html
from .models import StubModel, TERSE, VERBOSE
from .registry import default_registry
from .render import design_md, kit_css, kit_json, tokens_csv

SKELETONS = pathlib.Path("skeletons")


def _build(source: pathlib.Path, out: pathlib.Path, style: str) -> int:
    metrics = measure_html(source.read_text(encoding="utf-8"))
    model = StubModel(style)
    draft = model.draft(json.dumps(metrics.to_dict(), sort_keys=True))
    kit = assemble_kit(
        draft, metrics,
        model_id=model.id, model_label=model.label, provider=model.provider,
    )
    registry = default_registry()
    css = kit_css(kit)

    out.mkdir(parents=True, exist_ok=True)
    (out / "kit.json").write_text(kit_json(kit), encoding="utf-8")
    (out / "kit.css").write_text(css, encoding="utf-8")
    (out / "tokens.csv").write_text(tokens_csv(kit), encoding="utf-8")

    for skeleton in sorted(p for p in SKELETONS.iterdir() if p.is_dir()):
        tree = parse_tree((skeleton / "TREE.md").read_text(encoding="utf-8"))
        html = (skeleton / "layout-base.html").read_text(encoding="utf-8")
        painted = bind(html, kit, tree, registry, css)
        target = out / skeleton.name
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(painted, encoding="utf-8")
        (target / "DESIGN.md").write_text(
            design_md(kit, registry, tree), encoding="utf-8"
        )
        print(f"bound {skeleton.name}: {len(tree)} bands")

    print(f"fingerprint {kit['fingerprint']}")
    print(f"wrote {out}/kit.json, kit.css, tokens.csv")
    return 0


def _verify(source: pathlib.Path) -> int:
    """Two models, one kit. Exits non-zero if they disagree."""
    metrics = measure_html(source.read_text(encoding="utf-8"))
    payload = json.dumps(metrics.to_dict(), sort_keys=True)
    prints: List[str] = []
    for style in (TERSE, VERBOSE):
        model = StubModel(style)
        kit = assemble_kit(
            model.draft(payload), metrics,
            model_id=model.id, model_label=model.label, provider=model.provider,
        )
        prints.append(kit["fingerprint"])
        print(f"{model.label:<24} {kit['fingerprint']}")
    if len(set(prints)) != 1:
        print("DRIFT: models produced different kits", file=sys.stderr)
        return 1
    print("identical")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="brandkit")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="measure, assemble and bind every skeleton")
    b.add_argument("source", type=pathlib.Path)
    b.add_argument("--out", type=pathlib.Path, default=pathlib.Path("build"))
    b.add_argument("--model", choices=(TERSE, VERBOSE), default=TERSE)

    v = sub.add_parser("verify", help="assert two models produce one kit")
    v.add_argument("source", type=pathlib.Path)

    args = parser.parse_args(argv)
    if args.cmd == "build":
        return _build(args.source, args.out, args.model)
    return _verify(args.source)


if __name__ == "__main__":
    raise SystemExit(main())
