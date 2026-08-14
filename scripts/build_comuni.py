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
