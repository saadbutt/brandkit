"""A draft that invents a key is rejected, not quietly trimmed.

Dropping an unknown key hides the fact that the model misunderstood the
contract. Every test here asserts a refusal.
"""

from __future__ import annotations

import unittest

from brandkit.schema import SchemaError, validate_draft


class TestValidateDraft(unittest.TestCase):
    def test_non_object_draft_is_rejected(self):
        for bad in ("{}", 7, None, ["colors"]):
            with self.subTest(draft=bad):
                with self.assertRaises(SchemaError):
                    validate_draft(bad)

    def test_unknown_top_level_key_is_rejected(self):
        with self.assertRaisesRegex(SchemaError, "unknown top-level"):
            validate_draft({"colors": {}, "vibes": "warm"})

    def test_unknown_colour_role_is_rejected(self):
        with self.assertRaisesRegex(SchemaError, "colors: unknown key"):
            validate_draft({"colors": {"brand-accent-2": "#ff0000"}})

    def test_non_string_colour_is_rejected(self):
        with self.assertRaises(SchemaError):
            validate_draft({"colors": {"primary": 255}})

    def test_empty_colour_is_rejected(self):
        with self.assertRaises(SchemaError):
            validate_draft({"colors": {"primary": "   "}})

    def test_unknown_type_step_is_rejected(self):
        with self.assertRaisesRegex(SchemaError, "type_scale: unknown key"):
            validate_draft({"type_scale": {"gigantic": 96}})

    def test_non_numeric_size_is_rejected(self):
        with self.assertRaises(SchemaError):
            validate_draft({"type_scale": {"display": "48px"}})

    def test_boolean_is_not_accepted_as_a_size(self):
        """True == 1 in Python. A schema that forgets this accepts nonsense."""
        with self.assertRaises(SchemaError):
            validate_draft({"type_scale": {"display": True}})

    def test_non_positive_size_is_rejected(self):
        for bad in (0, -16):
            with self.subTest(size=bad):
                with self.assertRaises(SchemaError):
                    validate_draft({"type_scale": {"display": bad}})

    def test_unknown_copy_list_is_rejected(self):
        with self.assertRaisesRegex(SchemaError, "copy: unknown key"):
            validate_draft({"copy": {"taglines": ["hello"]}})

    def test_copy_must_be_strings(self):
        with self.assertRaises(SchemaError):
            validate_draft({"copy": {"h1": ["fine", 42]}})

    def test_unknown_font_key_is_rejected(self):
        with self.assertRaisesRegex(SchemaError, "fonts: unknown key"):
            validate_draft({"fonts": {"family": "Inter", "weight": 700}})

    def test_face_needs_family_and_src(self):
        with self.assertRaises(SchemaError):
            validate_draft({"fonts": {"faces": [{"family": "Inter"}]}})

    def test_valid_draft_is_normalised_not_mutated(self):
        draft = {"copy": {"h1": ["  spaced   out  "]}, "type_scale": {"body": 16}}
        out = validate_draft(draft)
        self.assertEqual(["spaced out"], out["copy"]["h1"])
        self.assertEqual(["  spaced   out  "], draft["copy"]["h1"])

    def test_every_known_section_is_present_after_validation(self):
        out = validate_draft({})
        for key in ("colors", "fonts", "type_scale", "radius", "elevation",
                    "spacing", "copy"):
            self.assertIn(key, out)

    def test_duplicate_spacing_values_collapse(self):
        out = validate_draft({"spacing": ["16px", "16px", "24px"]})
        self.assertEqual(["16px", "24px"], out["spacing"])


if __name__ == "__main__":
    unittest.main()
