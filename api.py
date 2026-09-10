from pathlib import Path

import pandas as pd

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chat_engine import process_question

from query_engine import (
    find_profiles,
    temperature_statistics,
    salinity_statistics,
    dataset_summary,
)


# ============================================================
# FLOATCHAT API
# ============================================================

app = FastAPI(
    title="FLOATCHAT API",
    description="AI-powered interface for ARGO ocean data",
    version="1.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://float-gu85.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATASET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PARQUET_PATH = (
    BASE_DIR
    / "data"
    / "argo_profiles.parquet"
)


try:
    argo_df = pd.read_parquet(PARQUET_PATH)

    print("=" * 60)
    print("ARGO DATASET LOADED SUCCESSFULLY")
    print(f"Rows available : {len(argo_df):,}")
    print(f"Columns        : {list(argo_df.columns)}")
    print("=" * 60)

except Exception as error:

    argo_df = None

    print("=" * 60)
    print("WARNING: ARGO DATASET COULD NOT BE LOADED")
    print(error)
    print("=" * 60)


# ============================================================
# REQUEST MODELS
# ============================================================

class OceanQuery(BaseModel):
    latitude: float | None = None
    longitude: float | None = None

    radius: float = 2

    min_pressure: float | None = None
    max_pressure: float | None = None

    variable: str = "temperature"


class ChatRequest(BaseModel):
    question: str


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {
        "application": "FLOATCHAT",
        "status": "online",
        "message": "ARGO Ocean Data API is running",
        "version": "1.0",
    }


# ============================================================
# SUMMARY
# ============================================================

@app.get("/summary")
def summary():

    try:

        return dataset_summary()

    except Exception as error:

        return {
            "success": False,
            "error": str(error),
        }


# ============================================================
# STRUCTURED OCEAN QUERY
# ============================================================

@app.post("/query")
def ocean_query(
    query: OceanQuery
):

    try:

        # ----------------------------------------------------
        # Find matching ARGO measurements
        # ----------------------------------------------------

        data = find_profiles(

            latitude=query.latitude,

            longitude=query.longitude,

            radius=query.radius,

            min_pressure=query.min_pressure,

            max_pressure=query.max_pressure,
        )

        # ----------------------------------------------------
        # No results
        # ----------------------------------------------------

        if len(data) == 0:

            return {
                "success": False,

                "message": (
                    "No ARGO measurements found "
                    "for the specified conditions."
                ),

                "results": {},
            }

        # ----------------------------------------------------
        # Validate variable
        # ----------------------------------------------------

        variable = (
            query.variable
            .lower()
            .strip()
        )

        # ----------------------------------------------------
        # Temperature
        # ----------------------------------------------------

        if variable == "temperature":

            statistics = temperature_statistics(
                data
            )

        # ----------------------------------------------------
        # Salinity
        # ----------------------------------------------------

        elif variable == "salinity":

            statistics = salinity_statistics(
                data
            )

        # ----------------------------------------------------
        # Unsupported variable
        # ----------------------------------------------------

        else:

            return {
                "success": False,

                "message": (
                    "Supported variables: "
                    "temperature, salinity"
                ),

                "results": {},
            }

        # ----------------------------------------------------
        # Successful response
        # ----------------------------------------------------

        return {

            "success": True,

            "query": {

                "latitude": query.latitude,

                "longitude": query.longitude,

                "radius": query.radius,

                "min_pressure": query.min_pressure,

                "max_pressure": query.max_pressure,

                "variable": variable,
            },

            "results": statistics,

        }

    except Exception as error:

        print(
            "Ocean query error:",
            error
        )

        return {

            "success": False,

            "message": (
                "Unable to process the ocean query."
            ),

            "error": str(error),

            "results": {},
        }


# ============================================================
# CHAT / NATURAL LANGUAGE QUERY
# ============================================================

@app.post("/chat")
def chat(
    request: ChatRequest
):

    try:

        # ----------------------------------------------------
        # Validate question
        # ----------------------------------------------------

        question = (
            request.question
            .strip()
        )

        if not question:

            return {

                "success": False,

                "answer": (
                    "Please enter a question "
                    "about the ARGO ocean dataset."
                ),

                "parameters": {},

                "statistics": {},
            }

        # ----------------------------------------------------
        # Process natural-language question
        # ----------------------------------------------------

        answer = process_question(
            question
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # process_question() returns the readable answer
        # as a string.
        #
        # The React frontend expects:
        #
        # result.answer
        #
        # Therefore we wrap the answer in JSON.
        # ----------------------------------------------------

        return {

            "success": True,

            "answer": str(answer),

            "parameters": {
                "question": question,
            },

            "statistics": {},

        }

    except Exception as error:

        print(
            "Chat endpoint error:",
            error
        )

        return {

            "success": False,

            "answer": (
                "I was unable to process that "
                "ARGO data question."
            ),

            "parameters": {
                "question": request.question,
            },

            "statistics": {},

            "error": str(error),
        }


# ============================================================
# FLOAT LOCATIONS
# ============================================================

@app.get("/floats")
def get_floats():

    if argo_df is None:

        return {

            "success": False,

            "count": 0,

            "floats": [],

            "error": (
                "ARGO dataset could not be loaded."
            ),
        }

    try:

        # ----------------------------------------------------
        # Required columns
        # ----------------------------------------------------

        required_columns = [
            "float_id",
            "latitude",
            "longitude",
        ]

        missing_columns = [

            column

            for column in required_columns

            if column not in argo_df.columns

        ]

        if missing_columns:

            return {

                "success": False,

                "count": 0,

                "floats": [],

                "error": (
                    "Missing dataset columns: "
                    +
                    ", ".join(
                        missing_columns
                    )
                ),
            }

        # ----------------------------------------------------
        # Select float information
        # ----------------------------------------------------

        floats = argo_df[
            required_columns
        ].copy()

        # ----------------------------------------------------
        # Remove invalid rows
        # ----------------------------------------------------

        floats = floats.dropna(
            subset=[
                "float_id",
                "latitude",
                "longitude",
            ]
        )

        # ----------------------------------------------------
        # Validate geographic coordinates
        # ----------------------------------------------------

        floats = floats[
            (floats["latitude"] >= -90)
            &
            (floats["latitude"] <= 90)
            &
            (floats["longitude"] >= -180)
            &
            (floats["longitude"] <= 180)
        ]

        # ----------------------------------------------------
        # One location per float
        # ----------------------------------------------------

        floats = floats.drop_duplicates(
            subset=["float_id"]
        )

        # ----------------------------------------------------
        # Convert to API records
        # ----------------------------------------------------

        result = []

        for _, row in floats.iterrows():

            result.append({

                "float_id": str(
                    row["float_id"]
                ),

                "latitude": float(
                    row["latitude"]
                ),

                "longitude": float(
                    row["longitude"]
                ),

            })

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return {

            "success": True,

            "count": len(result),

            "floats": result,

        }

    except Exception as error:

        print(
            "Float endpoint error:",
            error
        )

        return {

            "success": False,

            "count": 0,

            "floats": [],

            "error": str(error),

        }


# ============================================================
# 3D VISUALIZATION DATA
# ============================================================

@app.get("/visualization")
def visualization_data(
    max_points: int = 6000
):

    if argo_df is None:

        return {

            "success": False,

            "count": 0,

            "total_available": 0,

            "points": [],

            "error": (
                "ARGO dataset could not be loaded."
            ),
        }

    try:

        # ----------------------------------------------------
        # Protect the API from unreasonable values
        # ----------------------------------------------------

        max_points = max(
            100,
            min(
                int(max_points),
                20000,
            ),
        )

        # ----------------------------------------------------
        # Required columns
        # ----------------------------------------------------

        required_columns = [

            "latitude",
            "longitude",
            "pressure",
            "temperature",
            "salinity",
            "float_id",
            "cycle_number",
            "date",

        ]

        missing_columns = [

            column

            for column in required_columns

            if column not in argo_df.columns

        ]

        if missing_columns:

            return {

                "success": False,

                "count": 0,

                "total_available": 0,

                "points": [],

                "error": (
                    "Missing dataset columns: "
                    +
                    ", ".join(
                        missing_columns
                    )
                ),
            }

        # ----------------------------------------------------
        # Copy required data
        # ----------------------------------------------------

        data = argo_df[
            required_columns
        ].copy()

        # ----------------------------------------------------
        # Remove missing geographic/measurement values
        # ----------------------------------------------------

        data = data.dropna(
            subset=[
                "latitude",
                "longitude",
                "pressure",
                "temperature",
            ]
        )

        # ----------------------------------------------------
        # Geographic validation
        # ----------------------------------------------------

        data = data[
            (data["latitude"] >= -90)
            &
            (data["latitude"] <= 90)
            &
            (data["longitude"] >= -180)
            &
            (data["longitude"] <= 180)
        ]

        # ----------------------------------------------------
        # Pressure validation
        #
        # ARGO pressure represented in dbar.
        # Prototype visualizes 0–2000 dbar.
        # ----------------------------------------------------

        data = data[
            (data["pressure"] >= 0)
            &
            (data["pressure"] <= 2000)
        ]

        # ----------------------------------------------------
        # Temperature validation
        # ----------------------------------------------------

        data = data[
            data["temperature"].between(
                -5,
                40,
            )
        ]

        # ----------------------------------------------------
        # Total valid measurements
        # ----------------------------------------------------

        total_available = len(data)

        # ----------------------------------------------------
        # No valid data
        # ----------------------------------------------------

        if total_available == 0:

            return {

                "success": False,

                "count": 0,

                "total_available": 0,

                "points": [],

                "error": (
                    "No valid ARGO measurements "
                    "are available for visualization."
                ),
            }

        # ----------------------------------------------------
        # Limit points for browser performance
        # ----------------------------------------------------

        if len(data) > max_points:

            data = data.sample(
                n=max_points,
                random_state=42,
            )

        # ----------------------------------------------------
        # Stable ordering
        # ----------------------------------------------------

        data = data.sort_values(
            by=[
                "pressure",
                "latitude",
                "longitude",
            ]
        )

        # ----------------------------------------------------
        # Convert records
        # ----------------------------------------------------

        records = data.to_dict(
            orient="records"
        )

        points = []

        for point in records:

            # ------------------------------------------------
            # Salinity
            # ------------------------------------------------

            if pd.notna(
                point["salinity"]
            ):

                salinity = float(
                    point["salinity"]
                )

            else:

                salinity = None

            # ------------------------------------------------
            # Cycle number
            # ------------------------------------------------

            if pd.notna(
                point["cycle_number"]
            ):

                cycle_number = int(
                    point["cycle_number"]
                )

            else:

                cycle_number = None

            # ------------------------------------------------
            # Date
            # ------------------------------------------------

            if pd.notna(
                point["date"]
            ):

                date = str(
                    point["date"]
                )

            else:

                date = None

            # ------------------------------------------------
            # Point
            # ------------------------------------------------

            points.append({

                "latitude": float(
                    point["latitude"]
                ),

                "longitude": float(
                    point["longitude"]
                ),

                "pressure": float(
                    point["pressure"]
                ),

                "temperature": float(
                    point["temperature"]
                ),

                "salinity": salinity,

                "float_id": str(
                    point["float_id"]
                ),

                "cycle_number": cycle_number,

                "date": date,

            })

        # ----------------------------------------------------
        # Visualization response
        # ----------------------------------------------------

        return {

            "success": True,

            "count": len(points),

            "total_available": total_available,

            "visualization": {

                "x": "longitude",

                "x_unit": "degrees",

                "y": "latitude",

                "y_unit": "degrees",

                "z": "pressure",

                "z_unit": "dbar",

                "color": "temperature",

                "color_unit": "°C",

            },

            "points": points,

        }

    except Exception as error:

        print(
            "3D visualization endpoint error:",
            error
        )

        return {

            "success": False,

            "count": 0,

            "total_available": 0,

            "points": [],

            "error": str(error),

        }


# ============================================================
# SERVER STARTUP INFORMATION
# ============================================================

@app.on_event("startup")
def startup_event():

    print("=" * 60)
    print("FLOATCHAT API STARTED")
    print("API: http://127.0.0.1:8001")
    print("DOCS: http://127.0.0.1:8001/docs")

    if argo_df is not None:

        print(
            f"ARGO rows: {len(argo_df):,}"
        )

        if "float_id" in argo_df.columns:

            print(
                "ARGO floats: "
                f"{argo_df['float_id'].nunique():,}"
            )

    else:

        print(
            "ARGO dataset: NOT AVAILABLE"
        )

    print("=" * 60)