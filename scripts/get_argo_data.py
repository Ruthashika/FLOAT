import requests
import pandas as pd
import numpy as np
from pathlib import Path


# --------------------------------------------------
# 1. ARGO API CONFIGURATION
# --------------------------------------------------

URL = "https://argovis-api.colorado.edu/argo"

PARAMS = {
    "startDate": "2025-01-01T00:00:00Z",
    "endDate": "2025-01-31T23:59:59Z",

    # Indian Ocean prototype region
    # [lower-left lon, lower-left lat]
    # [upper-right lon, upper-right lat]
    "box": "[[60,-10],[100,20]]",

    "data": "pressure,temperature,salinity",
    "presRange": "0,2000"
}


# --------------------------------------------------
# 2. DOWNLOAD DATA
# --------------------------------------------------

print("Downloading ARGO data...")

response = requests.get(URL, params=PARAMS, timeout=120)

print("HTTP Status:", response.status_code)

response.raise_for_status()

profiles = response.json()

print("Profiles received:", len(profiles))


# --------------------------------------------------
# 3. CONVERT PROFILES → ROWS
# --------------------------------------------------

rows = []

for profile in profiles:

    try:

        # ------------------------------------------
        # Location
        # ------------------------------------------

        coordinates = profile["geolocation"]["coordinates"]

        longitude = coordinates[0]
        latitude = coordinates[1]


        # ------------------------------------------
        # Time
        # ------------------------------------------

        date = profile["timestamp"]


        # ------------------------------------------
        # Float ID
        # ------------------------------------------

        profile_id = profile["_id"]

        # Example:
        # 6903142_054
        #
        # float_id = 6903142
        # cycle_number = 54

        float_id = profile_id.split("_")[0]

        cycle_number = profile.get("cycle_number")


        # ------------------------------------------
        # ARGO measurements
        # ------------------------------------------

        data = profile["data"]

        pressure = data[0]
        temperature = data[1]
        salinity = data[2]


        # ------------------------------------------
        # Safety check
        # ------------------------------------------

        n = min(
            len(pressure),
            len(temperature),
            len(salinity)
        )


        # ------------------------------------------
        # Create one row per depth level
        # ------------------------------------------

        for i in range(n):

            p = pressure[i]
            t = temperature[i]
            s = salinity[i]

            rows.append({
                "latitude": latitude,
                "longitude": longitude,
                "date": date,
                "pressure": p,
                "temperature": t,
                "salinity": s,
                "float_id": float_id,
                "cycle_number": cycle_number
            })


    except Exception as e:

        print(
            "Skipped profile:",
            profile.get("_id", "unknown"),
            "|",
            str(e)
        )


# --------------------------------------------------
# 4. CREATE DATAFRAME
# --------------------------------------------------

print("\nCreating dataframe...")

df = pd.DataFrame(rows)


# --------------------------------------------------
# 5. CLEAN DATA
# --------------------------------------------------

numeric_columns = [
    "latitude",
    "longitude",
    "pressure",
    "temperature",
    "salinity",
    "cycle_number"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# Remove invalid measurements

df = df.dropna(
    subset=[
        "latitude",
        "longitude",
        "pressure",
        "temperature",
        "salinity"
    ]
)


# Remove impossible pressure values

df = df[
    (df["pressure"] >= 0) &
    (df["pressure"] <= 2000)
]


# --------------------------------------------------
# 6. SAVE PARQUET
# --------------------------------------------------

output_path = Path("data/argo_profiles.parquet")

output_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

df.to_parquet(
    output_path,
    index=False
)


# --------------------------------------------------
# 7. SHOW RESULTS
# --------------------------------------------------

print("\n======================================")
print("ARGO DATASET CREATED")
print("======================================")

print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nColumns:")
print(list(df.columns))

print("\nFirst 5 rows:")
print(df.head())

print("\nMissing values:")
print(df.isna().sum())

print("\nDataset saved to:")
print(output_path)

print("\nDataset size:")
print(f"{output_path.stat().st_size / 1024 / 1024:.2f} MB")