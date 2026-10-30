import pytest
from app.utils.unit_normalizer import canonicalize_unit_string, get_canonical_unit_mapping, normalize_biomarker_value


def test_unit_canonicalization():
    assert canonicalize_unit_string("/cumm") == "cells/cumm"
    assert canonicalize_unit_string("/cmm") == "cells/cumm"
    assert canonicalize_unit_string("/cu.mm") == "cells/cumm"
    assert canonicalize_unit_string("/mm3") == "cells/cumm"
    assert canonicalize_unit_string("gm/dl") == "g/dL"
    assert canonicalize_unit_string("Pg") == "pg"
    assert canonicalize_unit_string("10*12/L") == "10^12/L"


def test_canonical_unit_mapping():
    mapping = get_canonical_unit_mapping("/cumm")
    assert mapping["display_unit"] == "cells/cumm"
    assert mapping["canonical_unit"] == "10^3/uL"
    assert mapping["conversion_factor"] == 0.001


def test_platelet_unit_normalization():
    norm = normalize_biomarker_value(
        key="platelet_count",
        value=165000.0,
        unit="/cmm",
        reference_range="1,60,000 - 4,50,000"
    )
    assert norm["original_value"] == 165000.0
    assert norm["display_value"] == 165000.0
    assert norm["canonical_value"] == 165.0
    assert norm["value"] == 165.0
    assert norm["display_unit"] == "cells/cumm"
    assert norm["canonical_unit"] == "10^3/uL"
