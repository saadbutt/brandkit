"""The registry is the contract. These tests are about what it refuses."""

from __future__ import annotations

import unittest

from brandkit.registry import (
    REPEAT_MANY,
    REPEAT_ONCE,
    Block,
    Registry,
    RegistryError,
    default_registry,
)


class TestBlock(unittest.TestCase):
    def test_id_must_be_kebab_case(self):
        for bad in ("HeroStack", "hero_stack", "-hero", "hero-", "hero--stack", ""):
            with self.subTest(block_id=bad):
                with self.assertRaises(RegistryError):
                    Block(bad, "band")

    def test_unknown_repeat_rule_is_rejected(self):
        with self.assertRaises(RegistryError):
            Block("hero-stack", "stack", repeat="sometimes")

    def test_a_slot_cannot_be_both_required_and_optional(self):
        with self.assertRaises(RegistryError):
            Block("hero-stack", "stack", ("h1",), ("h1",))

    def test_slots_are_required_then_optional(self):
        block = Block("hero-stack", "stack", ("h1",), ("leads", "ctas"))
        self.assertEqual(("h1", "leads", "ctas"), block.slots)


class TestRegistry(unittest.TestCase):
    def test_duplicate_registration_is_rejected(self):
        reg = Registry([Block("hero-stack", "stack")])
        with self.assertRaises(RegistryError):
            reg.register(Block("hero-stack", "split"))

    def test_unknown_id_raises_rather_than_returning_none(self):
        with self.assertRaises(RegistryError):
            Registry().get("hero-stack")

    def test_tree_with_an_unregistered_id_is_rejected(self):
        reg = default_registry()
        with self.assertRaises(RegistryError):
            reg.validate_tree(["nav-bar", "pricing-waterfall"])

    def test_once_block_cannot_repeat(self):
        reg = default_registry()
        with self.assertRaises(RegistryError):
            reg.validate_tree(["nav-bar", "nav-bar"])

    def test_many_block_may_repeat(self):
        reg = default_registry()
        reg.validate_tree(["card-row", "card-row", "card-row"])

    def test_slot_map_collapses_repeats_and_keeps_tree_order(self):
        reg = default_registry()
        tree = ["nav-bar", "card-row", "card-row", "faq-stack"]
        self.assertEqual(
            ["nav-bar", "card-row", "faq-stack"], list(reg.slot_map(tree))
        )

    def test_seeded_registry_covers_every_block_the_skeletons_use(self):
        from tests.support import skeletons

        reg = default_registry()
        for name, _html, tree in skeletons():
            with self.subTest(skeleton=name):
                reg.validate_tree(tree)

    def test_registering_a_new_block_does_not_disturb_the_existing_ids(self):
        reg = default_registry()
        before = reg.ids()
        reg.register(Block("pricing-ladder", "grid", ("h2s",), ("bodies",), REPEAT_MANY))
        self.assertEqual(before, reg.ids()[: len(before)])
        self.assertEqual(REPEAT_MANY, reg.get("pricing-ladder").repeat)
        self.assertEqual(REPEAT_ONCE, reg.get("nav-bar").repeat)


if __name__ == "__main__":
    unittest.main()
