"""Tests for classify_organization: the ordered rules (first match wins)."""

import pytest

from organizations import classify_organization


def make_record(name, classes=("OTHER",)):
    return {"name": name, "classes": set(classes)}


@pytest.mark.parametrize("name, classes, expected", [
    ("Example Pharma Inc", ["INDUSTRY"], "company"),
    ("Example University Hospital", ["OTHER"], "hospital_academic"),
    ("Example Foundation", ["OTHER"], "other"),
    # The API often says OTHER or UNKNOWN for real companies: a company-like name wins.
    ("Example Therapeutics Ltd", ["OTHER"], "company"),
    ("Example Therapeutics Ltd", ["UNKNOWN"], "company"),
    # CRO words come before the INDUSTRY class: CROs run studies but do not manufacture.
    ("Example Clinical Research GmbH", ["INDUSTRY"], "other"),
    # Manufacturing words come first of all.
    ("Example Contract Manufacturing", ["INDUSTRY"], "cdmo_gmp"),
    ("Etablissement Fran\u00e7ais du Sang", ["OTHER"], "cdmo_gmp"),
])
def test_classify_organization(name, classes, expected):
    assert classify_organization(make_record(name, classes)) == expected
