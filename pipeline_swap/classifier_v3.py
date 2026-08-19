"""Classifier v3 — sentinel-led abstention. Versioned beside v1 and v2; neither is modified.

Ruled 5 August after full review of the 41 shortlisted replies: all 41 are REFUSALS. The uniform
pattern is a sentinel-led abstention followed by explanatory prose, and no entry asserts
extra-contextual content.

    v1   answer.strip() == "NOT FOUND"
    v2   v1 plus trailing punctuation
    v3   after stripping LEADING whitespace, the reply BEGINS with the sentinel (optional
         trailing punctuation), regardless of what follows

v3 ⊇ v2 ⊇ v1 by construction, and the tests assert that containment rather than trusting it.

**The one thing v3 still refuses to do is guess.** The sentinel must lead. An embedded sentinel
(`The answer is NOT FOUND in the context`) stays an ANSWER, because a reply that merely mentions
the token has not opened with it, and widening to substring search would make the classifier
decide what counts as an abstention rather than recognising the declared form. Case is still not
folded, for the same reason it was not folded in v2.

`NOT FOUNDATION` is not a sentinel: a word boundary is required after the token.

**Boundary case, logged as ruled.** The `A-026` entry — sentinel followed by a quoted default
value — classifies REFUSAL by rule. It is recorded in `boundary_cases.json` as a case decided by
the rule rather than by its own merits, so a future reader can find it without re-deriving it.
"""
from __future__ import annotations

import re

from pipeline_swap.classifier_v2 import is_not_found_v2               # identity, not re-derived
from src.v17.reading import NOT_FOUND, is_not_found as is_not_found_v1

VERSION = "classifier-v3"

#: Sentinel at the start, optional trailing punctuation, then a boundary (or end of string).
_LEADS_WITH_SENTINEL = re.compile(
    r"^" + re.escape(NOT_FOUND) + r"[.!;:,]*(?![A-Za-z0-9])")


def is_not_found_v3(answer: str) -> bool:
    """True iff the reply leads with the declared sentinel."""
    return bool(_LEADS_WITH_SENTINEL.match(answer.lstrip()))


def verdict(answer: str, version: str = "v3") -> str:
    fn = {"v1": is_not_found_v1, "v2": is_not_found_v2, "v3": is_not_found_v3}[version]
    return "REFUSAL" if fn(answer) else "ANSWER"


def residue(answer: str) -> str:
    """What follows the leading sentinel, for inspection. Empty when the reply is bare."""
    s = answer.lstrip()
    m = _LEADS_WITH_SENTINEL.match(s)
    return s[m.end():].strip() if m else ""


def new_under_v3(answer: str) -> bool:
    """Does v3 call this a refusal where v2 did not?"""
    return is_not_found_v3(answer) and not is_not_found_v2(answer)
