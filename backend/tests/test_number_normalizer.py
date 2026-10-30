import pytest
from app.utils.number_normalizer import normalize_number_string, extract_numbers_with_formatting


def test_indian_number_formatting():
    assert normalize_number_string("1,65,000") == "165000"
    assert normalize_number_string("4,50,000") == "450000"
    assert normalize_number_string("98,000") == "98000"
    assert normalize_number_string("2,10,500") == "210500"
    assert normalize_number_string("8,000") == "8000"
    assert normalize_number_string("11,000") == "11000"


def test_lakh_text_formatting():
    assert extract_numbers_with_formatting("1.25 lakh") == 125000.0
    assert extract_numbers_with_formatting("2 Lakhs") == 200000.0
    assert extract_numbers_with_formatting("3 lakh/cmm") == 300000.0
    assert extract_numbers_with_formatting("2.10 lakh/cmm") == 210000.0


def test_decimal_preservation():
    assert extract_numbers_with_formatting("94.0") == 94.0
    assert extract_numbers_with_formatting("27.7") == 27.7
    assert extract_numbers_with_formatting("12.50") == 12.5
