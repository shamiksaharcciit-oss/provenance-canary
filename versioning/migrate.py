"""Span migrator (build spec §1.2). Deterministic, no model call.

Character-level diff between a document's v1 and v2; every registered span maps to exactly one
outcome.

    UNCHANGED  the span lies entirely inside an `equal` region — migrated coordinates are the
               original shifted by that region's offset, which IS the net delta of preceding
               edits.
    MOVED      not covered by an equal region in place, but the exact byte sequence exists
               intact at one determinable location.
    DISTURBED  neither. Never migrated, no coordinates emitted, the intersecting edit named.

**The binding invariant.** For every UNCHANGED and MOVED span, the text at the migrated
coordinates in v2 must be byte-identical to the text at the original coordinates in v1. Migration
is verified, not trusted, and a single failure is a STOP rather than a statistic —
`MigrationNotVerified` carries the span and both texts.

**The ambiguity rule.** If a MOVED candidate's byte sequence occurs more than once in v2, the
outcome is DISTURBED with cause `ambiguous_relocation`. The migrator never guesses among
candidates; a span that could be in two places is not a migrated span.
"""
from __future__ import annotations

from difflib import SequenceMatcher

UNCHANGED, MOVED, DISTURBED = "UNCHANGED", "MOVED", "DISTURBED"


class MigrationNotVerified(AssertionError):
    """A migrated span's v2 text is not byte-identical to its v1 text. STOP."""


def opcodes(v1: str, v2: str):
    """Deterministic opcodes. `autojunk` off: on long documents its heuristic drops popular
    lines and would make the diff depend on document length rather than on the edit."""
    return SequenceMatcher(a=v1, b=v2, autojunk=False).get_opcodes()


def migrate_span(v1: str, v2: str, ops, s: int, t: int) -> dict:
    """Map one span. Returns its outcome record; asserts the invariant when it migrates."""
    original = v1[s:t]

    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal" and i1 <= s and t <= i2:
            ns, nt = j1 + (s - i1), j1 + (t - i1)
            if v2[ns:nt] != original:
                raise MigrationNotVerified(
                    f"UNCHANGED span [{s},{t}) -> [{ns},{nt}) is not byte-identical: "
                    f"{original[:60]!r} != {v2[ns:nt][:60]!r}")
            return {"outcome": UNCHANGED, "new_start": ns, "new_end": nt, "delta": ns - s,
                    "verified": True}

    hits = []
    idx = v2.find(original)
    while idx != -1:
        hits.append(idx)
        if len(hits) > 1:
            break
        idx = v2.find(original, idx + 1)

    if len(hits) == 1:
        ns, nt = hits[0], hits[0] + len(original)
        if v2[ns:nt] != original:
            raise MigrationNotVerified(f"MOVED span [{s},{t}) failed byte identity")
        return {"outcome": MOVED, "new_start": ns, "new_end": nt, "delta": ns - s,
                "verified": True}
    if len(hits) > 1:
        return {"outcome": DISTURBED, "new_start": None, "new_end": None, "delta": None,
                "cause": "ambiguous_relocation", "verified": False}

    cause = "edit_intersects_span"
    for tag, i1, i2, j1, j2 in ops:
        if tag != "equal" and not (i2 <= s or i1 >= t):
            cause = f"{tag} at v1[{i1},{i2})"
            break
    return {"outcome": DISTURBED, "new_start": None, "new_end": None, "delta": None,
            "cause": cause, "verified": False}


def migrate_document(v1: str, v2: str, spans: list[tuple[int, int]]) -> list[dict]:
    ops = opcodes(v1, v2)
    return [{"orig_start": s, "orig_end": t, **migrate_span(v1, v2, ops, s, t)}
            for (s, t) in spans]
