"""Two models, one kit. This is the test the whole design serves.

The two stubs disagree on purpose: different key order, invented hexes, an
invented typeface, sizes and radii the source never set, and one is far
chattier than the other. If the kits still match, the model has no vote on
facts. When this test first ran it failed, which is why role assignment is a
function of the measurements rather than a model's choice.
"""

from __future__ import annotations

import json
import unittest

from brandkit.assemble import assemble_kit
from brandkit.models import TERSE, VERBOSE, StubModel
from brandkit.render import kit_css, kit_json, tokens_csv
from tests.support import SOURCE_NAMES, STYLES, metrics_for


class TestTwoModelsOneKit(unittest.TestCase):
    def _kits(self, name):
        metrics = metrics_for(name)
        payload = json.dumps(metrics.to_dict(), sort_keys=True)
        out = []
        for style in STYLES:
            model = StubModel(style)
            out.append(
                assemble_kit(
                    model.draft(payload), metrics,
                    model_id=model.id, model_label=model.label,
                    provider=model.provider,
                )
            )
        return out

    def test_the_stubs_actually_disagree(self):
        """Otherwise this file proves nothing."""
        payload = json.dumps(metrics_for("source-acme.html").to_dict(), sort_keys=True)
        terse = StubModel(TERSE).draft(payload)
        verbose = StubModel(VERBOSE).draft(payload)
        self.assertNotEqual(terse, verbose)
        self.assertEqual("#7b3fe4", verbose["colors"]["primary"])
        self.assertEqual("Comic Sans MS", verbose["fonts"]["family"])

    def test_fingerprints_match_on_every_source(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                prints = {kit["fingerprint"] for kit in self._kits(name)}
                self.assertEqual(1, len(prints), prints)

    def test_every_token_matches_not_just_the_hash(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                a, b = self._kits(name)
                for key in ("colors", "fonts", "type_scale", "radius",
                            "elevation", "spacing"):
                    self.assertEqual(a[key], b[key], f"{name}: {key} drifted")

    def test_emitted_artefacts_are_byte_identical(self):
        """kit.css and tokens.csv are what a client actually consumes."""
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                a, b = self._kits(name)
                self.assertEqual(kit_css(a), kit_css(b))
                self.assertEqual(tokens_csv(a), tokens_csv(b))

    def test_only_the_model_block_and_copy_may_differ(self):
        a, b = self._kits("source-acme.html")
        differing = {k for k in a if a[k] != b[k]}
        self.assertTrue(differing <= {"model", "copy"}, differing)

    def test_the_same_model_twice_is_byte_identical(self):
        metrics = metrics_for("source-acme.html")
        payload = json.dumps(metrics.to_dict(), sort_keys=True)
        model = StubModel(TERSE)
        first = assemble_kit(model.draft(payload), metrics)
        second = assemble_kit(model.draft(payload), metrics)
        self.assertEqual(kit_json(first), kit_json(second))


if __name__ == "__main__":
    unittest.main()
