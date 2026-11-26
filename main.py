"""Entry point of the CGT Lead Finder."""

import json
from pathlib import Path

import requests

API_URL = "https://clinicaltrials.gov/api/v2/studies"
CACHE_PATH = Path("data/raw_studies.json")

# Only organization-level fields. We never request the contacts module, so no
# people's names, emails or phone numbers are ever downloaded.
FIELDS = "|".join([
    "NCTId", "BriefTitle",
    "LeadSponsorName", "LeadSponsorClass", "CollaboratorName",
    "Phase", "OverallStatus", "StartDate",
    "LocationCountry", "LocationFacility",
    "Condition", "InterventionType", "InterventionName",
])

NORDIC_COUNTRIES = ["Sweden", "Denmark", "Norway", "Finland", "Iceland"]
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

    unique_ids = {study["protocolSection"]["identificationModule"]["nctId"] for study in studies}
    unique_count = len(unique_ids)
    print(f"Unique studies: {unique_count}")


if __name__ == "__main__":
    main()
