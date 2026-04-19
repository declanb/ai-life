"""
User-specific transit configuration for Coolock (D17) ↔ Harcourt St (D2) commute.

PRE-MULTI-USER PLACEHOLDER: Hardcoded for single-user demo.
TODO: Move to user profiles / settings table when auth is implemented.

Stop IDs are indicative and should be verified at:
https://www.transportforireland.ie/plan-a-journey/
"""

# Home stops in Coolock, Dublin 17
# Routes 15/15A/15B run directly along Harcourt St from Coolock
# TODO: Verify exact stop IDs for Tonlegee Rd / Kilmore Rd / Malahide Rd stops
HOME_STOPS = [
    {
        "id": "4513",  # TODO: VERIFY - Indicative Coolock stop on 15/15A/15B route
        "name": "Tonlegee Rd (Coolock)",
        "mode": "bus",
        "routes": ["15", "15A", "15B"]
    },
    {
        "id": "4512",  # TODO: VERIFY - Indicative Coolock stop on 15/15A/15B route
        "name": "Kilmore Rd (Coolock)",
        "mode": "bus",
        "routes": ["15", "15A", "15B"]
    },
    {
        "id": "4510",  # TODO: VERIFY - Indicative Coolock stop on 15/15A/15B route
        "name": "Malahide Rd (Coolock Village)",
        "mode": "bus",
        "routes": ["15", "15A", "15B"]
    }
]

# Work stops near Harcourt St, Dublin 2
WORK_STOPS = [
    {
        "abbrev": "HAR",
        "name": "Harcourt",
        "mode": "luas",
        "line": "Green Line"
    },
    {
        "abbrev": "STS",
        "name": "St. Stephen's Green",
        "mode": "luas",
        "line": "Green Line"
    }
]

# Default walk times in minutes from door to stop
DEFAULT_WALK_MINUTES = {
    "home": 5,  # Home door → Coolock bus stops
    "work": 4   # Harcourt St office → Luas platform
}

# Routes that serve the Coolock → Harcourt commute
COMMUTE_ROUTES = ["15", "15A", "15B"]
