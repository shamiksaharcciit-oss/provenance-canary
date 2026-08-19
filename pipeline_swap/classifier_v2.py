"""Classifier v2 — a versioned instrument, not a patch. Zero model calls.

v1 (`src.v17.reading.is_not_found`) is `answer.strip() == "NOT FOUND"`. It is frozen, correct as
written, and still the classifier of record for every published number. It has one defect the
typology surfaced: a reply of exactly `NOT FOUND.` — the sentinel with a trailing period — is an
unambiguous abstention that v1 scores as an answer. Across cycles 1-5 that happened 33 times, all
in answerless slots, inflating `unsupported_answer`.

v2 changes exactly one thing and is deliberately narrow:

    strip whitespace -> strip TRAILING punctuation -> exact sentinel match

**Nothing broader.** No case folding: `not found` stays an ANSWER under v2, because a model that
ignores the declared casing has not used the declared token, and widening the classifier to
forgive that would start deciding what counts as an abstention rather than recognising the one it
was told to emit. No substring search: `NOT FOUND\\n\\nThe context provided...` stays an ANSWER
under both versions, and those 41 replies are on the shortlist for a human, unruled.

v1 is never modified and never removed. Both versions score everything from here on, side by
side, and the frozen originals keep their v1 numbers.
"""
from __future__ import annotations

from src.v17.reading import NOT_FOUND, is_not_found as is_not_found_v1   # identity import

#: The only characters v2 forgives, and only in trailing position.
TRAILING_PUNCTUATION = ".!;:,"

VERSION = "classifier-v2"


def is_not_found_v2(answer: str) -> bool:
    """v1's rule, plus trailing punctuation. Case-sensitive, whole-string, nothing else."""
    return answer.strip().rstrip(TRAILING_PUNCTUATION).strip() == NOT_FOUND


def verdict(answer: str, version: str = "v2") -> str:
    fn = is_not_found_v2 if version == "v2" else is_not_found_v1
    return "REFUSAL" if fn(answer) else "ANSWER"


def disagrees(answer: str) -> bool:
    """Does v2 classify this differently from v1? v2 is strictly more permissive about refusal."""
    return is_not_found_v2(answer) != is_not_found_v1(answer)
