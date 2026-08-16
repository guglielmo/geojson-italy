"""Identity and validity for the historical series (issue #25).

Two questions, and the archive's whole design turns on the first:

**Which entity is this?** Not the ISTAT code: the Sardinian reform of 1 January
2026 changed all 377 Sardinian `com_istat_code` values with zero overlap,
because the municipal code embeds the province code. The archive keys on the
entity's **first cadastral (Belfiore) code**, which is assigned by the Agenzia
delle Entrate and republished by ISTAT, so it is public and checkable — unlike
an internal row id, which renumbers whenever its database is rebuilt.

Measured across the 26 published rosters, 2001 to 2026: 8,231 codes appear,
exactly one municipality ever changed its own — Lonato, `E667` until its
renaming to Lonato del Garda in 2007, `M312` after — and no code has ever been
held by two entities. The one interruption in the series is Baranzate's `A618`,
absent from the 2004 roster alone, which is a genuine extinction and
re-establishment rather than a reuse.

Hence `terr_key` is the **first** code and never changes, while
`com_catasto_code` stays a time-scoped attribute. For every municipality but
Lonato del Garda the two coincide at every date.

**When was this version valid?** Intervals are built from the publication
calendar, not read from a source: consecutive dates carrying an identical
version are one interval, and a date where the entity is absent closes it. A
municipality that comes back later gets a second interval and not a repaired
first one — the gap is a fact about the entity, and Baranzate is exactly why.

Nothing here is repaired silently. An identity link that contradicts another,
or a chain of renamings that loops, raises: which of the two readings is right
is not recoverable from the data, and choosing one fabricates a history.
"""

# Variation codes under which an entity can change its cadastral code while
# remaining the same entity: a renaming and a code renumbering. Extinctions and
# constitutions are excluded on purpose — there the two codes belong to two
# different entities, which is the opposite claim.
IDENTITY_EVENTS = {"CD", "RN"}


# How a municipality comes into existence, as the variation reports describe it.
# A constitution (`CS`) names the entities it came from; what those entities did
# on the same date says which kind it is, and the two kinds need different
# geometry.
EXTINCTION_EVENTS = {"ES", "AQES"}       # the predecessor ends: a merger
CESSION_EVENTS = {"CECS"}                # the predecessor survives: a detachment


class AmbiguousIdentity(ValueError):
    """Two irreconcilable readings of who an entity is.

    Raised rather than resolved by precedence. A wrong link here silently
    merges or splits an entity's history, and no consumer can see it.
    """


def _code(record, field):
    value = record.get(field)
    return str(value).strip() if value else None


def identity_links(records):
    """{superseded cadastral code: its successor}, for one and the same entity.

    Read from the variation reports: a `CD` or `RN` record whose two cadastral
    codes differ is the same municipality carrying a new code. In the series
    from 2001 there is exactly one, Lonato's.
    """
    links = {}
    for record in records:
        described = record.get("DESC_COD_VARIAZIONE") or record.get("COD_VARIAZIONE") or ""
        code = str(described).split("-", 1)[0].strip()
        if code not in IDENTITY_EVENTS:
            continue
        old, new = _code(record, "COD_CATASTO"), _code(record, "COD_CATASTO_REL")
        if not old or not new or old == new:
            continue
        if links.get(old, new) != new:
            raise AmbiguousIdentity(
                f"{old} is recorded as becoming both {links[old]} and {new}"
            )
        links[old] = new
    return links


def first_code(code, links):
    """Walk an entity's chain of cadastral codes back to the first one.

    That first code is `terr_key`. Walking backwards rather than forwards is
    what makes the key stable: a future renaming adds a link at the far end and
    leaves every already-published key untouched.
    """
    backwards = {}
    for old, new in links.items():
        if backwards.get(new, old) != old:
            raise AmbiguousIdentity(
                f"{new} is recorded as succeeding both {backwards[new]} and {old}"
            )
        backwards[new] = old

    seen = [code]
    current = code
    while current in backwards:
        current = backwards[current]
        if current in seen:
            raise AmbiguousIdentity(
                f"cadastral codes form a cycle: {' -> '.join(seen + [current])}"
            )
        seen.append(current)
    return current


def terr_key(code, links):
    """The archive's public key for the entity holding `code` at some date."""
    return first_code(code, links)


def _variation(record):
    described = record.get("DESC_COD_VARIAZIONE") or record.get("COD_VARIAZIONE") or ""
    return str(described).split("-", 1)[0].strip()


def creations(records):
    """How each municipality created since 1991 came into existence.

    Returns {cadastral code: [{"date", "kind", "predecessors"}, ...]}, in date
    order, with `kind` one of `merger` or `detachment`. A list rather than a
    single entry because a municipality can be constituted twice: Baranzate was
    created in 2001, extinguished in 2003 when the Constitutional Court struck
    down the regional law behind it, and created again in 2004. Keeping only one
    creation would date its second life from its first.

    The distinction between the two kinds is what decides a municipality's
    geometry before ISTAT first publishes one, and the reports state it rather
    than leaving it to be inferred:

        ES / AQES  the predecessor is extinguished — Castegnero and Nanto
                   become Castegnero Nanto, so the new boundary is their union
        CECS       the predecessor cedes territory and survives — Trapani cedes
                   Misiliscemi, so the new boundary cannot be derived from it

    A constitution whose predecessors do neither, or do both, raises. Guessing
    would put a fabricated boundary in a public archive under ISTAT's name,
    which is the one thing this design refuses everywhere.
    """
    constituted, behaviour = {}, {}
    for record in records:
        code = _variation(record)
        this, related = _code(record, "COD_CATASTO"), _code(record, "COD_CATASTO_REL")
        at = str(record.get("DATA_INIZIO_AMMINISTRATIVA") or "")[:10]
        if not this or not related:
            continue
        if code == "CS":
            predecessors = constituted.setdefault((this, at), [])
            if related not in predecessors:
                predecessors.append(related)
        elif code in EXTINCTION_EVENTS or code in CESSION_EVENTS:
            behaviour.setdefault((related, at), set()).add(
                "merger" if code in EXTINCTION_EVENTS else "detachment"
            )

    out = {}
    for (code, at), predecessors in sorted(constituted.items()):
        kinds = behaviour.get((code, at), set())
        if len(kinds) != 1:
            raise AmbiguousIdentity(
                f"{code} constituted {at} from {sorted(predecessors)}: "
                f"predecessors are recorded as "
                f"{sorted(kinds) or 'neither extinguished nor ceding'}"
            )
        out.setdefault(code, []).append({
            "date": at,
            "kind": kinds.pop(),
            "predecessors": sorted(predecessors),
        })
    return out


def creation_at(creations_by_code, code, at):
    """The most recent creation of `code` on or before `at`, if any."""
    candidates = [c for c in creations_by_code.get(code, []) if c["date"] <= at]
    return candidates[-1] if candidates else None


def intervals(calendar, versions):
    """Collapse a date-indexed series into validity intervals.

    `calendar` is the full publication calendar in order; `versions` maps the
    dates on which the entity exists to a comparable value — its properties and
    geometry. Consecutive dates with an equal value become one interval;
    `valid_to` is exclusive and null while the version is still current.

    Absence is not interpolated. An entity missing from a date ends its
    interval there, and its return opens a new one, which is how Baranzate's
    extinction and re-establishment survives the collapse.
    """
    out = []
    current = None
    for at in calendar:
        value = versions.get(at)
        if value is None:
            if current is not None:
                current["valid_to"] = at
                current = None
            continue
        if current is not None and current["version"] == value:
            continue
        if current is not None:
            current["valid_to"] = at
        current = {"valid_from": at, "valid_to": None, "version": value}
        out.append(current)
    return out
