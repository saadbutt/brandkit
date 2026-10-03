"""A ninth page is a registry entry, not a template fork.

This is the test that decides whether the architecture actually holds. A new
block is registered, a new skeleton uses it, and it binds. The existing
skeletons must come out byte for byte identical to how they came out before the
new block existed, and assemble_kit must not be touched to make it work.

If adding a block ever requires editing assemble.py, render.py or binder.py,
this test is where that shows up.
"""

from __future__ import annotations

import unittest

from brandkit.binder import audit_skeleton, bind, check, parse_tree
from brandkit.registry import REPEAT_MANY, Block, Registry, default_registry
from brandkit.render import design_md, kit_css
from tests.support import kit_for, skeletons

PRICING_LADDER = Block(
    "pricing-ladder",
    "grid",
    required=("h2s",),
    optional=("bodies", "ctas", "helpers"),
    repeat=REPEAT_MANY,
)

NEW_SKELETON_TREE = """# TREE
nav-bar
hero-stack
pricing-ladder x2
faq-stack
footer-legal
"""

NEW_SKELETON_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Pricing</title>
</head>
<body>
<nav data-block="nav-bar"><span data-slot="wordmark">Brand</span></nav>
<header data-block="hero-stack"><h1 data-slot="h1">Headline</h1></header>
<section data-block="pricing-ladder"><h2 data-slot="h2s">Tier</h2><p data-slot="bodies">Body</p><button data-slot="ctas">Act</button></section>
<section data-block="pricing-ladder"><h2 data-slot="h2s">Tier</h2><p data-slot="bodies">Body</p><button data-slot="ctas">Act</button></section>
<section data-block="faq-stack"><h2 data-slot="h2s">FAQ</h2></section>
<footer data-block="footer-legal"><small data-slot="helpers">Legal</small></footer>
</body>
</html>
"""


class TestNewBlock(unittest.TestCase):
    def setUp(self):
        self.kit = kit_for("source-acme.html")
        self.css = kit_css(self.kit)
        self.base = default_registry()
        self.extended = default_registry()
        self.extended.register(PRICING_LADDER)

    def test_the_new_block_is_unknown_before_it_is_registered(self):
        tree = parse_tree(NEW_SKELETON_TREE)
        with self.assertRaises(Exception):
            check(NEW_SKELETON_HTML, tree, self.base)

    def test_the_new_skeleton_binds_once_the_block_is_registered(self):
        tree = parse_tree(NEW_SKELETON_TREE)
        painted = bind(NEW_SKELETON_HTML, self.kit, tree, self.extended, self.css)
        blocks, _slots = audit_skeleton(painted)
        self.assertEqual(tree, blocks)
        self.assertIn(self.kit["colors"]["primary"], painted)
        self.assertIn(self.kit["copy"]["h1"][0], painted)

    def test_the_existing_skeletons_are_byte_identical_before_and_after(self):
        for name, html, tree in skeletons():
            with self.subTest(skeleton=name):
                before = bind(html, self.kit, tree, self.base, self.css)
                after = bind(html, self.kit, tree, self.extended, self.css)
                self.assertEqual(before, after)

    def test_the_kit_itself_does_not_move(self):
        """The registry knows about blocks. The kit knows about tokens. Adding a
        block cannot change a hex, so the fingerprint is unchanged."""
        self.assertEqual(
            kit_for("source-acme.html")["fingerprint"], self.kit["fingerprint"]
        )
        self.assertEqual(self.css, kit_css(self.kit))

    def test_the_new_block_appears_in_its_own_design_md_and_no_others(self):
        new_tree = parse_tree(NEW_SKELETON_TREE)
        new_md = design_md(self.kit, self.extended, new_tree)
        self.assertIn("| `pricing-ladder` | grid |", new_md)
        for name, _html, tree in skeletons():
            with self.subTest(skeleton=name):
                self.assertNotIn(
                    "pricing-ladder", design_md(self.kit, self.extended, tree)
                )

    def test_a_new_block_with_an_unregistered_slot_is_still_rejected(self):
        """Registering a block widens the contract by exactly its own slots."""
        registry = Registry([PRICING_LADDER])
        html = (
            '<section data-block="pricing-ladder">'
            '<label data-slot="fields">Email</label></section>'
        )
        with self.assertRaises(Exception):
            check(html, ["pricing-ladder"], registry)

    def test_adding_a_block_does_not_renumber_the_existing_ids(self):
        self.assertEqual(self.base.ids(), self.extended.ids()[: len(self.base)])
        self.assertEqual(len(self.base) + 1, len(self.extended))


if __name__ == "__main__":
    unittest.main()
