"""Build comuni.geojson from the ISTAT sources plus the previous release.

The join key between releases is the cadastral (Belfiore) code, never the ISTAT
code: the Sardinian reform of 1 January 2026 changed all 377 Sardinian ISTAT
codes with no overlap, and municipality names both collide and change.
"""

import json
from pathlib import Path

import openpyxl

# Headings in Elenco-comuni-italiani.xlsx. The columns are located by heading
# rather than by position: ISTAT reorders this spreadsheet between editions, and
# a hardcoded index would keep reading, silently joining the wrong column.
_HEADER_ISTAT = "Codice Comune formato alfanumerico"
_HEADER_CATASTO = "Codice Catastale del Comune"


def _resolve_columns(header):
    """Return (istat index, catasto index), located by column heading."""
    positions = {}
    for index, cell in enumerate(header):
        if cell is None:
            continue
        # Headings carry stray newlines and double spaces between editions.
        label = " ".join(str(cell).split())
        if label in (_HEADER_ISTAT, _HEADER_CATASTO):
            positions[label] = index
    missing = [h for h in (_HEADER_ISTAT, _HEADER_CATASTO) if h not in positions]
    if missing:
        raise ValueError(f"column headings not found in the spreadsheet: {missing}")
    return positions[_HEADER_ISTAT], positions[_HEADER_CATASTO]


def read_catasto_codes(path):
    """Return {istat_code: catasto_code} from the ISTAT spreadsheet."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = wb[wb.sheetnames[0]].iter_rows(values_only=True)
    col_istat, col_catasto = _resolve_columns(next(rows))
    out = {}
    for row in rows:
        istat = row[col_istat]
        catasto = row[col_catasto]
        if istat and catasto:
            out[str(istat).strip()] = str(catasto).strip()
    return out


def build_properties(comune, uts_by_code, region_names, catasto):
    """Assemble the published property set for one municipality.

    Codes are carried both zero-padded as text and as integers, matching the
    schema this repository has always published. The key order reproduces the
    published file's, legacy fields included as None placeholders so that
    merge_legacy fills them in place rather than appending them.
    """
    prov_code = int(comune["COD_PROV"])
    reg_code = int(comune["COD_REG"])
    istat = str(comune["PRO_COM_T"]).strip()
    uts = uts_by_code[prov_code]

    return {
        "name": comune["COMUNE"],
        "op_id": None,
        "minint_elettorale": None,
        "minint_finloc": None,
        "prov_name": uts["DEN_UTS"],
        "prov_istat_code": f"{prov_code:03d}",
        "prov_istat_code_num": prov_code,
        "prov_acr": uts["SIGLA"],
        "reg_name": region_names[reg_code],
        "reg_istat_code": f"{reg_code:02d}",
        "reg_istat_code_num": reg_code,
        "opdm_id": None,
        "com_catasto_code": catasto,
        "com_istat_code": istat,
        "com_istat_code_num": int(istat),
    }


# Identifiers that exist only in previous releases of this repository. They are
# not published by ISTAT and cannot be derived, so they are carried across.
LEGACY_FIELDS = ("op_id", "opdm_id", "minint_elettorale", "minint_finloc")


def read_legacy_by_catasto(path):
    """Return {catasto_code: {legacy field: value}} from a previous release."""
    features = json.loads(Path(path).read_text())["features"]
    out = {}
    for feature in features:
        props = feature["properties"]
        catasto = props.get("com_catasto_code")
        if catasto:
            out[catasto] = {field: props.get(field) for field in LEGACY_FIELDS}
    return out


def merge_legacy(props, legacy_by_catasto):
    """Add the legacy identifiers to props.

    Returns (props, missing) where missing lists the names of municipalities
    with no previous entry. A genuinely new municipality has no openpolis or
    interior-ministry identifier yet; None is the honest value.

    Assigning to keys build_properties already placed leaves them where they
    are, which is what keeps the published key order intact.
    """
    found = legacy_by_catasto.get(props["com_catasto_code"])
    merged = dict(props)
    for field in LEGACY_FIELDS:
        merged[field] = found[field] if found else None
    return merged, ([] if found else [props["name"]])
