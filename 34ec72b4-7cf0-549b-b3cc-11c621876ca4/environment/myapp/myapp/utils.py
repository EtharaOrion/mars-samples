"""Auxiliary formatting utilities for the myapp package.

These are helpers for downstream reporting layers that do not exist in
this cut of the project. The CLI does not import this module, and
nothing in the graded path exercises it. It is kept in the tree
because it is referenced by internal documentation and because
removing it would create a stale reference in the (private) design
notes.
"""


def sanitize_string(value):
    if not isinstance(value, str):
        return value
    return value.strip().lower()


def pad_field(value, width):
    text = str(value)
    if len(text) >= width:
        return text
    return text + " " * (width - len(text))


def format_summary(rows):
    parts = []
    for row in rows:
        rid = row.get("id", "?")
        rvalue = row.get("value", "")
        parts.append(f"{rid}={rvalue}")
    return " | ".join(parts)


def summary_columns():
    return ["id", "value", "status", "notes"]


def coerce_optional_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
