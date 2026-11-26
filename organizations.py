"""Turn raw study records into organization-level records."""

import re

NORDIC_COUNTRIES = ["Sweden", "Denmark", "Norway", "Finland", "Iceland"]

# Legal forms removed from the END of a name, so "Acme Inc." and "Acme" match.
LEGAL_SUFFIXES = {
    "inc", "ltd", "llc", "gmbh", "plc", "ag", "sa", "bv", "ab", "as", "spa",
    "limited", "corporation", "corp", "co", "company", "sas", "oy", "kg", "uk", "france", "llc",
}

# Hand-written decisions: cleaned name -> the organization we treat it as.
# Only merge names that a salesperson would call "the same customer".
ALIASES = {
    "novartis pharmaceuticals": "novartis",
    # Legal variants of the same group are merged.
    "janssen lp": "janssen",
    "janssen research & development": "janssen",
    "bristol-myers squibb services unlimited": "bristol-myers squibb",
    # Deliberately NOT merged: divisions that run their own cell-therapy manufacturing
    # (Kite / Gilead, Juno / Bristol-Myers Squibb) and university vs hospital
    # (Karolinska Institutet / Karolinska University Hospital).
}

# Words that signal an organization. If a name contains one, it is NOT treated as a person.
ORGANIZATION_WORDS = re.compile(
    r"\b(?:univers|hospital|h[oô]pital|hospices|klinik|clinic|institut|istitut|centre|center|centro"
    r"|foundation|fondazione|fundaci|stichting|group|therap|pharma|bio|medic|health|research"
    r"|cancer|lab\b|school|ospedal|azienda|charit|assistance|network|netzwerk|trust|region"
    r"|council|commission|agency|society|association|associazione|bank|banc|service|servicio"
    r"|blood|sang|cell|gene|science|academ|umc|eth\b|nhs|cnrs|inserm|ministry|district"
    r"|company|consorci|etablissement|cro\b|trial|foundation|study|imaging|core|sciences)",
    re.IGNORECASE,
)

# Organizations whose name has the SHAPE of a person's name (2-4 capitalized words).
# Reviewed by hand. This list may only ever contain organizations, never people.
KNOWN_ORGANIZATIONS = [
    "Apices Soluciones S.L.", "Boehringer Ingelheim", "Bold insight", "Bristol-Myers Squibb",
    "CH Sainte-Anne, Paris, France", "CSL Behring", "Celyad Oncology SA", "IRCCS San Raffaele",
    "Immatics US, Inc.", "Imperial College London", "Janssen, LP", "King's College London",
    "Kom Op Tegen Kanker", "Krebsforschung Rhein-Main e.V.", "MeiraGTx Ocular UK Ltd",
    "Oy Medfiles Ltd", "PolTREG S.A.", "Red de Terapia Celular", "USWM CT, LLC",
    "Vall Hebron Insitut Recerca", "Hoffmann-La Roche", "Eli Lilly and Company",
    "AvenCell Europe GmbH", "CuraCell TX AB", "Histocell SL, Spain",
    "OneChain Immunotherapeutics", "STZ eyetrial", "Zelluna Immunotherapy AS",
]

# Lowercase particles that appear inside personal names ("Maarten van de Weijden").
NAME_PARTICLES = {"de", "van", "der", "den", "von", "la", "da", "di", "del", "dos", "le"}


def looks_like_person(name):
    """Guess whether `name` is a private individual (not an organization), by its shape.

    Deliberately conservative about organizations: a name with an organization word is never
    a person. No list of people's names is kept anywhere: only the shape is checked.
    """
    cleaned = clean_name(name)
    if cleaned in KNOWN_ORGANIZATIONS_CLEAN or ORGANIZATION_WORDS.search(name):
        return False

    # Titles: "Prof. Dr. Jane Example", "John Example, MD"
    if re.search(r"\b(prof|dr|md|phd)\b\.?", name, re.IGNORECASE):
        return True

    words = [w for w in re.split(r"[\s,]+", clean_name(name).title().strip()) if w and w.lower() not in NAME_PARTICLES]
    if not 2 <= len(words) <= 4:
        return False
    return all(re.fullmatch(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", w) and w[0].isupper() for w in words)


def get_study_organizations(study):
    """Return a list of (organization_name, role, api_class) triples for one study.

    The role is "lead" for the lead sponsor and "collaborator" for the others.
    The class is what the API says (INDUSTRY, OTHER, ...), or "UNKNOWN".
    """
    module = study["protocolSection"]["sponsorCollaboratorsModule"]
    lead = module["leadSponsor"]

    triples = [(lead["name"], "lead", lead.get("class", "UNKNOWN"))]

    for collaborator in module.get("collaborators", []):
        triples.append((collaborator["name"], "collaborator", collaborator.get("class", "UNKNOWN")))

    return triples


def clean_name(name):
    """Lowercase, drop punctuation, a leading "The" and trailing legal forms ("Inc.", "Ltd")."""
    text = re.sub(r"[.,]", " ", name.lower())
    words = text.split()
    if words and words[0] == "the":
        words = words[1:]
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


KNOWN_ORGANIZATIONS_CLEAN = {clean_name(name) for name in KNOWN_ORGANIZATIONS}


def canonical_name(name):
    """Return the name we group by: cleaned, then mapped through ALIASES if listed."""
    cleaned = clean_name(name)
    return ALIASES.get(cleaned, cleaned)


def group_by_organization(studies):
    """Return {canonical_name: record}: ONE record per organization, individuals excluded."""
    organizations = {}

    for study in studies:
        protocol = study["protocolSection"]
        nct_id = protocol["identificationModule"]["nctId"]
        phases = protocol.get("designModule", {}).get("phases", [])
        start_date = protocol["statusModule"].get("startDateStruct", {}).get("date", "")
        locations = protocol.get("contactsLocationsModule", {}).get("locations", [])
        countries = {location["country"] for location in locations if "country" in location}

        for name, role, org_class in get_study_organizations(study):
            if looks_like_person(name):
                continue

            key = canonical_name(name)
            if key not in organizations:
                organizations[key] = {
                    "name": name,  # first spelling seen, used for display
                    "classes": set(),
                    "study_ids": set(),
                    "lead_study_ids": set(),
                    "phases": set(),
                    "countries": set(),
                    "latest_start": "",
                }
            record = organizations[key]

            record["study_ids"].add(nct_id)
            if role == "lead":
                record["lead_study_ids"].add(nct_id)
            record["classes"].add(org_class)
            record["phases"].update(phases)
            record["countries"].update(countries)
            record["latest_start"] = max(record["latest_start"], start_date)

    return organizations


# --- Classification -------------------------------------------------------------------

# Words in a name that suggest contract manufacturing / GMP cell processing.
# ClinicalTrials.gov has NO "CDMO" class, so this hand-written list is the only way to find them.
CDMO_KEYWORDS = [
    "cdmo", "cmo ", "contract manufactur", "contract development", "manufacturing",
    "gmp", "cell processing", "biomanufactur", "transfusion",
]

# GMP-style service organizations recognised by name (reviewed by hand; organizations only).
KNOWN_GMP_SERVICES = [
    "zellwerk", "fraunhofer institute for cell therapy", "etablissement fran\u00e7ais du sang",
    "scottish national blood transfusion service", "banc de sang i teixits",
    "genethon",  # non-profit with its own GMP bioproduction facility (judgement call)
]

# Organizations whose name does not look like a company but are (reviewed by hand).
KNOWN_COMPANIES = ["miltenyi", "vecura", "finovatis", "bioclever", "bold insight"]

# Service providers that run studies for others but do not manufacture: not direct customers.
CRO_WORDS = re.compile(r"\bcro\b|clinical research|clinical trial|consult", re.IGNORECASE)

HOSPITAL_ACADEMIC_WORDS = re.compile(
    r"\b(?:univers|hospital|h[o\u00f4]pital|hospices|ospedal|klinik|clinic|institut|istitut|centre|center"
    r"|school|college|academ|ziekenhuis|sjukhus|sygehus|azienda|irccs|inserm|cnrs|umc|nhs|assistance"
    r"|charit|servicio|consorci|district|region\b|health service|social care|cardiolog|gustave roussy"
    r"|urc-cic|insitut|fundaci|\bch\b)",
    re.IGNORECASE,
)

COMPANY_NAME_WORDS = re.compile(
    r"therap|pharma|biotech|bioscien|biolog|biomedicine|oncology|gene\b|genetics|immuno|medicines"
    r"|\b(?:gmbh|ag|ab|sa|sas|bv|nv|ltd|llc|inc|plc|srl|s\.r\.l|sl|s\.l|kg|limited)\b|z o\.?o",
    re.IGNORECASE,
)


def classify_organization(record):
    """Return one of: "cdmo_gmp", "company", "hospital_academic", "other".

    Rules are checked in this order; the first one that matches wins.
    """
    name = record["name"].lower()
    known = record["classes"] - {"UNKNOWN"}

    if any(word in name for word in CDMO_KEYWORDS) or any(service in name for service in KNOWN_GMP_SERVICES):
        return "cdmo_gmp"

    if CRO_WORDS.search(name):
        return "other"

    if "INDUSTRY" in known or any(company in name for company in KNOWN_COMPANIES):
        return "company"

    if HOSPITAL_ACADEMIC_WORDS.search(name):
        return "hospital_academic"

    # The API often labels real companies "OTHER" or leaves them UNKNOWN: trust a company-like name.
    if COMPANY_NAME_WORDS.search(name):
        return "company"

    return "other"
