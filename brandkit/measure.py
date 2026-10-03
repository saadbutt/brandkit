"""Observe: measure the source. These are facts, not opinions.

Everything here is derived from the bytes of the page. No model is consulted.
If a hex or a font family is not in this output, it is not in the brand, and
assemble_kit will refuse to let a draft invent one.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Tuple

_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_RGB = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*[\d.]+\s*)?\)")
# Quotes are kept in the capture and stripped per family below. Excluding them
# here silently dropped every quoted declaration, which is a quiet way to
# measure the wrong typeface.
_FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}]+)", re.I)
_FONT_SIZE = re.compile(r"font-size\s*:\s*([\d.]+)(px|rem|em)", re.I)
_RADIUS = re.compile(r"border-radius\s*:\s*([^;}]+)", re.I)
_SHADOW = re.compile(r"box-shadow\s*:\s*([^;}]+)", re.I)
_SPACING = re.compile(r"(?:margin|padding)[a-z-]*\s*:\s*([^;}]+)", re.I)
_FACE_SRC = re.compile(r"@font-face\s*{[^}]*?src\s*:\s*([^;}]+)", re.I | re.S)
_FACE_FAM = re.compile(r"@font-face\s*{[^}]*?font-family\s*:\s*([^;}]+)", re.I | re.S)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
_TAG_SELECTOR = re.compile(r"^[a-z][a-z0-9]*$")


@dataclass
class Metrics:
    """Measured facts about one source page."""

    colors: List[str] = field(default_factory=list)          # most used first
    color_counts: Dict[str, int] = field(default_factory=dict)
    fonts: List[str] = field(default_factory=list)           # families actually referenced
    faces: List[Dict[str, str]] = field(default_factory=list)  # {family, src}
    type_scale_px: List[float] = field(default_factory=list)  # descending
    sizes_by_tag: Dict[str, float] = field(default_factory=dict)  # h1/h2/p/... -> px
    radii: List[str] = field(default_factory=list)
    shadows: List[str] = field(default_factory=list)
    spacing: List[str] = field(default_factory=list)
    text: Dict[str, List[str]] = field(default_factory=dict)  # h1 / h2 / p / a / button

    def to_dict(self) -> Dict:
        return {
            "colors": self.colors,
            "color_counts": self.color_counts,
            "fonts": self.fonts,
            "faces": self.faces,
            "type_scale_px": self.type_scale_px,
            "sizes_by_tag": self.sizes_by_tag,
            "radii": self.radii,
            "shadows": self.shadows,
            "spacing": self.spacing,
            "text": self.text,
        }


class _Collector(HTMLParser):
    """Pulls inline style/CSS and the visible text we might reuse as copy."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.css_chunks: List[str] = []
        self.stylesheet_hrefs: List[str] = []
        self.text: Dict[str, List[str]] = {
            "h1": [], "h2": [], "p": [], "a": [], "button": [],
        }
        self._stack: List[str] = []
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "style":
            self._in_style = True
        if "style" in a and a["style"]:
            self.css_chunks.append("{" + a["style"] + "}")
        if tag == "link" and a.get("rel", "").lower() == "stylesheet" and a.get("href"):
            self.stylesheet_hrefs.append(a["href"])
        self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False
        while self._stack:
            if self._stack.pop() == tag:
                break

    def handle_data(self, data):
        if self._in_style:
            self.css_chunks.append(data)
            return
        chunk = " ".join(data.split())
        if not chunk or not self._stack:
            return
        tag = self._stack[-1]
        if tag in self.text and len(chunk) > 1:
            self.text[tag].append(chunk)


def _norm_hex(value: str) -> str:
    v = value.lower()
    if len(v) == 4:  # #abc -> #aabbcc
        v = "#" + "".join(ch * 2 for ch in v[1:])
    return v


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    clamp = lambda n: max(0, min(255, n))
    return "#{:02x}{:02x}{:02x}".format(clamp(r), clamp(g), clamp(b))


def _families(raw: str) -> List[str]:
    out = []
    for part in raw.split(","):
        name = part.strip().strip("'\"")
        if not name or name.lower() in {
            "inherit", "initial", "unset", "sans-serif", "serif", "monospace",
            "system-ui", "-apple-system", "cursive", "fantasy", "ui-sans-serif",
            "ui-serif", "ui-monospace", "blinkmacsystemfont",
        }:
            continue
        out.append(name)
    return out


def _to_px(value: float, unit: str) -> float:
    unit = unit.lower()
    if unit in ("rem", "em"):
        return round(value * 16.0, 2)
    return round(value, 2)


def measure_html(source: str) -> Metrics:
    """Measure one page. Deterministic: same bytes in, same Metrics out."""
    parser = _Collector()
    parser.feed(source)
    css = "\n".join(parser.css_chunks) + "\n" + source

    counts: Counter = Counter()
    for m in _HEX.finditer(css):
        counts[_norm_hex(m.group(0))] += 1
    for m in _RGB.finditer(css):
        counts[_rgb_to_hex(int(m.group(1)), int(m.group(2)), int(m.group(3)))] += 1

    # Ties break on the hex itself so ordering never depends on dict insertion.
    colors = [c for c, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    fams: List[str] = []
    for m in _FONT_FAMILY.finditer(css):
        for name in _families(m.group(1)):
            if name not in fams:
                fams.append(name)
    for href in parser.stylesheet_hrefs:
        for name in re.findall(r"family=([A-Za-z0-9+%20_-]+)", href):
            name = name.replace("+", " ").replace("%20", " ").split(":")[0]
            if name and name not in fams:
                fams.append(name)

    faces: List[Dict[str, str]] = []
    seen_faces = set()
    for fam, src in zip(_FACE_FAM.findall(css), _FACE_SRC.findall(css)):
        face = {
            "family": fam.strip().strip("'\""),
            "src": " ".join(src.split()),
        }
        key = (face["family"], face["src"])
        if key in seen_faces:
            continue
        seen_faces.add(key)
        faces.append(face)

    sizes = sorted({_to_px(float(v), u) for v, u in _FONT_SIZE.findall(css)}, reverse=True)
    radii = _uniq(" ".join(v.split()) for v in _RADIUS.findall(css))
    shadows = _uniq(" ".join(v.split()) for v in _SHADOW.findall(css))
    spacing = _uniq(" ".join(v.split()) for v in _SPACING.findall(css))

    return Metrics(
        colors=colors,
        color_counts=dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        fonts=fams,
        faces=faces,
        type_scale_px=sizes,
        sizes_by_tag=_sizes_by_tag(css),
        radii=radii,
        shadows=shadows,
        spacing=spacing,
        text={k: _uniq(v) for k, v in parser.text.items()},
    )


def _sizes_by_tag(css: str) -> Dict[str, float]:
    """font-size per bare tag selector, so a role can be anchored to real markup.

    This is what stops the type scale being assigned by position. A page whose
    p rule says 17px has a 17px body, whether or not 17px happens to be the
    fifth largest number in the stylesheet. Later rules win, as in CSS.
    """
    out: Dict[str, float] = {}
    for selector_group, body in _RULE.findall(css):
        match = _FONT_SIZE.search(body)
        if not match:
            continue
        px = _to_px(float(match.group(1)), match.group(2))
        for part in selector_group.split(","):
            tag = part.strip().lower()
            if _TAG_SELECTOR.match(tag):
                out[tag] = px
    return out


def _uniq(values) -> List[str]:
    out: List[str] = []
    for v in values:
        v = v.strip()
        if v and v not in out:
            out.append(v)
    return out
