"""DESIGN.md and kit.css are two views of one kit, so they cannot disagree.

The usual failure mode is a markdown file written by hand next to a stylesheet
written by code. Here both render from the same dict, and this file proves it by
parsing the emitted CSS back and comparing it to the emitted markdown. Neither
artefact is ever parsed to produce the other at runtime.
"""

from __future__ import annotations

import re
import unittest

from brandkit.registry import default_registry
from brandkit.render import design_md, kit_css, kit_json, tokens_csv
from tests.support import SOURCE_NAMES, kit_for, skeletons

_VAR = re.compile(r"^\s*(--[a-z0-9-]+):\s*(.+?);\s*$", re.MULTILINE)
_MD_COLOR_ROW = re.compile(
    r"^\|\s*([a-z-]+)\s*\|\s*`(#[0-9a-f]{6})`\s*\|\s*`(--[a-z-]+)`\s*\|", re.MULTILINE
)
_MD_SIZE_ROW = re.compile(r"^\|\s*([a-z-]+)\s*\|\s*(\d+(?:\.\d+)?)px\s*\|", re.MULTILINE)


def _css_vars(css: str):
    return dict(_VAR.findall(css))


class TestDesignMatchesCss(unittest.TestCase):
    def setUp(self):
        self.registry = default_registry()
        self.tree = skeletons()[0][2]

    def test_every_colour_in_the_markdown_matches_the_stylesheet(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                kit = kit_for(name)
                css = _css_vars(kit_css(kit))
                md = design_md(kit, self.registry, self.tree)
                rows = _MD_COLOR_ROW.findall(md)
                self.assertEqual(
                    len(kit["colors"]), len(rows), "markdown dropped a role"
                )
                for role, hexv, var in rows:
                    self.assertEqual(kit["colors"][role], hexv)
                    self.assertEqual(css[var], hexv, f"{role} disagrees with :root")

    def test_every_type_step_in_the_markdown_matches_the_stylesheet(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                kit = kit_for(name)
                css = _css_vars(kit_css(kit))
                md = design_md(kit, self.registry, self.tree)
                rows = _MD_SIZE_ROW.findall(md)
                self.assertEqual(len(kit["type_scale"]), len(rows))
                for step, px in rows:
                    self.assertEqual(css[f"--size-{step}"], f"{px}px")

    def test_radius_and_shadow_agree(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                kit = kit_for(name)
                css = _css_vars(kit_css(kit))
                md = design_md(kit, self.registry, self.tree)
                self.assertIn(f"cta radius: `{css['--radius-cta']}`", md)
                self.assertIn(f"card radius: `{css['--radius-card']}`", md)
                self.assertIn(f"shadow: `{css['--shadow-card']}`", md)

    def test_the_typeface_named_in_the_markdown_is_the_one_in_root(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                kit = kit_for(name)
                css = _css_vars(kit_css(kit))
                md = design_md(kit, self.registry, self.tree)
                family = kit["fonts"]["family"]
                self.assertEqual(f"'{family}'", css["--heading-font"])
                self.assertIn(f"Family: **{family}**", md)

    def test_tokens_csv_agrees_with_the_stylesheet(self):
        kit = kit_for("source-acme.html")
        css = _css_vars(kit_css(kit))
        rows = [r.split(",") for r in tokens_csv(kit).strip().splitlines()[1:]]
        colors = {name: value for kind, name, value in rows if kind == "Color"}
        self.assertEqual(kit["colors"], colors)
        for role, hexv in colors.items():
            self.assertIn(hexv, css.values())

    def test_the_fingerprint_is_printed_in_the_markdown(self):
        kit = kit_for("source-acme.html")
        self.assertIn(kit["fingerprint"], design_md(kit, self.registry, self.tree))

    def test_the_markdown_slot_map_lists_exactly_this_trees_blocks(self):
        kit = kit_for("source-acme.html")
        for name, _html, tree in skeletons():
            with self.subTest(skeleton=name):
                md = design_md(kit, self.registry, tree)
                for block_id in set(tree):
                    self.assertIn(f"| `{block_id}` |", md)
                absent = set(self.registry.ids()) - set(tree)
                for block_id in absent:
                    self.assertNotIn(f"| `{block_id}` |", md)

    def test_kit_json_round_trips(self):
        import json

        kit = kit_for("source-acme.html")
        self.assertEqual(kit, json.loads(kit_json(kit)))

    def test_markdown_and_css_both_change_when_the_source_changes(self):
        a, b = (kit_for(n) for n in SOURCE_NAMES[:2])
        self.assertNotEqual(kit_css(a), kit_css(b))
        self.assertNotEqual(
            design_md(a, self.registry, self.tree),
            design_md(b, self.registry, self.tree),
        )

    def test_the_stylesheet_declares_every_font_face_once(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                kit = kit_for(name)
                css = kit_css(kit)
                self.assertEqual(len(kit["fonts"]["faces"]), css.count("@font-face"))


if __name__ == "__main__":
    unittest.main()
