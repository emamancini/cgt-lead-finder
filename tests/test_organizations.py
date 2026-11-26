"""Tests for the name-cleaning functions in organizations.py."""

import pytest

from organizations import canonical_name, clean_name, looks_like_person


def test_clean_name_removes_legal_suffix_and_punctuation():
    assert clean_name("Acme Inc.") == "acme"


def test_clean_name_removes_leading_the():
    assert clean_name("The Example Clinic") == "example clinic"


# --- canonical_name: cleaning plus the hand-written ALIASES ------------------------------

def test_canonical_name_merges_legal_variants_of_the_same_group():
    assert canonical_name("Janssen, LP") == canonical_name("Janssen Research & Development, LLC")


def test_canonical_name_keeps_manufacturing_divisions_separate():
    # Kite runs its own cell-therapy manufacturing: deliberately NOT merged with its parent.
    assert canonical_name("Kite, A Gilead Company") != canonical_name("Gilead Sciences")


def test_canonical_name_leaves_unknown_names_cleaned_only():
    assert canonical_name("Example Pharma GmbH") == "example pharma"


# --- looks_like_person: INVENTED names only, never real people ---------------------------

@pytest.mark.parametrize("name", [
    "Jane Example",
    "Example Jane",
    "Prof. Dr. Jane Example",
    "John Example, MD",
    "Anna Maria Example",
])
def test_looks_like_person_flags_personal_names(name):
    assert looks_like_person(name) is True


@pytest.mark.parametrize("name", [
    "Example University Hospital",
    "Example Therapeutics Inc.",
    "Example Biotech GmbH",
    "Boehringer Ingelheim",      # two capitalized words, but on the allow-list of organizations
    "Imperial College London",   # same: allow-listed organization
    "Pfizer",                    # one word: never a person
])
def test_looks_like_person_does_not_flag_organizations(name):
    assert looks_like_person(name) is False


def test_looks_like_person_is_not_fooled_by_bio_inside_a_first_name():
    # Regression: "Fabio" contains "bio", which once made a person look like a company.
    assert looks_like_person("Example Fabio") is True
