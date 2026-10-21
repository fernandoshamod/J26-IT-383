"""Repair Windows-1252 mojibake introduced while rewriting two JSX files."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
replacements = {
    "\u00c2\u00b7": "\u00b7",
    "\u00e2\u20ac\u201c": "\u2013",
    "\u00e2\u20ac\u201d": "\u2014",
    "\u00e2\u20ac\u00a6": "\u2026",
    "\u00e2\u20ac\u2122": "\u2019",
}
for name in ("frontend/src/pages/EventWizard.jsx", "frontend/src/pages/PackageViews.jsx"):
    path = root / name
    value = path.read_text(encoding="utf-8")
    counts = {key.encode("unicode_escape").decode(): value.count(key) for key in replacements}
    for old, new in replacements.items():
        value = value.replace(old, new)
    path.write_text(value, encoding="utf-8")
    print(name, counts)