"""The block registry is the contract.

A skeleton's TREE.md may only name ids that live here. A genuinely new block
gets one entry. An id invented on a locked skeleton is rejected rather than
accommodated, because silently accepting it is how a "locked" layout drifts.

Nothing in this module knows about any particular skeleton. Adding a 9th page
means adding entries here, not forking a template or touching assemble_kit.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

Geometry = str  # "band" | "row" | "stack" | "split" | "grid" | "card"

REPEAT_ONCE = "once"
REPEAT_MANY = "many"
_REPEAT_RULES = (REPEAT_ONCE, REPEAT_MANY)


class RegistryError(ValueError):
    """Raised when a block definition or a tree violates the registry."""


@dataclass(frozen=True)
class Block:
    """One registered block.

    required: slots that must receive copy for the block to bind.
    optional: slots that may receive copy. Empty is fine.
    repeat:   whether a tree may list this id more than once.
    """

    id: str
    geometry: Geometry
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    repeat: str = REPEAT_ONCE

    def __post_init__(self) -> None:
        if not _is_kebab(self.id):
            raise RegistryError(f"block id must be kebab-case: {self.id!r}")
        if self.repeat not in _REPEAT_RULES:
            raise RegistryError(
                f"{self.id}: repeat must be one of {_REPEAT_RULES}, got {self.repeat!r}"
            )
        overlap = set(self.required) & set(self.optional)
        if overlap:
            raise RegistryError(
                f"{self.id}: slot(s) both required and optional: {sorted(overlap)}"
            )

    @property
    def slots(self) -> tuple[str, ...]:
        return tuple(self.required) + tuple(self.optional)


def _is_kebab(value: str) -> bool:
    if not value or value != value.lower():
        return False
    if value[0] == "-" or value[-1] == "-":
        return False
    return all(ch.isalnum() or ch == "-" for ch in value) and "--" not in value


class Registry:
    """Central, ordered collection of blocks."""

    def __init__(self, blocks: Iterable[Block] = ()) -> None:
        self._blocks: dict[str, Block] = {}
        for block in blocks:
            self.register(block)

    def register(self, block: Block) -> None:
        if block.id in self._blocks:
            raise RegistryError(f"duplicate block id: {block.id}")
        self._blocks[block.id] = block

    def get(self, block_id: str) -> Block:
        try:
            return self._blocks[block_id]
        except KeyError:
            raise RegistryError(f"unknown block id: {block_id}") from None

    def has(self, block_id: str) -> bool:
        return block_id in self._blocks

    def ids(self) -> list[str]:
        return list(self._blocks)

    def __len__(self) -> int:
        return len(self._blocks)

    def validate_tree(self, tree: list[str]) -> None:
        """Reject a tree that names an unregistered id or over-repeats a block."""
        seen: dict[str, int] = {}
        for block_id in tree:
            block = self.get(block_id)  # raises on unknown
            seen[block_id] = seen.get(block_id, 0) + 1
            if block.repeat == REPEAT_ONCE and seen[block_id] > 1:
                raise RegistryError(
                    f"{block_id}: repeat rule is {REPEAT_ONCE}, appears {seen[block_id]} times"
                )

    def slot_map(self, tree: list[str]) -> dict[str, tuple[str, ...]]:
        """Slots each block in this tree can accept. Drives the DESIGN.md slot map."""
        self.validate_tree(tree)
        return {block_id: self.get(block_id).slots for block_id in dict.fromkeys(tree)}


def default_registry() -> Registry:
    """Seeded with the blocks the starter skeletons already use."""
    return Registry(_SEED)


_SEED: tuple[Block, ...] = (
    Block("promo-bar", "band", ("helpers",), repeat=REPEAT_ONCE),
    Block("nav-bar", "band", ("wordmark",), ("links", "ctas"), REPEAT_ONCE),
    Block("hero-stack", "stack", ("h1",), ("leads", "ctas", "helpers"), REPEAT_ONCE),
    Block("hero-split", "split", ("h1",), ("leads", "ctas", "helpers"), REPEAT_ONCE),
    Block("product-split", "split", ("h2s",), ("bodies", "ctas"), REPEAT_MANY),
    Block("media-bleed", "band", (), ("h2s", "bodies"), REPEAT_MANY),
    Block("media-pair", "row", (), ("h2s", "bodies"), REPEAT_MANY),
    Block("stat-band", "band", ("h2s",), ("bodies",), REPEAT_ONCE),
    Block("stat-row", "row", (), ("bodies", "helpers"), REPEAT_MANY),
    Block("icon-row", "row", (), ("h2s", "bodies"), REPEAT_MANY),
    Block("steps-row", "row", ("h2s",), ("bodies",), REPEAT_MANY),
    Block("steps-split", "split", ("h2s",), ("bodies",), REPEAT_MANY),
    Block("split-row", "row", (), ("h2s", "bodies", "ctas"), REPEAT_MANY),
    Block("split-stack", "stack", (), ("h2s", "bodies", "ctas"), REPEAT_MANY),
    Block("card-row", "row", (), ("h2s", "bodies", "ctas"), REPEAT_MANY),
    Block("product-grid", "grid", (), ("h2s", "bodies"), REPEAT_MANY),
    Block("product-row", "row", (), ("h2s", "bodies"), REPEAT_MANY),
    Block("copy-stack", "stack", (), ("h2s", "bodies"), REPEAT_MANY),
    Block("stack-media", "stack", (), ("h2s", "bodies"), REPEAT_MANY),
    Block("logo-row", "row", (), ("helpers",), REPEAT_MANY),
    Block("chip-row", "row", (), ("helpers",), REPEAT_MANY),
    Block("quote-row", "row", (), ("bodies", "helpers"), REPEAT_MANY),
    Block("faq-stack", "stack", ("h2s",), ("bodies",), REPEAT_ONCE),
    Block("cta-band", "band", ("ctas",), ("h2s", "bodies"), REPEAT_MANY),
    Block("cta-row", "row", ("ctas",), ("bodies",), REPEAT_MANY),
    Block("form-card", "card", ("fields",), ("h2s", "ctas", "helpers"), REPEAT_MANY),
    Block("form-split", "split", ("fields",), ("h2s", "ctas", "helpers"), REPEAT_MANY),
    Block("form-row", "row", ("fields",), ("ctas", "helpers"), REPEAT_MANY),
    Block("tab-split", "split", (), ("h2s", "bodies"), REPEAT_MANY),
    Block("footer-directory", "band", (), ("links", "helpers"), REPEAT_ONCE),
    Block("footer-legal", "band", (), ("helpers", "crumbs"), REPEAT_ONCE),
    Block("footnote-band", "band", (), ("helpers",), REPEAT_ONCE),
)
