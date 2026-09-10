"""
FLOATCHAT - Natural Language Ocean Query Engine

Converts user questions into structured ARGO dataset queries
and generates human-readable responses.

Current capabilities:
- Temperature queries
- Salinity queries
- Pressure-range queries
- Geographic coordinate queries
- Named ocean / region queries
- Average / minimum / maximum statistics
- ARGO float counting
- ARGO float ID listing
- Location / ocean-region identification
- Conversational responses
"""

import re
from typing import Optional, Tuple, Dict

import pandas as pd

from query_engine import (
    find_profiles,
)


# ============================================================
# BASIC HELPERS
# ============================================================

def _clean_question(question: str) -> str:
    """Normalize whitespace while preserving the original meaning."""
    return re.sub(r"\s+", " ", question.strip())


def _format_number(value, decimals: int = 2) -> str:
    """Format numeric values cleanly."""
    try:
        value = float(value)

        if abs(value - round(value)) < 1e-9:
            return f"{int(round(value)):,}"

        return f"{value:,.{decimals}f}"

    except (TypeError, ValueError):
        return str(value)


def _numeric(value) -> Optional[float]:
    """Safely convert a value to float."""
    try:
        value = float(value)

        if pd.isna(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


# ============================================================
# DATASET LOADER
# ============================================================

def load_argo_data() -> Optional[pd.DataFrame]:
    """Load the local ARGO parquet dataset safely."""

    try:
        return pd.read_parquet(
            "data/argo_profiles.parquet"
        )

    except Exception:
        return None


# ============================================================
# COORDINATE EXTRACTION
# ============================================================

def extract_coordinates(
    question: str,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract latitude and longitude from natural language.

    Supports:
        78°E and 0°N
        78E 0N
        78 E, 0 N
        latitude 0 longitude 78
        0°N, 78°E
        around 78°E and 0°N
    """

    q = question.lower()

    latitude = None
    longitude = None

    # --------------------------------------------------------
    # Explicit latitude / longitude wording
    # --------------------------------------------------------

    lat_match = re.search(
        r"(?:latitude|lat)\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s*°?\s*([ns])?",
        q,
    )

    lon_match = re.search(
        r"(?:longitude|lon|lng)\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s*°?\s*([ew])?",
        q,
    )

    if lat_match:

        latitude = float(
            lat_match.group(1)
        )

        direction = lat_match.group(2)

        if direction == "s":
            latitude = -abs(latitude)

        elif direction == "n":
            latitude = abs(latitude)

    if lon_match:

        longitude = float(
            lon_match.group(1)
        )

        direction = lon_match.group(2)

        if direction == "w":
            longitude = -abs(longitude)

        elif direction == "e":
            longitude = abs(longitude)

    if latitude is not None and longitude is not None:
        return latitude, longitude

    # --------------------------------------------------------
    # Degree + direction format
    # --------------------------------------------------------

    coord_pattern = re.compile(
        r"(-?\d+(?:\.\d+)?)\s*°?\s*([nsew])"
    )

    matches = coord_pattern.findall(q)

    for value, direction in matches:

        value = float(value)

        if direction == "n":
            latitude = abs(value)

        elif direction == "s":
            latitude = -abs(value)

        elif direction == "e":
            longitude = abs(value)

        elif direction == "w":
            longitude = -abs(value)

    if latitude is not None and longitude is not None:
        return latitude, longitude

    # --------------------------------------------------------
    # Decimal coordinate fallback
    # --------------------------------------------------------

    numbers = re.findall(
        r"(?<![a-z])[-+]?\d+(?:\.\d+)?(?![a-z])",
        q,
    )

    if len(numbers) >= 2:

        try:

            first = float(numbers[0])
            second = float(numbers[1])

            if (
                -90 <= first <= 90
                and -180 <= second <= 180
            ):

                latitude = first
                longitude = second

                return latitude, longitude

        except ValueError:
            pass

    return latitude, longitude


# ============================================================
# NAMED OCEAN / REGION DETECTION
# ============================================================

def detect_named_region(
    question: str,
) -> Optional[str]:
    """
    Detect a named oceanographic region from natural language.

    This is different from resolve_location_name():

        resolve_location_name()
            coordinate -> region name

        detect_named_region()
            question text -> requested region
    """

    q = question.lower()

    # Most specific regions first
    region_patterns = [
        (
            "equatorial indian ocean",
            [
                "equatorial indian ocean",
                "equatorial indian",
            ],
        ),
        (
            "bay of bengal",
            [
                "bay of bengal",
                "bengal bay",
            ],
        ),
        (
            "arabian sea",
            [
                "arabian sea",
                "arabian",
            ],
        ),
        (
            "south indian ocean",
            [
                "south indian ocean",
                "southern indian ocean",
            ],
        ),
        (
            "north indian ocean",
            [
                "north indian ocean",
                "northern indian ocean",
            ],
        ),
        (
            "indian ocean",
            [
                "indian ocean",
                "indian oceans",
            ],
        ),
        (
            "pacific ocean",
            [
                "pacific ocean",
                "pacific",
            ],
        ),
        (
            "atlantic ocean",
            [
                "atlantic ocean",
                "atlantic",
            ],
        ),
        (
            "southern ocean",
            [
                "southern ocean",
                "antarctic ocean",
            ],
        ),
        (
            "arctic ocean",
            [
                "arctic ocean",
                "arctic",
            ],
        ),
    ]

    for region_name, patterns in region_patterns:

        for pattern in patterns:

            if re.search(
                rf"\b{re.escape(pattern)}\b",
                q,
            ):
                return region_name

    return None


# ============================================================
# REGION BOUNDING BOXES
# ============================================================

def get_region_bounds(
    region: str,
) -> Optional[Dict[str, float]]:
    """
    Return approximate geographic bounding boxes.

    Format:
        min_lat
        max_lat
        min_lon
        max_lon

    These are intentionally broad oceanographic regions.
    """

    region = region.lower().strip()

    regions = {

        # ----------------------------------------------------
        # Indian Ocean
        # ----------------------------------------------------

        "indian ocean": {
            "min_lat": -40,
            "max_lat": 30,
            "min_lon": 20,
            "max_lon": 120,
        },

        "equatorial indian ocean": {
            "min_lat": -10,
            "max_lat": 5,
            "min_lon": 50,
            "max_lon": 100,
        },

        "bay of bengal": {
            "min_lat": 5,
            "max_lat": 22,
            "min_lon": 80,
            "max_lon": 100,
        },

        "arabian sea": {
            "min_lat": 5,
            "max_lat": 25,
            "min_lon": 50,
            "max_lon": 80,
        },

        "south indian ocean": {
            "min_lat": -40,
            "max_lat": -10,
            "min_lon": 20,
            "max_lon": 120,
        },

        "north indian ocean": {
            "min_lat": 22,
            "max_lat": 30,
            "min_lon": 40,
            "max_lon": 100,
        },

        # ----------------------------------------------------
        # Pacific Ocean
        # ----------------------------------------------------

        "pacific ocean": {
            "min_lat": -60,
            "max_lat": 60,
            "min_lon": 120,
            "max_lon": 180,
        },

        # ----------------------------------------------------
        # Atlantic Ocean
        # ----------------------------------------------------

        "atlantic ocean": {
            "min_lat": -60,
            "max_lat": 60,
            "min_lon": -70,
            "max_lon": 20,
        },

        # ----------------------------------------------------
        # Southern Ocean
        # ----------------------------------------------------

        "southern ocean": {
            "min_lat": -90,
            "max_lat": -40,
            "min_lon": -180,
            "max_lon": 180,
        },

        # ----------------------------------------------------
        # Arctic Ocean
        # ----------------------------------------------------

        "arctic ocean": {
            "min_lat": 66,
            "max_lat": 90,
            "min_lon": -180,
            "max_lon": 180,
        },
    }

    return regions.get(region)


# ============================================================
# REGION FILTER
# ============================================================

def filter_region_data(
    data: pd.DataFrame,
    region: str,
) -> pd.DataFrame:
    """
    Filter ARGO observations according to a named region.
    """

    bounds = get_region_bounds(region)

    if bounds is None:
        return pd.DataFrame()

    if data.empty:
        return data

    working = data.copy()

    # Ensure coordinates are numeric
    working["latitude"] = pd.to_numeric(
        working["latitude"],
        errors="coerce",
    )

    working["longitude"] = pd.to_numeric(
        working["longitude"],
        errors="coerce",
    )

    mask = (
        working["latitude"].between(
            bounds["min_lat"],
            bounds["max_lat"],
        )
        &
        working["longitude"].between(
            bounds["min_lon"],
            bounds["max_lon"],
        )
    )

    return working[mask]


# ============================================================
# LOCATION / OCEAN REGION RESOLVER
# ============================================================

def resolve_location_name(
    latitude: Optional[float],
    longitude: Optional[float],
) -> str:
    """
    Convert ocean coordinates into a useful geographic/ocean-region
    name.
    """

    if latitude is None or longitude is None:
        return "Unknown location"

    lat = float(latitude)
    lon = float(longitude)

    # Normalize longitude
    if lon > 180:
        lon -= 360

    if lon < -180:
        lon += 360

    # --------------------------------------------------------
    # Indian Ocean
    # --------------------------------------------------------

    if -10 <= lat <= 5 and 50 <= lon <= 100:
        return "Equatorial Indian Ocean"

    if 5 < lat <= 22 and 80 <= lon <= 100:
        return "Bay of Bengal"

    if 5 < lat <= 25 and 50 <= lon < 80:
        return "Arabian Sea"

    if -40 <= lat < -10 and 20 <= lon <= 120:
        return "South Indian Ocean"

    if 22 < lat <= 30 and 40 <= lon <= 100:
        return "North Indian Ocean"

    if -40 <= lat <= 30 and 20 <= lon <= 120:
        return "Indian Ocean"

    # --------------------------------------------------------
    # Pacific
    # --------------------------------------------------------

    if -60 <= lat <= 60 and 120 <= lon <= 180:
        return "Pacific Ocean"

    if -60 <= lat <= 60 and -180 <= lon < -70:
        return "Pacific Ocean"

    # --------------------------------------------------------
    # Atlantic
    # --------------------------------------------------------

    if -60 <= lat <= 60 and -70 <= lon <= 20:
        return "Atlantic Ocean"

    # --------------------------------------------------------
    # Southern Ocean
    # --------------------------------------------------------

    if lat < -40:
        return "Southern Ocean"

    # --------------------------------------------------------
    # Arctic
    # --------------------------------------------------------

    if lat > 66:
        return "Arctic Ocean"

    return "Open Ocean"


def format_location(
    latitude: Optional[float],
    longitude: Optional[float],
) -> str:
    """Return a human-readable coordinate string."""

    if latitude is None or longitude is None:
        return "Unknown coordinates"

    lat = abs(float(latitude))
    lon = abs(float(longitude))

    lat_dir = "N" if latitude >= 0 else "S"
    lon_dir = "E" if longitude >= 0 else "W"

    return (
        f"{_format_number(lat)}°{lat_dir}, "
        f"{_format_number(lon)}°{lon_dir}"
    )


# ============================================================
# PRESSURE EXTRACTION
# ============================================================

def extract_pressure_range(
    question: str,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract pressure range from natural language.

    Supports:
        0 to 500 dbar
        0-500 dbar
        0 – 500 dbar
        between 0 and 500 dbar
        500 and 1000 dbar
        at 500 dbar
        500 dbar
    """

    q = question.lower()

    q = (
        q.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    # --------------------------------------------------------
    # between X and Y
    # --------------------------------------------------------

    match = re.search(
        r"between\s+(-?\d+(?:\.\d+)?)\s*"
        r"(?:and|to)\s+"
        r"(-?\d+(?:\.\d+)?)\s*"
        r"(?:dbar|db|decibar)?",
        q,
    )

    if match:

        a = float(match.group(1))
        b = float(match.group(2))

        return min(a, b), max(a, b)

    # --------------------------------------------------------
    # X to Y
    # --------------------------------------------------------

    match = re.search(
        r"(-?\d+(?:\.\d+)?)\s*"
        r"(?:to|-)\s*"
        r"(-?\d+(?:\.\d+)?)\s*"
        r"(?:dbar|db|decibar)",
        q,
    )

    if match:

        a = float(match.group(1))
        b = float(match.group(2))

        return min(a, b), max(a, b)

    # --------------------------------------------------------
    # X-Y without dbar
    # --------------------------------------------------------

    if re.search(
        r"\b(?:pressure|depth|dbar|db|decibar)\b",
        q,
    ):

        match = re.search(
            r"(?<!\d)"
            r"(\d+(?:\.\d+)?)"
            r"\s*-\s*"
            r"(\d+(?:\.\d+)?)"
            r"(?!\d)",
            q,
        )

        if match:

            a = float(match.group(1))
            b = float(match.group(2))

            return min(a, b), max(a, b)

    # --------------------------------------------------------
    # Single pressure
    # --------------------------------------------------------

    match = re.search(
        r"(?:at|around|near|of)?\s*"
        r"(-?\d+(?:\.\d+)?)\s*"
        r"(?:dbar|db|decibar)",
        q,
    )

    if match:

        pressure = float(match.group(1))

        return (
            max(0, pressure - 25),
            pressure + 25,
        )

    return None, None


# ============================================================
# VARIABLE DETECTION
# ============================================================

def detect_variable(
    question: str,
) -> Optional[str]:

    q = question.lower()

    if re.search(
        r"\b(?:temperature|temp|thermal|warm|cold)\b",
        q,
    ):
        return "temperature"

    if re.search(
        r"\b(?:salinity|salt|saline)\b",
        q,
    ):
        return "salinity"

    if re.search(
        r"\b(?:pressure|dbar|decibar)\b",
        q,
    ):
        return "pressure"

    return None


# ============================================================
# STATISTIC DETECTION
# ============================================================

def detect_statistic(
    question: str,
) -> str:

    q = question.lower()

    if re.search(
        r"\b(?:minimum|min|lowest|coldest|least)\b",
        q,
    ):
        return "minimum"

    if re.search(
        r"\b(?:maximum|max|highest|warmest|greatest)\b",
        q,
    ):
        return "maximum"

    return "average"


# ============================================================
# INTENT DETECTION
# ============================================================

def is_location_question(
    question: str,
) -> bool:

    q = question.lower()

    location_words = [
        "where is",
        "where are",
        "what location",
        "which location",
        "what region",
        "which region",
        "name of the location",
        "location name",
        "ocean region",
        "which ocean",
    ]

    return any(
        word in q
        for word in location_words
    )


def is_float_question(
    question: str,
) -> bool:

    q = question.lower()

    float_words = [
        "float",
        "floats",
        "argo float",
        "argo floats",
    ]

    return any(
        word in q
        for word in float_words
    )


def is_greeting(
    question: str,
) -> bool:

    q = question.lower().strip()

    greetings = [
        "hi",
        "hello",
        "hey",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "hi floatchat",
        "hello floatchat",
    ]

    return q in greetings


def is_help_question(
    question: str,
) -> bool:

    q = question.lower()

    return (
        "help" in q
        or "what can you do" in q
        or "how can you help" in q
        or "capabilities" in q
    )


def is_casual_question(
    question: str,
) -> bool:

    q = question.lower().strip()

    casual = [
        "how are you",
        "who are you",
        "what are you",
        "what is your name",
        "thanks",
        "thank you",
        "nice",
        "cool",
        "great",
    ]

    return any(
        x in q
        for x in casual
    )


# ============================================================
# LOCATION RESPONSE
# ============================================================

def process_location_question(
    question: str,
    latitude: Optional[float],
    longitude: Optional[float],
) -> str:

    if latitude is None or longitude is None:

        return (
            "I can identify the ocean region when you "
            "provide coordinates. For example, try: "
            "\"Where is 78°E and 0°N?\""
        )

    location_name = resolve_location_name(
        latitude,
        longitude,
    )

    coordinates = format_location(
        latitude,
        longitude,
    )

    return (
        f"📍 **{location_name}**\n\n"
        f"The coordinates **{coordinates}** fall within "
        f"the **{location_name}** region covered by "
        f"FLOATCHAT."
    )


# ============================================================
# NAMED REGION OCEAN QUERY
# ============================================================

def process_region_query(
    question: str,
    region: str,
    min_pressure: Optional[float],
    max_pressure: Optional[float],
) -> str:
    """
    Process queries such as:

        What is the temperature in the Pacific Ocean?
        What is the salinity in the Atlantic Ocean?
        What is the average temperature in the Indian Ocean?
    """

    variable = detect_variable(question)

    if variable is None:
        variable = "temperature"

    statistic = detect_statistic(question)

    data = load_argo_data()

    if data is None:

        return (
            "I couldn't load the ARGO dataset right now."
        )

    if data.empty:

        return (
            "The ARGO dataset is currently empty."
        )

    # --------------------------------------------------------
    # Filter region
    # --------------------------------------------------------

    working = filter_region_data(
        data,
        region,
    )

    # --------------------------------------------------------
    # Pressure filtering
    # --------------------------------------------------------

    if (
        min_pressure is not None
        or max_pressure is not None
    ):

        if "pressure" in working.columns:

            working["pressure"] = pd.to_numeric(
                working["pressure"],
                errors="coerce",
            )

            if min_pressure is not None:

                working = working[
                    working["pressure"] >= min_pressure
                ]

            if max_pressure is not None:

                working = working[
                    working["pressure"] <= max_pressure
                ]

    # --------------------------------------------------------
    # Pressure description
    # --------------------------------------------------------

    if (
        min_pressure is not None
        and max_pressure is not None
    ):

        pressure_text = (
            f"{_format_number(min_pressure)}–"
            f"{_format_number(max_pressure)} dbar"
        )

    else:

        pressure_text = (
            "the available 0–2000 dbar pressure range"
        )

    # --------------------------------------------------------
    # No matching observations
    # --------------------------------------------------------

    if working.empty:

        return (
            f"🌊 **{region.title()}**\n\n"
            f"I couldn't find any matching ARGO "
            f"observations for the **{region.title()}** "
            f"within {pressure_text}.\n\n"
            f"**Current dataset coverage:** approximately "
            f"60–98.5°E and 10°S–19.3°N, which is primarily "
            f"the Indian Ocean region."
        )

    # --------------------------------------------------------
    # Variable validation
    # --------------------------------------------------------

    if variable not in working.columns:

        matching_column = None

        for column in working.columns:

            if column.lower() == variable.lower():

                matching_column = column
                break

        if matching_column:

            variable_column = matching_column

        else:

            return (
                f"The dataset does not currently contain "
                f"{variable} measurements for this region."
            )

    else:

        variable_column = variable

    # --------------------------------------------------------
    # Numeric values
    # --------------------------------------------------------

    values = pd.to_numeric(
        working[variable_column],
        errors="coerce",
    ).dropna()

    if values.empty:

        return (
            f"I couldn't find valid {variable} measurements "
            f"for the {region.title()}."
        )

    # --------------------------------------------------------
    # Statistic
    # --------------------------------------------------------

    if statistic == "minimum":

        value = values.min()
        statistic_text = "minimum"

    elif statistic == "maximum":

        value = values.max()
        statistic_text = "maximum"

    else:

        value = values.mean()
        statistic_text = "average"

    # --------------------------------------------------------
    # Units
    # --------------------------------------------------------

    if variable == "temperature":

        value_text = f"{value:.2f}°C"

    elif variable == "salinity":

        value_text = f"{value:.2f} PSU"

    elif variable == "pressure":

        value_text = f"{value:.2f} dbar"

    else:

        value_text = f"{value:.2f}"

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return (
        f"🌊 **{region.title()}**\n\n"
        f"The **{statistic_text} {variable}** is "
        f"**{value_text}**. "
        f"I found **{len(values):,} ARGO measurements** "
        f"within **{pressure_text}**."
    )


# ============================================================
# FLOAT PROCESSING
# ============================================================

def process_float_question(
    question: str,
    data: Optional[pd.DataFrame] = None,
) -> str:

    if data is None:
        data = load_argo_data()

    if data is None:

        return (
            "I couldn't load the ARGO dataset right now."
        )

    if data.empty:

        return (
            "The ARGO dataset is currently empty."
        )

    q = question.lower()

    latitude, longitude = extract_coordinates(
        question
    )

    named_region = detect_named_region(
        question
    )

    min_pressure, max_pressure = extract_pressure_range(
        question
    )

    # --------------------------------------------------------
    # Float ID column
    # --------------------------------------------------------

    if "float_id" not in data.columns:

        return (
            "The current ARGO dataset does not contain "
            "float IDs, so I cannot identify individual "
            "floats."
        )

    working = data.copy()

    working["float_id"] = (
        working["float_id"]
        .astype(str)
    )

    working = working[
        working["float_id"].notna()
        &
        (working["float_id"].str.strip() != "")
        &
        (working["float_id"].str.lower() != "nan")
    ]

    # --------------------------------------------------------
    # Named region filtering
    # --------------------------------------------------------

    location_name = None
    coordinate_text = None

    if (
        named_region is not None
        and latitude is None
        and longitude is None
    ):

        working = filter_region_data(
            working,
            named_region,
        )

        location_name = named_region.title()

    # --------------------------------------------------------
    # Coordinate filtering
    # --------------------------------------------------------

    elif latitude is not None and longitude is not None:

        radius = 2.0

        lat_mask = working[
            "latitude"
        ].between(
            latitude - radius,
            latitude + radius,
        )

        lon_mask = working[
            "longitude"
        ].between(
            longitude - radius,
            longitude + radius,
        )

        working = working[
            lat_mask & lon_mask
        ]

        location_name = resolve_location_name(
            latitude,
            longitude,
        )

        coordinate_text = format_location(
            latitude,
            longitude,
        )

    # --------------------------------------------------------
    # Pressure filtering
    # --------------------------------------------------------

    if (
        min_pressure is not None
        or max_pressure is not None
    ):

        if "pressure" in working.columns:

            working["pressure"] = pd.to_numeric(
                working["pressure"],
                errors="coerce",
            )

            if min_pressure is not None:

                working = working[
                    working["pressure"] >= min_pressure
                ]

            if max_pressure is not None:

                working = working[
                    working["pressure"] <= max_pressure
                ]

    # --------------------------------------------------------
    # Unique floats
    # --------------------------------------------------------

    unique_floats = sorted(
        working["float_id"]
        .dropna()
        .unique()
        .tolist()
    )

    float_count = len(
        unique_floats
    )

    observation_count = len(
        working
    )

    # --------------------------------------------------------
    # Pressure text
    # --------------------------------------------------------

    if (
        min_pressure is not None
        and max_pressure is not None
    ):

        pressure_text = (
            f"{_format_number(min_pressure)}–"
            f"{_format_number(max_pressure)} dbar"
        )

    else:

        pressure_text = (
            "the available 0–2000 dbar pressure range"
        )

    # --------------------------------------------------------
    # Named region response
    # --------------------------------------------------------

    if (
        named_region is not None
        and latitude is None
        and longitude is None
    ):

        if float_count == 0:

            return (
                f"🌊 **{named_region.title()}**\n\n"
                f"I couldn't find any unique ARGO floats "
                f"in this region within {pressure_text}.\n\n"
                f"**Current dataset coverage:** approximately "
                f"60–98.5°E and 10°S–19.3°N."
            )

        wants_list = any(
            word in q
            for word in [
                "show",
                "list",
                "which",
                "ids",
                "id",
                "names",
                "identify",
            ]
        )

        if wants_list:

            float_ids = ", ".join(
                unique_floats
            )

            return (
                f"🌊 **{named_region.title()}**\n\n"
                f"I found **{float_count} unique ARGO "
                f"floats** across {pressure_text}.\n\n"
                f"**Float IDs:** {float_ids}\n\n"
                f"These floats contributed "
                f"**{observation_count:,} observations**."
            )

        return (
            f"🌊 **{named_region.title()}**\n\n"
            f"I found **{float_count} unique ARGO floats** "
            f"across {pressure_text}. "
            f"These floats contributed "
            f"**{observation_count:,} observations**."
        )

    # --------------------------------------------------------
    # Coordinate-specific response
    # --------------------------------------------------------

    if (
        latitude is not None
        and longitude is not None
    ):

        if float_count == 0:

            return (
                f"📍 **{location_name}** — "
                f"{coordinate_text}\n\n"
                f"I couldn't find any unique ARGO floats "
                f"in the specified area within "
                f"{pressure_text}."
            )

        wants_list = any(
            word in q
            for word in [
                "show",
                "list",
                "which",
                "ids",
                "id",
                "names",
                "identify",
            ]
        )

        if wants_list:

            float_ids = ", ".join(
                unique_floats
            )

            return (
                f"📍 **{location_name}** — "
                f"{coordinate_text}\n\n"
                f"I found **{float_count} unique ARGO "
                f"floats** around this location across "
                f"{pressure_text}.\n\n"
                f"**Float IDs:** {float_ids}\n\n"
                f"These floats contributed "
                f"**{observation_count:,} observations**."
            )

        return (
            f"📍 **{location_name}** — "
            f"{coordinate_text}\n\n"
            f"I found **{float_count} unique ARGO floats** "
            f"around this location across "
            f"{pressure_text}. "
            f"These floats contributed "
            f"**{observation_count:,} observations**."
        )

    # --------------------------------------------------------
    # Dataset-wide response
    # --------------------------------------------------------

    if float_count == 0:

        return (
            "I couldn't identify any ARGO floats "
            "in the current dataset."
        )

    wants_list = any(
        word in q
        for word in [
            "show",
            "list",
            "which",
            "ids",
            "id",
            "names",
            "identify",
        ]
    )

    if wants_list:

        float_ids = ", ".join(
            unique_floats
        )

        return (
            f"I found **{float_count} unique ARGO floats** "
            f"in the available dataset.\n\n"
            f"**Float IDs:** {float_ids}\n\n"
            f"These floats contributed "
            f"**{observation_count:,} observations** "
            f"across {pressure_text}."
        )

    return (
        f"I found **{float_count} unique ARGO floats** "
        f"in the available dataset across "
        f"{pressure_text}. "
        f"These floats contributed "
        f"**{observation_count:,} observations**."
    )


# ============================================================
# NORMAL OCEANOGRAPHIC QUERY
# ============================================================

def process_ocean_query(
    question: str,
    latitude: Optional[float],
    longitude: Optional[float],
    min_pressure: Optional[float],
    max_pressure: Optional[float],
) -> str:

    variable = detect_variable(
        question
    )

    if variable is None:
        variable = "temperature"

    statistic = detect_statistic(
        question
    )

    # --------------------------------------------------------
    # Location information
    # --------------------------------------------------------

    location_name = None
    coordinate_text = None

    if (
        latitude is not None
        and longitude is not None
    ):

        location_name = resolve_location_name(
            latitude,
            longitude,
        )

        coordinate_text = format_location(
            latitude,
            longitude,
        )

    # --------------------------------------------------------
    # Pressure text
    # --------------------------------------------------------

    if (
        min_pressure is not None
        and max_pressure is not None
    ):

        pressure_text = (
            f"{_format_number(min_pressure)}–"
            f"{_format_number(max_pressure)} dbar"
        )

    else:

        pressure_text = (
            "the available 0–2000 dbar pressure range"
        )

    # --------------------------------------------------------
    # Query dataset
    # --------------------------------------------------------

    try:

        result = find_profiles(
            latitude=latitude,
            longitude=longitude,
            radius=2,
            min_pressure=min_pressure,
            max_pressure=max_pressure,
        )

    except Exception as exc:

        return (
            "I encountered an error while querying the "
            f"ARGO dataset: {exc}"
        )

    if result is None:

        return (
            "No matching ARGO observations were found."
        )

    if not isinstance(
        result,
        pd.DataFrame,
    ):

        try:

            result = pd.DataFrame(
                result
            )

        except Exception:

            return (
                "I couldn't interpret the ARGO query result."
            )

    if result.empty:

        if location_name:

            return (
                f"📍 **{location_name}** — "
                f"{coordinate_text}\n\n"
                f"I couldn't find matching ARGO "
                f"observations within "
                f"{pressure_text}."
            )

        return (
            f"I couldn't find matching ARGO "
            f"observations within {pressure_text}."
        )

    # --------------------------------------------------------
    # Variable column
    # --------------------------------------------------------

    if variable not in result.columns:

        matching_column = None

        for column in result.columns:

            if column.lower() == variable.lower():

                matching_column = column
                break

        if matching_column:

            variable_column = matching_column

        else:

            return (
                f"The dataset does not currently contain "
                f"{variable} measurements for this query."
            )

    else:

        variable_column = variable

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    values = pd.to_numeric(
        result[variable_column],
        errors="coerce",
    ).dropna()

    if values.empty:

        return (
            f"I couldn't find valid {variable} "
            f"measurements for this query."
        )

    # --------------------------------------------------------
    # Statistic
    # --------------------------------------------------------

    if statistic == "minimum":

        value = values.min()
        statistic_text = "minimum"

    elif statistic == "maximum":

        value = values.max()
        statistic_text = "maximum"

    else:

        value = values.mean()
        statistic_text = "average"

    # --------------------------------------------------------
    # Units
    # --------------------------------------------------------

    if variable == "temperature":

        value_text = f"{value:.2f}°C"

    elif variable == "salinity":

        value_text = f"{value:.2f} PSU"

    elif variable == "pressure":

        value_text = f"{value:.2f} dbar"

    else:

        value_text = f"{value:.2f}"

    # --------------------------------------------------------
    # Location response
    # --------------------------------------------------------

    if location_name:

        return (
            f"📍 **{location_name}** — "
            f"{coordinate_text}\n\n"
            f"The **{statistic_text} {variable}** is "
            f"**{value_text}**. "
            f"I found **{len(values):,} ARGO measurements** "
            f"around this location within "
            f"**{pressure_text}**."
        )

    # --------------------------------------------------------
    # Standard response
    # --------------------------------------------------------

    return (
        f"The **{statistic_text} {variable}** is "
        f"**{value_text}**. "
        f"I found **{len(values):,} ARGO measurements** "
        f"within **{pressure_text}**."
    )


# ============================================================
# MAIN QUESTION PROCESSOR
# ============================================================

def process_question(
    question: str,
) -> str:

    if not question or not question.strip():

        return (
            "Ask me an ocean-data question. For example: "
            "\"What is the average temperature around "
            "78°E and 0°N?\""
        )

    question = _clean_question(
        question
    )

    # ========================================================
    # GREETINGS
    # ========================================================

    if is_greeting(question):

        return (
            "Hello! 👋 I'm **FLOATCHAT**, your conversational "
            "interface for ARGO ocean data.\n\n"
            "You can ask me about temperature, salinity, "
            "pressure, ARGO floats, locations, or geographic "
            "regions."
        )

    # ========================================================
    # HELP
    # ========================================================

    if is_help_question(question):

        return (
            "I can help you explore the available ARGO "
            "dataset. 🌊\n\n"
            "**Try asking:**\n"
            "• What is the average temperature around "
            "78°E and 0°N?\n"
            "• What is the salinity between 0 and 500 dbar?\n"
            "• What is the minimum temperature around "
            "78°E and 0°N?\n"
            "• What is the temperature in the Indian Ocean?\n"
            "• What is the salinity in the Pacific Ocean?\n"
            "• How many ARGO floats are in the dataset?\n"
            "• Show me the ARGO floats around "
            "78°E and 0°N.\n"
            "• Where is 78°E and 0°N?\n"
            "• What ocean region is 78°E and 0°N in?"
        )

    # ========================================================
    # CASUAL QUESTIONS
    # ========================================================

    if is_casual_question(question):

        q = question.lower()

        if "thank" in q:

            return (
                "You're welcome! 🌊 "
                "Ask me another ARGO data question anytime."
            )

        if "name" in q:

            return (
                "I'm **FLOATCHAT** — a conversational "
                "interface for exploring ARGO ocean data."
            )

        if (
            "who are you" in q
            or "what are you" in q
        ):

            return (
                "I'm **FLOATCHAT**, an AI-style conversational "
                "ocean-data assistant designed to make ARGO "
                "measurements easier to explore."
            )

        return (
            "I'm ready to explore the ARGO dataset with you. 🌊"
        )

    # ========================================================
    # EXTRACT COORDINATES
    # ========================================================

    latitude, longitude = extract_coordinates(
        question
    )

    # ========================================================
    # EXPLICIT LOCATION QUESTION
    # ========================================================

    if is_location_question(question):

        return process_location_question(
            question,
            latitude,
            longitude,
        )

    # ========================================================
    # FLOAT QUESTION
    # ========================================================

    if is_float_question(question):

        data = load_argo_data()

        return process_float_question(
            question,
            data,
        )

    # ========================================================
    # PRESSURE
    # ========================================================

    min_pressure, max_pressure = extract_pressure_range(
        question
    )

    # ========================================================
    # NAMED REGION
    #
    # IMPORTANT:
    # This MUST happen before normal ocean queries.
    # Otherwise:
    #
    # "temperature in Pacific Ocean"
    #
    # would fall through to the whole dataset.
    # ========================================================

    named_region = detect_named_region(
        question
    )

    if (
        named_region is not None
        and latitude is None
        and longitude is None
    ):

        return process_region_query(
            question=question,
            region=named_region,
            min_pressure=min_pressure,
            max_pressure=max_pressure,
        )

    # ========================================================
    # NORMAL COORDINATE / DATASET QUERY
    # ========================================================

    return process_ocean_query(
        question=question,
        latitude=latitude,
        longitude=longitude,
        min_pressure=min_pressure,
        max_pressure=max_pressure,
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    test_questions = [

        # Named regions
        "What is the temperature in the Pacific Ocean?",
        "What is the average temperature in the Atlantic Ocean?",
        "What is the salinity in the Indian Ocean?",
        "What is the average temperature in the Arabian Sea?",
        "What is the temperature in the Bay of Bengal?",

        # Coordinates
        "Where is 78°E and 0°N?",
        "What is the average temperature around 78°E and 0°N?",
        "What is the average temperature around 78°E and 0°N between 0 and 500 dbar?",
        "What is the salinity around 78°E and 0°N?",

        # Floats
        "How many ARGO floats are around 78°E and 0°N?",
        "Show me the ARGO floats around 78°E and 0°N.",
        "How many ARGO floats are in the dataset?",
    ]

    for q in test_questions:

        print("\n" + "=" * 70)
        print("QUESTION:", q)
        print("-" * 70)
        print(process_question(q))