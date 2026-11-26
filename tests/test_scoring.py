"""Tests for the scoring rules in scoring.py (one rule = one function = a few tests)."""

from scoring import (
    rule_lead, rule_nordic, rule_phase, rule_recent, rule_study_count, rule_type, score_organization,
)


def make_record(**overrides):
    record = {
        "name": "Example Pharma",
        "type": "company",
        "study_ids": {"NCT1"},
        "lead_study_ids": set(),
        "phases": {"PHASE1"},
        "countries": {"Germany"},
        "latest_start": "2024-01",
    }
    record.update(overrides)
    return record


def test_rule_type_gives_most_points_to_cdmo_then_company_then_hospital():
    points = {t: rule_type(make_record(type=t))[0] for t in ("cdmo_gmp", "company", "hospital_academic")}
    assert points == {"cdmo_gmp": 4, "company": 3, "hospital_academic": 2}


def test_rule_study_count_is_capped_at_five_points():
    record = make_record(study_ids={f"NCT{i}" for i in range(8)})
    assert rule_study_count(record)[0] == 5


def test_rule_phase_uses_the_most_advanced_phase():
    assert rule_phase(make_record(phases={"PHASE1", "PHASE3"}))[0] == 3


def test_rule_phase_gives_nothing_when_phase_is_not_applicable():
    points, reason = rule_phase(make_record(phases={"NA"}))
    assert points == 0
    assert reason is None


def test_rule_nordic_needs_a_site_in_a_nordic_country():
    assert rule_nordic(make_record(countries={"Germany", "Sweden"}))[0] == 3
    assert rule_nordic(make_record(countries={"Germany"}))[0] == 0


def test_rule_recent_starts_counting_from_january_2025():
    assert rule_recent(make_record(latest_start="2024-12-31"))[0] == 0
    assert rule_recent(make_record(latest_start="2025-01"))[0] == 2


def test_rule_lead_gives_a_point_to_an_organization_that_leads_a_study():
    record = make_record(lead_study_ids={"NCT1"})
    assert rule_lead(record)[0] == 1


def test_best_possible_score_is_18_and_every_rule_explains_itself():
    best = make_record(
        type="cdmo_gmp",
        study_ids={f"NCT{i}" for i in range(6)},
        lead_study_ids={"NCT1"},
        phases={"PHASE3"},
        countries={"Sweden"},
        latest_start="2026-06",
    )
    total, reasons = score_organization(best)
    assert total == 18
    assert len(reasons) == 6
