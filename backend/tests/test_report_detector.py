import os
import pytest
from app.parsers.report_detector import detect_report

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_detect_hospital_labsmart():
    text = read_fixture("labsmart_cbc.txt")
    res = detect_report(text)
    assert res["hospital"] == "labsmart"
    assert res["report_type"] == "CBC"
    assert res["confidence"] >= 0.90


def test_detect_hospital_aster():
    text = read_fixture("aster_cbc.txt")
    res = detect_report(text)
    assert res["hospital"] == "aster"
    assert res["report_type"] == "CBC"


def test_detect_hospital_apollo():
    text = read_fixture("apollo_cbc.txt")
    res = detect_report(text)
    assert res["hospital"] == "apollo"
    assert res["report_type"] == "CBC"


def test_detect_hospital_medplus():
    text = read_fixture("medplus_cbc.txt")
    res = detect_report(text)
    assert res["hospital"] == "medplus"
    assert res["report_type"] == "CBC"


def test_detect_hospital_vijaya():
    text = read_fixture("vijaya_cbc.txt")
    res = detect_report(text)
    assert res["hospital"] == "vijaya"
    assert res["report_type"] == "CBC"


def test_detect_unknown_hospital():
    res = detect_report("Generic Lab Report - Complete Blood Count")
    assert res["hospital"] == "generic"
    assert res["report_type"] == "CBC"
