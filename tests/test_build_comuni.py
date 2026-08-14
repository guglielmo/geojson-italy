import json

import openpyxl
import pytest

from scripts.build_comuni import read_catasto_codes


@pytest.fixture
def elenco(tmp_path):
    """A minimal Elenco-comuni-italiani.xlsx with only the columns we read."""
    wb = openpyxl.Workbook()
    ws = wb.active
    header = [""] * 21
    header[4] = "Codice Comune formato alfanumerico"
    header[6] = "Denominazione in italiano"
    header[20] = "Codice Catastale del Comune"
    ws.append(header)
    for istat, name, catasto in [
        ("001001", "Agliè", "A074"),
        ("113001", "Aggius", "A069"),
    ]:
        row = [None] * 21
        row[4], row[6], row[20] = istat, name, catasto
        ws.append(row)
    path = tmp_path / "elenco.xlsx"
    wb.save(path)
    return path


def test_read_catasto_codes_maps_istat_to_catasto(elenco):
    assert read_catasto_codes(elenco) == {"001001": "A074", "113001": "A069"}


def test_read_catasto_codes_survives_a_moved_column(tmp_path):
    """ISTAT reorders this spreadsheet between editions.

    The columns are located by heading, so a move must be absorbed rather than
    silently producing a wrong join.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Codice Catastale del Comune", "Denominazione in italiano",
               "Codice Comune formato alfanumerico"])
    ws.append(["A074", "Agliè", "001001"])
    path = tmp_path / "moved.xlsx"
    wb.save(path)

    assert read_catasto_codes(path) == {"001001": "A074"}


def test_read_catasto_codes_fails_loudly_on_a_missing_column(tmp_path):
    """A renamed or dropped column must stop the build, not empty the join."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Denominazione in italiano", "Codice Comune formato alfanumerico"])
    ws.append(["Agliè", "001001"])
    path = tmp_path / "incomplete.xlsx"
    wb.save(path)

    with pytest.raises(ValueError, match="Codice Catastale del Comune"):
        read_catasto_codes(path)
