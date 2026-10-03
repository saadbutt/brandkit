"""assemble_kit is the only writer. Facts win every argument with the draft.

These tests hand assemble_kit drafts that are confidently wrong and assert the
wrongness does not reach the kit.
"""

from __future__ import annotations

import unittest

from brandkit.assemble import AssemblyError, assemble_kit, fingerprint
from brandkit.measure import Metrics
from brandkit.schema import COLOR_ROLES, COPY_LISTS, TYPE_STEPS
from tests.support import SOURCE_NAMES, kit_for, metrics_for


class TestAssembleRejectsInvention(unittest.TestCase):
    def setUp(self):
        self.metrics = metrics_for("source-acme.html")

    def test_a_hex_the_source_never_used_cannot_reach_the_kit(self):
        kit = assemble_kit({"colors": {"primary": "#7b3fe4"}}, self.metrics)
        self.assertNotIn("#7b3fe4", kit["colors"].values())
        for hexv in kit["colors"].values():
            self.assertIn(hexv, self.metrics.colors)

    def test_a_typeface_the_page_never_loads_cannot_reach_the_kit(self):
        kit = assemble_kit({"fonts": {"family": "Comic Sans MS"}}, self.metrics)
        self.assertEqual("Space Grotesk", kit["fonts"]["family"])

    def test_a_size_the_source_never_set_cannot_reach_the_kit(self):
        kit = assemble_kit({"type_scale": {"meta": 9999.0}}, self.metrics)
        for px in kit["type_scale"].values():
            self.assertIn(px, self.metrics.type_scale_px)

    def test_a_radius_the_source_never_set_cannot_reach_the_kit(self):
        kit = assemble_kit({"radius": {"cta": "42px"}}, self.metrics)
        self.assertIn(kit["radius"]["cta"], self.metrics.radii)
        self.assertIn(kit["radius"]["card"], self.metrics.radii)

    def test_spacing_comes_from_the_source_not_the_draft(self):
        kit = assemble_kit({"spacing": ["1000rem"]}, self.metrics)
        self.assertNotIn("1000rem", kit["spacing"])
        self.assertEqual(sorted(set(self.metrics.spacing)), kit["spacing"])

    def test_copy_is_the_one_thing_the_model_is_allowed_to_write(self):
        kit = assemble_kit({"copy": {"h1": ["A line no page contained"]}}, self.metrics)
        self.assertEqual(["A line no page contained"], kit["copy"]["h1"])

    def test_an_empty_draft_still_produces_a_complete_kit(self):
        kit = assemble_kit({}, self.metrics)
        self.assertEqual(set(COLOR_ROLES), set(kit["colors"]))
        self.assertEqual(list(TYPE_STEPS), list(kit["type_scale"]))
        self.assertEqual(set(COPY_LISTS), set(kit["copy"]))

    def test_a_source_with_no_colours_is_refused_rather_than_defaulted(self):
        with self.assertRaises(AssemblyError):
            assemble_kit({}, Metrics())


class TestRoleAssignment(unittest.TestCase):
    def test_canvas_is_lighter_than_ink_on_every_source(self):
        from brandkit.assemble import _luminance

        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                kit = kit_for(name)
                self.assertGreater(
                    _luminance(kit["colors"]["canvas"]),
                    _luminance(kit["colors"]["ink"]),
                )

    def test_on_primary_contrasts_with_primary(self):
        from brandkit.assemble import _luminance

        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                kit = kit_for(name)
                gap = abs(
                    _luminance(kit["colors"]["primary"])
                    - _luminance(kit["colors"]["on-primary"])
                )
                self.assertGreater(gap, 0.3, "primary and its text are too close")

    def test_primary_is_the_most_saturated_mid_tone(self):
        kit = kit_for("source-acme.html")
        self.assertEqual("#0b5fff", kit["colors"]["primary"])

    def test_the_ramp_descends(self):
        """display down to meta is a ramp. button is not part of it."""
        from brandkit.assemble import _RAMP

        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                scale = kit_for(name)["type_scale"]
                ramp = [scale[step] for step in _RAMP]
                self.assertEqual(sorted(ramp, reverse=True), ramp)

    def test_button_sits_just_under_body(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                scale = kit_for(name)["type_scale"]
                self.assertLess(scale["button"], scale["body"])
                self.assertGreater(scale["button"], scale["meta"])

    def test_body_is_anchored_to_the_p_rule_not_to_its_position(self):
        """The naive implementation gave acme a 13px body off a 17px page."""
        expected = {
            "source-acme.html": (56.0, 32.0, 17.0, 15.0),
            "source-northwind.html": (64.0, 36.0, 18.0, 16.0),
            "source-salt.html": (52.0, 30.0, 18.0, 16.0),
        }
        for name, (display, heading, body, button) in expected.items():
            with self.subTest(source=name):
                scale = kit_for(name)["type_scale"]
                self.assertEqual(display, scale["display"])
                self.assertEqual(heading, scale["heading-md"])
                self.assertEqual(body, scale["body"])
                self.assertEqual(button, scale["button"])

    def test_steps_repeat_rather_than_interpolate_a_new_size(self):
        """Six measured sizes cannot honestly fill eight distinct steps."""
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                metrics = metrics_for(name)
                scale = kit_for(name)["type_scale"]
                self.assertLess(len(set(scale.values())), len(scale))
                for px in scale.values():
                    self.assertIn(px, metrics.type_scale_px)

    def test_cta_radius_is_no_larger_than_card_radius(self):
        from brandkit.assemble import _radius_px

        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                radius = kit_for(name)["radius"]
                self.assertLessEqual(
                    _radius_px(radius["cta"]), _radius_px(radius["card"])
                )


class TestFingerprint(unittest.TestCase):
    def test_fingerprint_ignores_copy(self):
        metrics = metrics_for("source-acme.html")
        a = assemble_kit({"copy": {"h1": ["One"]}}, metrics)
        b = assemble_kit({"copy": {"h1": ["Something else entirely"]}}, metrics)
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertNotEqual(a["copy"], b["copy"])

    def test_fingerprint_ignores_which_model_ran(self):
        metrics = metrics_for("source-acme.html")
        a = assemble_kit({}, metrics, model_id="x", provider="openai")
        b = assemble_kit({}, metrics, model_id="y", provider="anthropic")
        self.assertEqual(a["fingerprint"], b["fingerprint"])

    def test_fingerprint_changes_when_a_token_changes(self):
        kit = kit_for("source-acme.html")
        before = kit["fingerprint"]
        kit["colors"]["primary"] = "#000000"
        self.assertNotEqual(before, fingerprint(kit))

    def test_different_sources_produce_different_kits(self):
        """Guards against a pipeline that passes by emitting a constant."""
        prints = {name: kit_for(name)["fingerprint"] for name in SOURCE_NAMES}
        self.assertEqual(len(SOURCE_NAMES), len(set(prints.values())), prints)

    def test_fingerprint_is_stable_across_processes(self):
        """Pinned value. If measurement or role assignment changes, this fails
        on purpose: the whole promise is that the kit does not move."""
        self.assertEqual(
            "1c5f33e9343e0bac20a1ec280e6d0b170bb43e10c5bd663799377daf7efbbd6f",
            kit_for("source-acme.html")["fingerprint"],
        )


if __name__ == "__main__":
    unittest.main()
