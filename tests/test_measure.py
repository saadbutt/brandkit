"""Measurement is the floor the rest of the repo stands on.

If measure_html is wrong, every downstream guarantee is a guarantee about the
wrong facts. So these assertions are about specific values in the real sources,
not about shapes.
"""

from __future__ import annotations

import unittest

from brandkit.measure import measure_html
from tests.support import SOURCE_NAMES, metrics_for, source_text


class TestMeasureRealSources(unittest.TestCase):
    def test_every_source_yields_colors_fonts_and_sizes(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                m = metrics_for(name)
                self.assertTrue(m.colors, "no colours measured")
                self.assertTrue(m.fonts, "no font families measured")
                self.assertTrue(m.type_scale_px, "no type scale measured")
                self.assertTrue(m.radii, "no radii measured")
                self.assertTrue(m.shadows, "no shadows measured")
                self.assertTrue(m.text["h1"], "no h1 text measured")

    def test_acme_exact_facts(self):
        m = metrics_for("source-acme.html")
        self.assertIn("#0b5fff", m.colors)
        self.assertIn("#f7f5f2", m.colors)
        self.assertIn("#16181d", m.colors)
        self.assertEqual("Space Grotesk", m.fonts[0])
        self.assertEqual(56.0, max(m.type_scale_px))
        self.assertIn("8px", m.radii)
        self.assertIn("14px", m.radii)

    def test_webfont_family_is_read_from_the_stylesheet_link(self):
        """Fraunces is only named in the Google Fonts href and the @font-face."""
        m = metrics_for("source-salt.html")
        self.assertIn("Fraunces", m.fonts)

    def test_font_size_is_attributed_to_the_tag_that_declares_it(self):
        for name, expected in (
            ("source-acme.html", {"h1": 56.0, "h2": 32.0, "p": 17.0}),
            ("source-northwind.html", {"h1": 64.0, "h2": 36.0, "p": 18.0}),
            ("source-salt.html", {"h1": 52.0, "h2": 30.0, "p": 18.0}),
        ):
            with self.subTest(source=name):
                by_tag = metrics_for(name).sizes_by_tag
                for tag, px in expected.items():
                    self.assertEqual(px, by_tag[tag])

    def test_a_later_rule_wins_as_it_would_in_css(self):
        m = measure_html("<style>p{font-size:14px}p{font-size:18px}</style>")
        self.assertEqual(18.0, m.sizes_by_tag["p"])

    def test_class_selectors_are_not_attributed_to_a_tag(self):
        m = measure_html("<style>.btn{font-size:15px}</style>")
        self.assertEqual({}, m.sizes_by_tag)

    def test_a_selector_group_attributes_to_every_tag_in_it(self):
        m = measure_html("<style>h2, h3 {font-size:24px}</style>")
        self.assertEqual({"h2": 24.0, "h3": 24.0}, m.sizes_by_tag)

    def test_rem_sizes_are_converted_to_px(self):
        m = measure_html("<style>p{font-size:1.125rem}</style>")
        self.assertEqual(18.0, m.sizes_by_tag["p"])

    def test_rgba_is_normalised_to_hex(self):
        m = measure_html(
            "<style>.c{box-shadow:0 1px 2px rgba(22,24,29,0.06);color:#fff}</style>"
        )
        self.assertIn("#16181d", m.colors)

    def test_short_hex_is_expanded(self):
        m = measure_html("<style>body{color:#ABC}</style>")
        self.assertIn("#aabbcc", m.colors)

    def test_generic_families_are_not_treated_as_brand_fonts(self):
        m = measure_html(
            "<style>body{font-family:'Space Grotesk',system-ui,sans-serif}</style>"
        )
        self.assertEqual(["Space Grotesk"], m.fonts)

    def test_font_faces_are_deduplicated(self):
        css = (
            "<style>"
            "@font-face{font-family:'Inter';src:url('/a.woff2') format('woff2')}"
            "@font-face{font-family:'Inter';src:url('/a.woff2') format('woff2')}"
            "</style>"
        )
        self.assertEqual(1, len(measure_html(css).faces))

    def test_measurement_is_a_pure_function_of_the_bytes(self):
        for name in SOURCE_NAMES:
            with self.subTest(source=name):
                text = source_text(name)
                self.assertEqual(
                    measure_html(text).to_dict(), measure_html(text).to_dict()
                )

    def test_colour_order_does_not_depend_on_dict_insertion(self):
        """Equal counts must break on the hex, so the order is reproducible."""
        m = measure_html("<style>.a{color:#ffffff}.b{color:#000000}</style>")
        self.assertEqual(["#000000", "#ffffff"], m.colors)

    def test_a_source_with_no_css_measures_empty_rather_than_guessing(self):
        m = measure_html("<h1>Just words</h1>")
        self.assertEqual([], m.colors)
        self.assertEqual(["Just words"], m.text["h1"])


if __name__ == "__main__":
    unittest.main()
