"""Score how good a customer an organization could be for caloTrace (rapid sterility testing).

Each rule is a small function that returns (points, reason). The reason is None when the
rule does not apply. Weights are judgement calls, documented in learning/plan.md.
"""

from organizations import NORDIC_COUNTRIES

TYPE_POINTS = {"cdmo_gmp": 4, "company": 3, "hospital_academic": 2, "other": 0}
TYPE_LABELS = {
    "cdmo_gmp": "CDMO/GMP service",
    "company": "company",
    "hospital_academic": "hospital/academic centre",
    "other": "other",
}
PHASE_POINTS = {"PHASE3": 3, "PHASE2": 2, "PHASE1": 1, "EARLY_PHASE1": 1}
PHASE_LABELS = {"PHASE3": "Phase 3", "PHASE2": "Phase 2", "PHASE1": "Phase 1", "EARLY_PHASE1": "Phase 1"}
MAX_STUDY_POINTS = 5
NORDIC_POINTS = 3
RECENT_FROM = "2025-01"
RECENT_POINTS = 2
LEAD_POINTS = 1


def rule_type(record):
    """Producers buy: CDMO/GMP 4, company 3, hospital/academic 2."""
    points = TYPE_POINTS[record["type"]]
    return points, f"type: {TYPE_LABELS[record['type']]}"


def rule_study_count(record):
    """1 point per active study, capped, so size alone cannot win."""
    count = len(record["study_ids"])
    points = min(count, MAX_STUDY_POINTS)
    return points, f"{count} active stud{'y' if count == 1 else 'ies'}"


def rule_phase(record):
    """Later phases mean bigger-scale manufacturing: Phase 3 = 3, Phase 2 = 2, Phase 1 = 1."""
    best = max(record["phases"], key=lambda phase: PHASE_POINTS.get(phase, 0), default=None)
    points = PHASE_POINTS.get(best, 0)
    if points == 0:
        return 0, None
    return points, f"most advanced: {PHASE_LABELS[best]}"


def rule_nordic(record):
    """Symcel is Swedish: a study site in a Nordic country is a plus."""
    nordic = sorted(set(record["countries"]) & set(NORDIC_COUNTRIES))
    if not nordic:
        return 0, None
    return NORDIC_POINTS, "study site in " + ", ".join(nordic)


def rule_recent(record):
    """Programmes with a study starting from 2025 on (including planned ones) are alive."""
    if record["latest_start"] >= RECENT_FROM:
        return RECENT_POINTS, f"latest study start {record['latest_start']}"
    return 0, None


def rule_lead(record):
    """A lead sponsor decides how its therapies are made; a collaborator may not."""
    if record["lead_study_ids"]:
        return LEAD_POINTS, f"lead sponsor of {len(record['lead_study_ids'])}"
    return 0, None


RULES = [rule_type, rule_study_count, rule_phase, rule_nordic, rule_recent, rule_lead]


def score_organization(record):
    """Return (total_points, [reasons]) for one organization record."""
    total = 0
    reasons = []
    for rule in RULES:
        points, reason = rule(record)
        total += points
        if reason is not None and points > 0:
            reasons.append(f"{reason} (+{points})")
    return total, reasons
