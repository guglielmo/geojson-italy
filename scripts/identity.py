"""Identity rules for the historical series (issue #25).

The identity source is a date-framed territorial reconstruction, maintained
outside this repository, that records which entity is which across mergers,
recodings and reassignments. It supplies what no shapefile can; geometry comes
from the ISTAT editions instead (D9, #24).

This module holds the rules that decide what reaches a public archive. They are
pure functions, testable without a database — the extraction that feeds them
lives in `extract_identity.py` and needs credentials.

**The key is public.** Entities are keyed on their first cadastral (Belfiore)
code, not on the source's internal row id. That id is a database sequence
assigned at import: it renumbers whenever the source is rebuilt, and no third
party can verify it, so an archive keyed on it would not be checkable. The
cadastral code is assigned by the Agenzia delle Entrate and republished in
ISTAT's `Elenco-comuni-italiani`. Measured across the source: 8,229 of 8,230
municipalities hold exactly one for their whole life and no code has ever been
reused; Lonato del Garda alone holds two (`E667` until 2008, `M312` after),
which is why the key is the *first* one.

**Bad source data fails loudly.** The source holds intervals whose `valid_to`
precedes `valid_from`. Sorting the two dates into order would invent a validity
period that was never published, so a reversed interval raises instead.
"""

from datetime import date

# Sorts before every real date, so a null valid_from reads as "since before
# records began" — which is how the source uses it.
_EARLIEST = date.min


class ReversedInterval(ValueError):
    """An interval whose end precedes its start.

    Raised rather than repaired: which of the two dates is wrong is not
    recoverable from the data, and choosing one fabricates a validity period.
    """


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _sort_key(row):
    frm = _as_date(row.get("valid_from"))
    return (frm or _EARLIEST, str(row.get("identifier") or ""))


def is_reversed(row):
    """True when the row's interval ends before it starts."""
    frm = _as_date(row.get("valid_from"))
    to = _as_date(row.get("valid_to"))
    return frm is not None and to is not None and to < frm


def reversed_intervals(rows):
    """Every row whose interval is reversed. Reported, never silently fixed."""
    return [r for r in rows if is_reversed(r)]


def sort_by_validity(rows, strict=False):
    """Order rows by validity start, then identifier.

    Deterministic on purpose: the extraction is a tracked artefact, and an
    unstable order would churn the diff on every run. With strict=True a
    reversed interval raises instead of being ordered.
    """
    if strict:
        for row in rows:
            if is_reversed(row):
                raise ReversedInterval(
                    f"{row.get('identifier')}: valid_to {row.get('valid_to')} "
                    f"precedes valid_from {row.get('valid_from')}"
                )
    return sorted(rows, key=_sort_key)


def first_cadastral_code(rows):
    """The entity's first cadastral code — its stable public key.

    Returns None when the entity has none, which in the current data means a
    stray record or a municipality extinguished before the series begins.
    """
    if not rows:
        return None
    return sort_by_validity(rows)[0]["identifier"]


def is_publishable(entity):
    """Whether an entity belongs in the archive at all.

    An entity carrying no identifier of any scheme is not a municipality anyone
    can refer to. In the current data this drops exactly two rows, both stray
    records, and nothing else.
    """
    return bool(entity.get("identifiers"))
