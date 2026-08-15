"""Reading the ISTAT roster at a date (issue #25).

SITUAS report 61 answers with the municipalities valid on a given date. This
module turns one such answer into the attribute layer of the archive, using the
property names this repository already publishes so that a historical feature
and a current one are the same shape.

Three things in the payload are not stable across the series, and each is a way
to write a reader that works on 2026 and silently misreads 2001:

- **`PRO_COM_T` arrives as a string or as a number.** `"001001"` keeps its
  leading zeros, `103025` does not. Compared without padding, a fifth of the
  roster fails to match the geometry and the failure looks like missing
  municipalities.
- **The NUTS columns carry their vintage in the name** — `COM_NUTS3_2006`,
  `_2010`, `_2021`, `_2024` — so they are matched by prefix. They are absent
  before 2006 entirely.
- **`COD_PROV_STORICO` appears only in later rosters.** The province code is
  therefore taken from the first three characters of `PRO_COM_T`, which is what
  this repository has always published and is available at every date.

`TIPO_UTS` is numeric here and textual in the boundary editions. The two agree
exactly on the 2026 counts — 83 provinces, 15 metropolitan cities, 6 liberi
consorzi, 4 non-administrative units, 2 autonomous provinces — which is what
pins the mapping below without guessing.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROSTERS = ROOT / "build" / "situas" / "rosters"

# Numeric TIPO_UTS as published in the roster, against the textual form the
# boundary editions use. Verified by counting both for 2026: the five values
# partition the 110 units identically.
TIPO_UTS_LABELS = {
    1: "Provincia",
    2: "Provincia autonoma",
    3: "Città metropolitana",
    4: "Libero consorzio di comuni",
    5: "Unità non amministrativa",
}


class UnknownUtsType(ValueError):
    """A TIPO_UTS outside the five ISTAT publishes.

    Raised rather than passed through: the value reaches consumers as
    `prov_tipo_uts`, and a code nobody has a label for is worse than a failure
    during the build.
    """


def istat_code(value):
    """Normalise a municipality code to its six-character form."""
    return str(value).strip().zfill(6)


def _nuts(record, level):
    for key, value in record.items():
        if key.startswith(f"COM_NUTS{level}_"):
            return value
    return None


def _uts_label(value):
    if value in (None, ""):
        return None
    try:
        return TIPO_UTS_LABELS[int(value)]
    except (KeyError, ValueError):
        raise UnknownUtsType(
            f"TIPO_UTS {value!r} is not one of {sorted(TIPO_UTS_LABELS)}"
        ) from None


def attributes(record):
    """One roster record, as the properties this repository publishes.

    `op_id`, `opdm_id` and the two `minint_*` identifiers are absent by
    construction: ISTAT holds none of them. They are backfilled on the cadastral
    code for municipalities that still exist (#31).
    """
    code = istat_code(record["PRO_COM_T"])
    prov = code[:3]
    reg = str(record["COD_REG"]).strip().zfill(2)
    return {
        "name": record.get("COMUNE_IT") or record.get("COMUNE"),
        "com_istat_code": code,
        "com_istat_code_num": int(code),
        "com_catasto_code": record.get("COD_CATASTO"),
        "prov_istat_code": prov,
        "prov_istat_code_num": int(prov),
        "prov_name": record.get("DEN_UTS"),
        "prov_acr": record.get("SIGLA_AUTOMOBILISTICA"),
        "prov_uts_code": str(record["COD_UTS"]).strip().zfill(3),
        "prov_tipo_uts": _uts_label(record.get("TIPO_UTS")),
        "reg_istat_code": reg,
        "reg_istat_code_num": int(reg),
        "reg_name": record.get("DEN_REG"),
        "com_nuts3": _nuts(record, 3),
    }


def read_roster(at, root=ROSTERS):
    """The roster valid at a date, keyed by ISTAT code.

    The key is the ISTAT code because that is what joins to the geometry. The
    archive's own key is the cadastral code, assigned later by
    `scripts.identity`, once an entity's whole series is in hand.
    """
    path = Path(root) / f"{at}.json"
    payload = json.loads(path.read_text())
    records = payload["resultset"] if isinstance(payload, dict) else payload
    out = {}
    for record in records:
        attrs = attributes(record)
        code = attrs["com_istat_code"]
        if code in out:
            raise ValueError(f"{at}: ISTAT code {code} appears twice in the roster")
        out[code] = attrs
    return out


def available(root=ROSTERS):
    """The dates whose roster is already cached."""
    root = Path(root)
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.json"))
