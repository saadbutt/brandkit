"""The HTML is restyled, not rebuilt.

Band order, band count and the skeleton's own tags come out the far side
unchanged. What changes is the theme and the copy. A binder that is allowed to
move a band is a binder that will eventually ship a different page than the
skeleton the client signed off.
"""

from __future__ import annotations

import unittest

from brandkit.binder import BindError, audit_skeleton, bind, check, parse_tree
from brandkit.registry import default_registry
from brandkit.render import kit_css
from tests.support import SOURCE_NAMES, kit_for, skeletons


class TestParseTree(unittest.TestCase):
    def test_repeat_suffix_expands(self):
        tree = parse_tree("# TREE\nnav-bar\ncard-row x3\nfaq-stack\n")
        self.assertEqual(
            ["nav-bar", "card-row", "card-row", "card-row", "faq-stack"], tree
        )

    def test_bullets_and_headings_are_tolerated(self):
        self.assertEqual(
            ["nav-bar", "hero-stack"],
            parse_tree("## Blocks\n\n- nav-bar\n- hero-stack\n"),
        )

    def test_an_empty_tree_is_an_error_not_an_empty_page(self):
        with self.assertRaises(BindError):
            parse_tree("# TREE\n\n")


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.registry = default_registry()

    def test_band_order_mismatch_is_rejected(self):
        html = (
            '<nav data-block="nav-bar"></nav>'
            '<header data-block="hero-stack"></header>'
        )
        with self.assertRaisesRegex(BindError, "band order"):
            check(html, ["hero-stack", "nav-bar"], self.registry)

    def test_an_unregistered_id_in_the_tree_is_rejected(self):
        html = '<section data-block="pricing-waterfall"></section>'
        with self.assertRaisesRegex(BindError, "unknown block id"):
            check(html, ["pricing-waterfall"], self.registry)

    def test_an_unregistered_block_in_the_markup_is_rejected(self):
        """The tree is clean, the markup is not. This is drift, not a gap."""
        html = (
            '<nav data-block="nav-bar"></nav>'
            '<section data-block="pricing-waterfall"></section>'
        )
        with self.assertRaisesRegex(BindError, "unregistered"):
            check(html, ["nav-bar"], self.registry)

    def test_a_slot_the_registry_does_not_list_is_rejected(self):
        html = '<nav data-block="nav-bar"><span data-slot="fields">x</span></nav>'
        with self.assertRaisesRegex(BindError, "not in the registry entry"):
            check(html, ["nav-bar"], self.registry)

    def test_every_shipped_skeleton_passes_check(self):
        for name, html, tree in skeletons():
            with self.subTest(skeleton=name):
                check(html, tree, self.registry)


class TestBind(unittest.TestCase):
    def setUp(self):
        self.registry = default_registry()
        self.kit = kit_for("source-acme.html")
        self.css = kit_css(self.kit)

    def test_layout_survives_and_theme_arrives(self):
        for name, html, tree in skeletons():
            with self.subTest(skeleton=name):
                painted = bind(html, self.kit, tree, self.registry, self.css)
                before_blocks, before_slots = audit_skeleton(html)
                after_blocks, after_slots = audit_skeleton(painted)
                self.assertEqual(before_blocks, after_blocks, "bands moved")
                self.assertEqual(before_slots, after_slots, "slots moved")
                self.assertIn('data-brandkit="kit"', painted)
                self.assertIn(self.kit["colors"]["primary"], painted)

    def test_slot_text_is_replaced_by_kit_copy(self):
        html, tree = skeletons()[0][1], skeletons()[0][2]
        painted = bind(html, self.kit, tree, self.registry, self.css)
        self.assertIn(self.kit["copy"]["h1"][0], painted)
        self.assertNotIn(">Headline<", painted)

    def test_binding_is_idempotent(self):
        """Running the pipeline twice must not stack two style blocks."""
        html, tree = skeletons()[1][1], skeletons()[1][2]
        once = bind(html, self.kit, tree, self.registry, self.css)
        twice = bind(once, self.kit, tree, self.registry, self.css)
        self.assertEqual(1, twice.count('data-brandkit="kit"'))
        self.assertEqual(once, twice)

    def test_a_different_source_repaints_the_same_skeleton(self):
        _name, html, tree = skeletons()[0]
        seen = set()
        for source in SOURCE_NAMES:
            kit = kit_for(source)
            painted = bind(html, kit, tree, self.registry, kit_css(kit))
            self.assertIn(kit["colors"]["primary"], painted)
            seen.add(painted)
        self.assertEqual(len(SOURCE_NAMES), len(seen), "sources painted alike")

    def test_copy_is_escaped_not_injected(self):
        kit = dict(self.kit)
        kit["copy"] = dict(kit["copy"], h1=['<script>alert("x")</script>'])
        html, tree = skeletons()[0][1], skeletons()[0][2]
        painted = bind(html, kit, tree, self.registry, self.css)
        self.assertNotIn("<script>", painted)
        self.assertIn("&lt;script&gt;", painted)

    def test_an_empty_copy_list_leaves_the_skeleton_text_alone(self):
        kit = dict(self.kit)
        kit["copy"] = dict(kit["copy"], wordmark=[])
        html, tree = skeletons()[0][1], skeletons()[0][2]
        painted = bind(html, kit, tree, self.registry, self.css)
        self.assertIn(">Brand<", painted)

    def test_repeated_bands_receive_successive_copy(self):
        """Three card-rows must not all say the same thing."""
        _name, html, tree = skeletons()[1]
        kit = dict(self.kit)
        kit["copy"] = dict(kit["copy"], h2s=["First", "Second", "Third", "Fourth"])
        painted = bind(html, kit, tree, self.registry, self.css)
        for word in ("First", "Second", "Third"):
            self.assertIn(f">{word}<", painted)


if __name__ == "__main__":
    unittest.main()
