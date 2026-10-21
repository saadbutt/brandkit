"""Bind a kit onto a skeleton.

The tree is read from TREE.md and checked against the registry before anything
is written. Band order and repeats stay exactly as the skeleton declares them:
the binder paints theme and copy, it never moves or invents a band.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from .registry import Registry, RegistryError

_TREE_LINE = re.compile(r"^\s*(?:[-*]\s*)?([a-z0-9]+(?:-[a-z0-9]+)*)\s*(?:x\s*(\d+))?\s*$")
_ROOT_BLOCK = re.compile(
    r"<style\s+data-brandkit=\"kit\"\s*>.*?</style>\s*", re.DOTALL | re.IGNORECASE
)


class BindError(ValueError):
    """Raised when a skeleton and the registry disagree."""


def parse_tree(text: str) -> list[str]:
    """Read TREE.md into an ordered block list, expanding `id x3` repeats."""
    tree: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("|"):
            continue
        match = _TREE_LINE.match(line)
        if not match:
            continue
        block_id, count = match.group(1), match.group(2)
        tree.extend([block_id] * (int(count) if count else 1))
    if not tree:
        raise BindError("TREE.md listed no blocks")
    return tree


class _BlockAudit(HTMLParser):
    """Collect the data-block ids and data-slot names the skeleton actually uses."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.slots: list[tuple[str, str]] = []
        self._current: str = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-block" in a:
            self._current = a["data-block"]
            self.blocks.append(self._current)
        if "data-slot" in a:
            self.slots.append((self._current, a["data-slot"]))


def audit_skeleton(html: str) -> tuple[list[str], list[tuple[str, str]]]:
    parser = _BlockAudit()
    parser.feed(html)
    return parser.blocks, parser.slots


def check(html: str, tree: list[str], registry: Registry) -> None:
    """Fail loudly when the skeleton, the tree and the registry disagree.

    An unknown id on a new skeleton is a registry gap: register it, then bind.
    An id in the markup that the tree never declared is drift, and is rejected.
    """
    try:
        registry.validate_tree(tree)
    except RegistryError as exc:
        raise BindError(str(exc)) from None

    blocks, slots = audit_skeleton(html)
    unknown = [b for b in blocks if not registry.has(b)]
    if unknown:
        raise BindError(f"skeleton uses unregistered block id(s): {sorted(set(unknown))}")
    if blocks != tree:
        raise BindError(
            f"skeleton band order does not match TREE.md\n  tree: {tree}\n  html: {blocks}"
        )
    for block_id, slot in slots:
        block = registry.get(block_id)
        if slot not in block.slots:
            raise BindError(f"{block_id}: slot {slot!r} is not in the registry entry")


def bind(html: str, kit: dict[str, Any], tree: list[str], registry: Registry,
         css: str) -> str:
    """Return the skeleton restyled by the kit. Layout stays, theme and copy change."""
    check(html, tree, registry)

    out = _ROOT_BLOCK.sub("", html)
    style = f'<style data-brandkit="kit">\n{css}</style>\n'
    if "</head>" in out:
        out = out.replace("</head>", style + "</head>", 1)
    else:
        out = style + out

    counters: dict[str, int] = {}
    return _fill_slots(out, kit, counters)


_SLOT_TAG = re.compile(
    r'(<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*?data-slot="(?P<slot>[a-z0-9]+)"[^>]*)>)'
    r'(?P<body>.*?)'
    r'(</(?P=tag)>)',
    re.DOTALL,
)


def _fill_slots(html: str, kit: dict[str, Any], counters: dict[str, int]) -> str:
    copy = kit["copy"]

    def replace(match: re.Match[str]) -> str:
        slot = match.group("slot")
        values = copy.get(slot, [])
        if not values:
            return match.group(0)  # empty slots are fine, leave the skeleton text
        index = counters.get(slot, 0)
        counters[slot] = index + 1
        value = values[index % len(values)]
        return match.group(1) + _escape(value) + match.group(6)

    return _SLOT_TAG.sub(replace, html)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
