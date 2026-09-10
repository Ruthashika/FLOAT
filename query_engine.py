import math
from pathlib import Path

import pandas as pd


# ============================================================
# FLOATCHAT QUERY ENGINE
# ARGO DATA SEARCH + STATISTICS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PARQUET_PATH = BASE_DIR / "data" / "argo_profiles.parquet"


# ============================================================
# LOAD DATA
# ============================================================

try:
    df = pd.read_parquet(PARQUET_PATH)

    print(
        f"QUERY ENGINE: loaded {len(df):,} ARGO observations"
    )

except Exception as error:
    df = pd.DataFrame()

    print(
        "QUERY ENGINE: dataset loading failed:",
        error
    )


# ============================================================
# DATASET SUMMARY
# ============================================================

def dataset_summary():

    if df.empty:
        return {
            "rows": 0,
            "profiles": 0,
            "floats": 0,
            "latitude_min": None,
            "latitude_max": None,
            "longitude_min": None,
            "longitude_max": None,
            "pressure_min": None,
            "pressure_max": None,
            "temperature_min": None,
            "temperature_max": None,
            "salinity_min": None,
            "salinity_max": None,
        }

    result = {
        "rows": int(len(df)),
        "profiles": (
            int(df["cycle_number"].nunique())
            if "cycle_number" in df.columns
            else 0
        ),
        "floats": (
            int(df["float_id"].nunique())
            if "float_id" in df.columns
            else 0
        ),
    }

    numeric_columns = [
        "latitude",
        "longitude",
        "pressure",
        "temperature",
        "salinity",
    ]

    for column in numeric_columns:

        if column not in df.columns:
            result[f"{column}_min"] = None
            result[f"{column}_max"] = None
            continue

        series = pd.to_numeric(
            df[column],
            errors="coerce"
        ).dropna()

        if series.empty:
            result[f"{column}_min"] = None
            result[f"{column}_max"] = None

        else:
            result[f"{column}_min"] = float(
                series.min()
            )

            result[f"{column}_max"] = float(
                series.max()
            )

    return result


# ============================================================
# LOCATION SEARCH
# ============================================================

def search_location(
    data,
    latitude=None,
    longitude=None,
    radius=2
):
    """
    Filter observations within an approximate geographic radius.

    Radius is interpreted in degrees for this prototype.
    This works well for the regional ARGO visualization.
    """

    if data is None or len(data) == 0:
        return pd.DataFrame()

    result = data.copy()

    if latitude is None or longitude is None:
        return result

    if "latitude" not in result.columns:
        return pd.DataFrame()

    if "longitude" not in result.columns:
        return pd.DataFrame()

    try:
        latitude = float(latitude)
        longitude = float(longitude)
        radius = abs(float(radius))

    except (TypeError, ValueError):
        return pd.DataFrame()

    # Approximate degree-distance filtering.
    lat_difference = (
        result["latitude"] - latitude
    )

    lon_difference = (
        result["longitude"] - longitude
    )

    # Correct longitude scaling according to latitude.
    longitude_scale = max(
        math.cos(math.radians(latitude)),
        0.1
    )

    distance = (
        lat_difference ** 2
        +
        (
            lon_difference
            * longitude_scale
        ) ** 2
    ) ** 0.5

    result = result[
        distance <= radius
    ]

    return result


# ============================================================
# PRESSURE FILTER
# ============================================================

def search_pressure(
    data,
    min_pressure=None,
    max_pressure=None
):
    """
    Filter ARGO observations by pressure.

    ARGO pressure is expressed in dbar.
    For oceanographic visualization, pressure is used
    as the vertical/depth-related coordinate.
    """

    if data is None or len(data) == 0:
        return pd.DataFrame()

    result = data.copy()

    if "pressure" not in result.columns:
        return pd.DataFrame()

    pressure = pd.to_numeric(
        result["pressure"],
        errors="coerce"
    )

    if min_pressure is not None:

        try:
            min_pressure = float(
                min_pressure
            )

            result = result[
                pressure >= min_pressure
            ]

        except (TypeError, ValueError):
            pass

    if max_pressure is not None:

        try:
            max_pressure = float(
                max_pressure
            )

            result = result[
                pressure <= max_pressure
            ]

        except (TypeError, ValueError):
            pass

    return result


# ============================================================
# FIND PROFILES
# ============================================================

def find_profiles(
    latitude=None,
    longitude=None,
    radius=2,
    min_pressure=None,
    max_pressure=None
):
    """
    Main ARGO observation query.
    """

    if df.empty:
        return pd.DataFrame()

    data = df.copy()

    # --------------------------------------------------------
    # Geographic filtering
    # --------------------------------------------------------

    data = search_location(
        data,
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )

    # --------------------------------------------------------
    # Pressure filtering
    # --------------------------------------------------------

    data = search_pressure(
        data,
        min_pressure=min_pressure,
        max_pressure=max_pressure
    )

    return data


# ============================================================
# TEMPERATURE STATISTICS
# ============================================================

def temperature_statistics(data):

    if data is None or len(data) == 0:
        return {
            "count": 0,
            "mean_temperature": None,
            "minimum_temperature": None,
            "maximum_temperature": None,
        }

    if "temperature" not in data.columns:
        return {
            "count": 0,
            "mean_temperature": None,
            "minimum_temperature": None,
            "maximum_temperature": None,
        }

    values = pd.to_numeric(
        data["temperature"],
        errors="coerce"
    ).dropna()

    # Reasonable physical range for this prototype.
    values = values[
        values.between(-5, 40)
    ]

    if values.empty:
        return {
            "count": 0,
            "mean_temperature": None,
            "minimum_temperature": None,
            "maximum_temperature": None,
        }

    return {
        "count": int(len(values)),
        "mean_temperature": float(
            values.mean()
        ),
        "minimum_temperature": float(
            values.min()
        ),
        "maximum_temperature": float(
            values.max()
        ),
    }


# ============================================================
# SALINITY STATISTICS
# ============================================================

def salinity_statistics(data):

    if data is None or len(data) == 0:
        return {
            "count": 0,
            "mean_salinity": None,
            "minimum_salinity": None,
            "maximum_salinity": None,
        }

    if "salinity" not in data.columns:
        return {
            "count": 0,
            "mean_salinity": None,
            "minimum_salinity": None,
            "maximum_salinity": None,
        }

    values = pd.to_numeric(
        data["salinity"],
        errors="coerce"
    ).dropna()

    # Remove clearly invalid salinity values.
    # This prevents corrupted/sentinel values from
    # dominating the statistics.
    values = values[
        values.between(0, 45)
    ]

    if values.empty:
        return {
            "count": 0,
            "mean_salinity": None,
            "minimum_salinity": None,
            "maximum_salinity": None,
        }

    return {
        "count": int(len(values)),
        "mean_salinity": float(
            values.mean()
        ),
        "minimum_salinity": float(
            values.min()
        ),
        "maximum_salinity": float(
            values.max()
        ),
    }


# ============================================================
# SIMPLE DATASET TEST
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 70)
    print("FLOATCHAT QUERY ENGINE TEST")
    print("=" * 70)

    print("\nDATASET SUMMARY")

    print(
        dataset_summary()
    )

    print("\nTEST QUERY")

    test_data = find_profiles(
        latitude=0,
        longitude=78,
        radius=2,
        min_pressure=0,
        max_pressure=500
    )

    print(
        f"Matching observations: {len(test_data):,}"
    )

    print("\nTEMPERATURE")

    print(
        temperature_statistics(
            test_data
        )
    )

    print("\nSALINITY")

    print(
        salinity_statistics(
            test_data
        )
    )

    print("\n" + "=" * 70)