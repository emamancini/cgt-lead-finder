"""Pick the organizations to report and write them to a CSV file."""

import csv
from pathlib import Path

from organizations import NORDIC_COUNTRIES
from scoring import PHASE_LABELS, PHASE_POINTS

GLOBAL_TOP = 20
NORDIC_TOP = 10

COLUMNS = [
    "list", "rank", "organization", "type", "score", "active_studies",
    "most_advanced_phase", "nordic_study_sites", "latest_study_start", "reason",
]


def sort_by_score(records):
    """Highest score first; ties go to more studies, then alphabetical order."""
    return sorted(records, key=lambda r: (-r["score"], -len(r["study_ids"]), r["name"]))


def select_leads(candidates):
    """Return [(list_name, rank, record)]: a global top list plus a Nordic academic/GMP list."""
    ranked = sort_by_score(candidates)
    global_top = ranked[:GLOBAL_TOP]

    # "Nordic-based" proxy: a hospital/academic centre or GMP service whose study sites are
    # ALL in Nordic countries (the API gives no organization home country).
    nordic = [
        r for r in ranked
        if r["type"] in ("hospital_academic", "cdmo_gmp")
        and r["countries"] and r["countries"] <= set(NORDIC_COUNTRIES)
    ]

    rows = [("global_top_20", rank, r) for rank, r in enumerate(global_top, start=1)]
    rows += [("nordic_academic_top_10", rank, r) for rank, r in enumerate(nordic[:NORDIC_TOP], start=1)]
    return rows


def best_phase(record):
    best = max(record["phases"], key=lambda phase: PHASE_POINTS.get(phase, 0), default=None)
    return PHASE_LABELS.get(best, "n/a")


def write_leads_csv(rows, path):
    """Write the selected leads to `path` (UTF-8 with BOM so Excel shows accents correctly)."""
    path = Path(path)
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for list_name, rank, r in rows:
            nordic_sites = ", ".join(sorted(set(r["countries"]) & set(NORDIC_COUNTRIES)))
            writer.writerow([
                list_name, rank, r["name"], r["type"], r["score"], len(r["study_ids"]),
                best_phase(r), nordic_sites, r["latest_start"], "; ".join(r["reasons"]),
            ])
