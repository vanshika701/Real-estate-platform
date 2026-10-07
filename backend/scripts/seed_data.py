"""Static reference data for the seed script: cities, localities, pricing and people."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Locality:
    name: str
    lat: float
    lng: float


@dataclass(frozen=True)
class City:
    name: str
    # Typical residential price per sq ft in INR (low, high); villas and plots are scaled off this.
    rate_per_sqft: tuple[int, int]
    localities: tuple[Locality, ...]
    listing_count: int


CITIES: tuple[City, ...] = (
    City(
        "Greater Noida",
        (4_500, 7_500),
        (
            Locality("Pari Chowk", 28.4655, 77.5100),
            Locality("Alpha 1", 28.4744, 77.5126),
            Locality("Greater Noida West", 28.6070, 77.4280),
            Locality("Knowledge Park", 28.4700, 77.4900),
            Locality("Sector Chi", 28.4588, 77.5328),
        ),
        listing_count=7,
    ),
    City(
        "Noida",
        (7_000, 13_000),
        (
            Locality("Sector 50", 28.5708, 77.3626),
            Locality("Sector 62", 28.6270, 77.3727),
            Locality("Sector 137", 28.5104, 77.4075),
            Locality("Sector 150", 28.4425, 77.4880),
            Locality("Sector 18", 28.5700, 77.3219),
        ),
        listing_count=8,
    ),
    City(
        "Gurugram",
        (9_000, 20_000),
        (
            Locality("DLF Phase 4", 28.4646, 77.0826),
            Locality("Golf Course Road", 28.4503, 77.0990),
            Locality("Sohna Road", 28.4089, 77.0420),
            Locality("Sector 56", 28.4227, 77.1027),
            Locality("Dwarka Expressway", 28.4927, 76.9839),
        ),
        listing_count=8,
    ),
    City(
        "Delhi",
        (12_000, 35_000),
        (
            Locality("Vasant Kunj", 28.5200, 77.1590),
            Locality("Dwarka Sector 12", 28.5921, 77.0406),
            Locality("Greater Kailash", 28.5482, 77.2380),
            Locality("Saket", 28.5245, 77.2066),
            Locality("Rohini", 28.7383, 77.0822),
            Locality("Hauz Khas", 28.5494, 77.2001),
        ),
        listing_count=7,
    ),
    City(
        "Bengaluru",
        (7_000, 18_000),
        (
            Locality("Whitefield", 12.9698, 77.7500),
            Locality("Koramangala", 12.9352, 77.6245),
            Locality("HSR Layout", 12.9116, 77.6474),
            Locality("Indiranagar", 12.9784, 77.6408),
            Locality("Electronic City", 12.8452, 77.6602),
            Locality("Hebbal", 13.0358, 77.5970),
        ),
        listing_count=8,
    ),
    City(
        "Pune",
        (6_500, 15_000),
        (
            Locality("Hinjewadi", 18.5913, 73.7389),
            Locality("Kharadi", 18.5515, 73.9348),
            Locality("Baner", 18.5590, 73.7868),
            Locality("Wakad", 18.5974, 73.7700),
            Locality("Koregaon Park", 18.5362, 73.8930),
        ),
        listing_count=6,
    ),
    City(
        "Mumbai",
        (15_000, 55_000),
        (
            Locality("Andheri West", 19.1364, 72.8296),
            Locality("Powai", 19.1176, 72.9060),
            Locality("Bandra West", 19.0596, 72.8295),
            Locality("Goregaon East", 19.1663, 72.8526),
            Locality("Worli", 19.0176, 72.8180),
            Locality("Thane West", 19.2183, 72.9781),
        ),
        listing_count=6,
    ),
)

DEMO_PASSWORD = "Demo@1234"  # noqa: S105 - public demo credentials, documented in the README


@dataclass(frozen=True)
class Person:
    email: str
    full_name: str
    phone: str


DEMO_BUYER = Person("buyer@demo.com", "Ananya Verma", "+919810012345")
DEMO_AGENT = Person("agent@demo.com", "Aarav Mehta", "+919810054321")
OTHER_AGENTS = (
    Person("priya.sharma@propvisit.dev", "Priya Sharma", "+919820011122"),
    Person("rohan.kapoor@propvisit.dev", "Rohan Kapoor", "+919845033344"),
    Person("neha.iyer@propvisit.dev", "Neha Iyer", "+919890055566"),
)

TITLE_PREFIXES = (
    "Spacious",
    "Sunlit",
    "Corner",
    "Park-facing",
    "Ready-to-move",
    "Newly built",
    "Well-ventilated",
    "Premium",
)

FEATURES = (
    "covered car parking",
    "24x7 security with CCTV",
    "power backup for common areas",
    "a clubhouse and swimming pool",
    "a modular kitchen",
    "east-facing balconies",
    "vitrified tile flooring",
    "a children's play area",
    "a gym and jogging track",
    "piped gas connection",
    "rainwater harvesting",
    "a landscaped central garden",
)

NEARBY = (
    "the metro station",
    "reputed schools",
    "a multi-specialty hospital",
    "a major shopping mall",
    "the IT park",
    "the expressway",
)

SOCIETY_NAMES = (
    "Green Meadows",
    "Silver Oak Residency",
    "Lotus Heights",
    "Palm Grove",
    "Skyline Towers",
    "Orchid Enclave",
    "Royal Habitat",
    "Maple Court",
)
