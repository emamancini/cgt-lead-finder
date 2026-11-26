"""Entry point of the CGT Lead Finder."""

import requests

API_URL = "https://clinicaltrials.gov/api/v2/studies"


def fetch_studies(country):
    """Ask the API for one page of CAR-T studies in `country` and return the response as a dict."""
    params = {
        "query.term": "CAR-T",
        "query.locn": country,
        "pageSize": 5,
        "countTotal": "true",
        "format": "json",
    }
    response = requests.get(API_URL, params=params)
    print(f"Status code: {response.status_code}")

    return response.json()


def main():
    print("CGT Lead Finder started")

    data = fetch_studies("Sweden")
    studies = data["studies"]
    print(f"Total studies found: {data['totalCount']}")
    print(f"Studies on this page: {len(studies)}")

    first = studies[0]
    title = first["protocolSection"]["identificationModule"]["briefTitle"]
    print(f"Title: {title}")

    sponsor = first["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"]
    print(f"Sponsor: {sponsor}")


if __name__ == "__main__":
    main()
