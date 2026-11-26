"""Entry point of the CGT Lead Finder."""

import json
from pathlib import Path

import requests

from collections import Counter

from organizations import NORDIC_COUNTRIES, classify_organization, group_by_organization
from report import select_leads, write_leads_csv
from scoring import score_organization

API_URL = "https://clinicaltrials.gov/api/v2/studies"
CACHE_PATH = Path("data/raw_studies.json")

# Only organization-level fields. We never request the contacts module, so no
# people's names, emails or phone numbers are ever downloaded.
FIELDS = "|".join([
    "NCTId", "BriefTitle",
    "LeadSponsorName", "LeadSponsorClass", "CollaboratorName", "CollaboratorClass",
    "Phase", "OverallStatus", "StartDate",
    "LocationCountry", "LocationFacility",
    "Condition", "InterventionType", "InterventionName",
])

OTHER_EUROPEAN_COUNTRIES = [
    "Germany", "France", "Netherlands", "Belgium", "Spain", "Italy",
    "United Kingdom", "Switzerland", "Austria", "Poland", "Ireland",
    "Czechia", "Portugal", "Greece", "Hungary",
]

# Studies that are still running or about to start.
STATUSES = "RECRUITING|ACTIVE_NOT_RECRUITING|NOT_YET_RECRUITING|ENROLLING_BY_INVITATION"

# Searched only in the "intervention" field, so a stray mention in a title does not count.
CGT_TERMS = (
    '"CAR-T" OR "CAR T" OR "chimeric antigen receptor" OR "gene therapy" OR "cell therapy" '
    'OR "ATMP" OR "advanced therapy medicinal product" OR "AAV" OR "lentiviral" '
    'OR "mesenchymal stem cell" OR "tumor infiltrating lymphocytes"'
)


def build_country_filter(countries):
    """Turn ["Sweden", "Denmark"] into: AREA[LocationCountry]("Sweden" OR "Denmark")."""
    quoted = [f'"{country}"' for country in countries]
    return "AREA[LocationCountry](" + " OR ".join(quoted) + ")"


def fetch_studies(countries):
    """Return ALL active cell/gene therapy studies with a site in `countries`."""
    params = {
        "query.intr": CGT_TERMS,
        "filter.advanced": build_country_filter(countries),
        "filter.overallStatus": STATUSES,
        "pageSize": 100,
        "countTotal": "true",
        "fields": FIELDS,
        "format": "json",
    }
    all_studies = []
    page_number = 0

    while True:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        page_number += 1
        if page_number == 1:
            # The API only sends totalCount on the first page.
            print(f"Total announced by the API: {data['totalCount']}")
        print(f"Page {page_number}: {len(data['studies'])} studies")

        all_studies.extend(data["studies"])

        next_token = data.get("nextPageToken")
        if next_token is None:
            break
        params["pageToken"] = next_token

    return all_studies


def load_studies():
    """Return the studies from the cache file if it exists, otherwise download and save them."""
    if CACHE_PATH.exists():
        print(f"Loaded from cache: {CACHE_PATH}")
        with open(CACHE_PATH, "r") as f:
            return json.load(f)

    studies = fetch_studies(NORDIC_COUNTRIES + OTHER_EUROPEAN_COUNTRIES)
    CACHE_PATH.parent.mkdir(exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(studies, f)
    print(f"Downloaded and saved to cache: {CACHE_PATH}")
    return studies


def main():
    print("CGT Lead Finder started")

    studies = load_studies()
    print(f"Collected studies: {len(studies)}")

    organizations = group_by_organization(studies)
    for record in organizations.values():
        record["type"] = classify_organization(record)
    print(f"Organizations: {len(organizations)}")

    type_counts = Counter(record["type"] for record in organizations.values())
    for org_type, count in type_counts.most_common():
        print(f"- {org_type}: {count}")

    # Score every candidate customer (type "other" = funders, ministries, CROs: not customers).
    candidates = [record for record in organizations.values() if record["type"] != "other"]
    for record in candidates:
        record["score"], record["reasons"] = score_organization(record)

    leads = select_leads(candidates)
    write_leads_csv(leads, "output/leads.csv")
    print(f"Candidates scored: {len(candidates)}")
    print(f"Wrote {len(leads)} rows to output/leads.csv")


if __name__ == "__main__":
    main()
