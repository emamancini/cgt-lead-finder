"""Tests for group_by_organization, using tiny fake studies: no network, no cache file."""

from organizations import canonical_name, group_by_organization


def make_study(nct_id, lead, collaborators=(), phases=("PHASE2",), start="2025-03", countries=("Sweden",)):
    """Build a minimal study with the same shape as the ClinicalTrials.gov JSON we download."""
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id},
            "statusModule": {"startDateStruct": {"date": start}},
            "designModule": {"phases": list(phases)},
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": lead, "class": "INDUSTRY"},
                "collaborators": [{"name": name, "class": "OTHER"} for name in collaborators],
            },
            "contactsLocationsModule": {"locations": [{"country": c} for c in countries]},
        }
    }


def test_one_study_creates_a_record_for_lead_and_for_each_collaborator():
    organizations = group_by_organization([make_study("NCT1", "Example Pharma", ["Example University Hospital"])])

    assert set(organizations) == {"example pharma", "example university hospital"}
    assert organizations["example pharma"]["lead_study_ids"] == {"NCT1"}
    assert organizations["example university hospital"]["lead_study_ids"] == set()


def test_same_organization_in_two_studies_counts_two_studies():
    studies = [make_study("NCT1", "Example Pharma"), make_study("NCT2", "Example Pharma")]

    record = group_by_organization(studies)["example pharma"]

    assert record["study_ids"] == {"NCT1", "NCT2"}


def test_organization_that_is_lead_and_collaborator_of_one_study_counts_once():
    study = make_study("NCT1", "Example Pharma", ["Example Pharma"])

    record = group_by_organization([study])["example pharma"]

    assert len(record["study_ids"]) == 1


def test_name_variants_are_merged_into_one_record():
    studies = [make_study("NCT1", "Janssen, LP"), make_study("NCT2", "Janssen Research & Development, LLC")]

    organizations = group_by_organization(studies)

    assert list(organizations) == [canonical_name("Janssen, LP")]
    assert len(organizations["janssen"]["study_ids"]) == 2


def test_individuals_are_excluded():
    study = make_study("NCT1", "Example Pharma", ["Jane Example"])

    organizations = group_by_organization([study])

    assert set(organizations) == {"example pharma"}


def test_phases_countries_and_latest_start_are_combined_across_studies():
    studies = [
        make_study("NCT1", "Example Pharma", phases=("PHASE1",), start="2024-05", countries=("Sweden",)),
        make_study("NCT2", "Example Pharma", phases=("PHASE3",), start="2026-01-15", countries=("Germany", "Sweden")),
    ]

    record = group_by_organization(studies)["example pharma"]

    assert record["phases"] == {"PHASE1", "PHASE3"}
    assert record["countries"] == {"Sweden", "Germany"}
    assert record["latest_start"] == "2026-01-15"


def test_study_without_phase_information_does_not_crash():
    study = make_study("NCT1", "Example Pharma")
    del study["protocolSection"]["designModule"]

    record = group_by_organization([study])["example pharma"]

    assert record["phases"] == set()
