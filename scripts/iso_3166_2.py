"""ISO 3166-2:IT reference data (issue #22).

Two lookups, because the two levels of the standard work differently.

Regions carry a numeric code of ISO's own devising, unrelated to the ISTAT one:
Piedmont is ISTAT 01 and ISO IT-21. Nothing can be derived; the table is the
only source. All 20 regions have a code.

Second-level units carry their vehicle registration plate, so the code looks
derivable — but only for units the standard actually lists. Deriving it blindly
would mint identifiers for units ISO does not recognise, which is the opposite
of what an identifier standard is for. The valid set is therefore enumerated
here, and any plate outside it gets no code.

Source: the `iso-codes` package (4.16.0), `/usr/share/iso-codes/json/iso_3166-2.json`,
which is the machine-readable form of the standard. It lists 20 regions and 106
second-level units for Italy. Relevant history, from the ISO newsletters:

- 9 April 2019 — deletion of IT-CI, IT-GO, IT-OG, IT-OT, IT-PN, IT-TS, IT-UD, IT-VS
- 22 November 2019 — deletion of IT-AO
- 22 November 2020 — IT-GO, IT-PN, IT-TS and IT-UD restored as decentralized
  regional entities; IT-SD corrected to IT-SU
"""

# ISTAT region code -> ISO 3166-2 code. ISO's numbering is its own.
_REGIONS = {
    1: "IT-21",   # Piemonte
    2: "IT-23",   # Valle d'Aosta / Vallée d'Aoste
    3: "IT-25",   # Lombardia
    4: "IT-32",   # Trentino-Alto Adige / Südtirol
    5: "IT-34",   # Veneto
    6: "IT-36",   # Friuli-Venezia Giulia
    7: "IT-42",   # Liguria
    8: "IT-45",   # Emilia-Romagna
    9: "IT-52",   # Toscana
    10: "IT-55",  # Umbria
    11: "IT-57",  # Marche
    12: "IT-62",  # Lazio
    13: "IT-65",  # Abruzzo
    14: "IT-67",  # Molise
    15: "IT-72",  # Campania
    16: "IT-75",  # Puglia
    17: "IT-77",  # Basilicata
    18: "IT-78",  # Calabria
    19: "IT-82",  # Sicilia
    20: "IT-88",  # Sardegna
}

# The 106 second-level units listed by the standard, by vehicle plate:
# 80 provinces, 14 metropolitan cities, 6 free municipal consortia,
# 4 decentralized regional entities and 2 autonomous provinces.
_SECOND_LEVEL = frozenset({
    "AG", "AL", "AN", "AP", "AQ", "AR", "AT", "AV", "BA", "BG", "BI", "BL",
    "BN", "BO", "BR", "BS", "BT", "BZ", "CA", "CB", "CE", "CH", "CL", "CN",
    "CO", "CR", "CS", "CT", "CZ", "EN", "FC", "FE", "FG", "FI", "FM", "FR",
    "GE", "GO", "GR", "IM", "IS", "KR", "LC", "LE", "LI", "LO", "LT", "LU",
    "MB", "MC", "ME", "MI", "MN", "MO", "MS", "MT", "NA", "NO", "NU", "OR",
    "PA", "PC", "PD", "PE", "PG", "PI", "PN", "PO", "PR", "PT", "PU", "PV",
    "PZ", "RA", "RC", "RE", "RG", "RI", "RM", "RN", "RO", "SA", "SI", "SO",
    "SP", "SR", "SS", "SU", "SV", "TA", "TE", "TN", "TO", "TP", "TR", "TS",
    "TV", "UD", "VA", "VB", "VC", "VE", "VI", "VR", "VT", "VV",
})

# Plates present in the ISTAT data that the standard does not cover, with the
# reason. Kept as documentation, not consulted at run time: the lookup below
# already returns None for anything outside _SECOND_LEVEL. Listing them here
# means a future vintage that gains a code shows up as a diff on this table.
UNCOVERED = {
    "AO": "IT-AO deleted 2019-11-22; Valle d'Aosta has no province, the region "
          "exercises provincial functions. ISTAT keeps COD_PROV 007 for statistics.",
    "OT": "Gallura Nord-Est Sardegna, created 2026-01-01. IT-OT was deleted "
          "2019-04-09 with the old Olbia-Tempio and never restored.",
    "OG": "Ogliastra, re-created 2026-01-01. IT-OG deleted 2019-04-09.",
    "VS": "Medio Campidano, re-created 2026-01-01. IT-VS deleted 2019-04-09.",
    "CI": "Sulcis Iglesiente, created 2026-01-01. IT-CI was deleted 2019-04-09 "
          "with the old Carbonia-Iglesias.",
}


def region_iso_code(istat_code):
    """Return the ISO 3166-2 code for an ISTAT region code (1-20).

    Raises KeyError outside that range: every Italian region has a code, so a
    miss is a corrupt input rather than a gap in the standard.
    """
    return _REGIONS[int(istat_code)]


def province_iso_code(sigla):
    """Return the ISO 3166-2 code for a vehicle plate, or None.

    None means the standard does not list this unit — see UNCOVERED for the
    five cases in the 1 January 2026 vintage. Four of them are Sardinian
    provinces whose plates match codes ISO deleted in 2019 and has not
    restored, so publishing them would assert a standard identifier that does
    not exist.
    """
    if not sigla:
        return None
    sigla = str(sigla).strip().upper()
    return f"IT-{sigla}" if sigla in _SECOND_LEVEL else None
