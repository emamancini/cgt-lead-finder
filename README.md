# CGT Lead Finder

A small Python tool that finds **organizations running cell and gene therapy (CGT) studies in the
Nordics and the rest of Europe**, scores them, and writes a ranked CSV with a one-sentence reason
for each. It uses only the public [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api).

It is a demo of how public registry data can help find potential users of a rapid sterility test
for cell and gene therapy manufacturing, such as Symcel's caloTrace. The idea: companies, hospitals
and GMP manufacturers that run active cell/gene therapy studies are the ones that make such
products. The tool is **not** affiliated with, or endorsed by, any organization named in its output.

## What you get

`output/leads.csv`: 30 organizations in two lists.

| List | Rows | What it is |
|---|---|---|
| `global_top_20` | 20 | Best score among all candidate organizations |
| `nordic_academic_top_10` | 10 | Best hospitals/universities/GMP services whose study sites are **all** in Nordic countries |

Columns: `list, rank, organization, type, score, active_studies, most_advanced_phase,
nordic_study_sites, latest_study_start, reason`.

Snapshot of 26 November 2026: 448 active studies, 412 organizations, 365 scored candidates.

## How to run

You need Python 3 (developed and tested with 3.13) and an internet connection for the first run.

```bash
git clone https://github.com/emamancini/cgt-lead-finder.git
cd cgt-lead-finder
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

The first run downloads the studies (about 2 seconds) and saves them to `data/raw_studies.json`.
Later runs read that file instead of calling the API. **Delete it to download fresh data**: the
registry changes, so new runs can give different numbers than the snapshot above.

Run the tests with `pytest` (40 tests, no network needed).

## How it works

1. **Download** (`main.py`): active studies (recruiting, not yet recruiting, active, enrolling by
   invitation) whose *intervention* mentions CAR-T, gene therapy, cell therapy, ATMP, AAV, lentiviral,
   mesenchymal stem cells or tumor-infiltrating lymphocytes, with at least one site in 5 Nordic
   or 15 other European countries. Follows every result page and caches the response.
2. **Organizations** (`organizations.py`): takes lead sponsors and collaborators, cleans names
   (case, punctuation, legal forms such as "Inc." or "GmbH"), merges a few hand-picked variants of
   the same group, and groups the studies into one record per organization.
3. **Type**: `company`, `hospital_academic`, `cdmo_gmp` or `other`, from ordered rules based on the
   API's sponsor class and on the name. The API has no "CDMO" class.
4. **Score** (`scoring.py`): six transparent rules, maximum 18 points. Each rule returns its points
   and a reason, and the reasons are what you read in the CSV.

| Rule | Points |
|---|---|
| Type: CDMO/GMP service 4, company 3, hospital/academic 2 | 2-4 |
| Active studies (1 each, capped at 5) | 1-5 |
| Most advanced phase: Phase 3 = 3, Phase 2 = 2, Phase 1 = 1 | 0-3 |
| At least one study site in a Nordic country | 3 |
| A study starting in 2025 or later (planned ones included) | 2 |
| Lead sponsor of at least one study | 1 |

Type `other` (funders, ministries, CROs, networks) is not scored: those are not direct customers.

## Privacy

Only **organization-level** data is used. The tool asks the API for a fixed list of fields and never
requests the contacts module, so contact names, e-mails and phone numbers are never downloaded.

The registry does list some private individuals (for example investigators) as sponsors or
collaborators. They are excluded by a rule that recognizes the *shape* of a personal name, with a
reviewed allow-list of organizations that look like names. This is a heuristic, not a guarantee, so
the final CSV was also read line by line before publishing. No personal names are stored in this
repository.

## Limitations

- **One source.** Only ClinicalTrials.gov. Trials registered only in the EU's CTIS are missing.
- **20 countries**, not the whole of Europe.
- **No organization home country.** The API gives the countries of the *study sites*. "Nordic study
  site" does not mean "based in the Nordics"; the Nordic list uses "all sites are Nordic" as a proxy.
- **Types are name-based guesses.** Commercial CDMOs rarely sponsor trials, so almost none appear;
  the `cdmo_gmp` group is mostly GMP-style services and non-profit producers (a judgement call).
- **Name merging is manual.** Subsidiaries are kept apart when they run their own manufacturing
  (for example several entities of one pharma group appear separately).
- **The weights are judgement, not measurement.** The score is a guide to prioritization.
- **A snapshot.** Study statuses change; the data date is part of any conclusion.

## Project layout

```
main.py             download, cache and run the pipeline
organizations.py    names, privacy filter, grouping, type
scoring.py          the six scoring rules
report.py           selects the leads and writes the CSV
tests/              pytest suite (invented names and fake studies only)
output/leads.csv    the result
```

Data source: ClinicalTrials.gov (U.S. National Library of Medicine); see its terms and conditions for reuse.
