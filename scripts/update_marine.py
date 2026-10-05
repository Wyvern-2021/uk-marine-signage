"""
Update the signage data from the official Met Office
marine observation pages.

The eight locations are deliberately referenced by
their official Met Office observation-page IDs.

This avoids guessing station names or trying to infer
station identity from latitude/longitude in the raw
CSV dataset.
"""

from __future__ import annotations

import io
import json
import math
import re
import sys
import urllib.request
from datetime import datetime, timezone

import pandas as pd


OUTPUT_FILE = "data/marine.json"


MET_OFFICE_BASE = (
    "https://weather.metoffice.gov.uk/"
    "specialist-forecasts/coast-and-sea/"
    "observations/"
)


# ----------------------------------------------------
# THE TWO SIGNAGE PAGES
# ----------------------------------------------------

PAGES = {

    "page1": [
        "Channel",
        "Seven Stones",
        "Sandettie",
        "M5",
    ],

    "page2": [
        "Donna Nook",
        "Lerwick",
        "K7",
        "Malin Head",
    ],

}


# ----------------------------------------------------
# Official Met Office observation-page IDs
#
# These were checked against the current Met Office
# marine observation service.
# ----------------------------------------------------

STATIONS = {

    "Channel": {
        "page_id": "162103",
        "type": "Buoy",
    },

    "Seven Stones": {
        "page_id": "162107",
        "type": "Light Vessel",
    },

    "Sandettie": {
        "page_id": "162304",
        "type": "Light Vessel",
    },

    "M5": {
        "page_id": "162094",
        "type": "Buoy",
    },

    "Donna Nook": {
        "page_id": "3385",
        "type": "Land",
    },

    "Lerwick": {
        "page_id": "3005",
        "type": "Land",
    },

    "K7": {
        "page_id": "164046",
        "type": "Buoy",
    },

    "Malin Head": {
        "page_id": "3980",
        "type": "Land",
    },

}


USER_AGENT = (
    "UK-Marine-Signage/1.0 "
    "(GitHub Actions)"
)


# ----------------------------------------------------
# HTTP
# ----------------------------------------------------

def fetch_page(url: str) -> str:

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=60,
    ) as response:

        raw = response.read()


    return raw.decode(
        "utf-8",
        errors="replace",
    )


# ----------------------------------------------------
# Helpers
# ----------------------------------------------------

def is_number(value) -> bool:

    try:

        number = float(value)

        return math.isfinite(number)

    except (
        ValueError,
        TypeError,
    ):

        return False


def clean_text(value) -> str:

    if value is None:

        return ""

    return str(value).strip()


def numeric_from_text(value):

    if value is None:

        return None


    text = clean_text(value)


    if not text:

        return None


    if text in {
        "-",
        "–",
        "—",
        "No data",
        "- No data",
    }:

        return None


    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text,
    )


    if not match:

        return None


    try:

        number = float(
            match.group(0)
        )

    except ValueError:

        return None


    if not math.isfinite(
        number
    ):

        return None


    return number


# ----------------------------------------------------
# Parse wind
# ----------------------------------------------------

def parse_wind(value):

    text = clean_text(
        value
    )


    if not text:

        return (
            None,
            None,
        )


    if "No data" in text:

        return (
            None,
            None,
        )


    # Examples:
    #
    #   SW 12
    #   WSW 18
    #   N 4
    #
    match = re.search(
        r"^\s*([A-Za-z]+)"
        r"\s+(-?\d+(?:\.\d+)?)",
        text,
    )


    if not match:

        return (
            None,
            None,
        )


    direction = (
        match.group(1)
        .upper()
    )


    speed = float(
        match.group(2)
    )


    return (
        speed,
        direction,
    )


# ----------------------------------------------------
# Find a row in a Met Office table
# ----------------------------------------------------

def find_row(
    table,
    possible_names,
):

    if table.empty:

        return None


    first_column = (
        table.iloc[:, 0]
        .astype(str)
        .str.strip()
    )


    for wanted in possible_names:

        wanted_lower = (
            wanted.lower()
        )


        for index, label in (
            first_column.items()
        ):

            if (
                label.lower()
                == wanted_lower
            ):

                return table.loc[
                    index
                ]


    # More tolerant matching.

    for wanted in possible_names:

        wanted_lower = (
            wanted.lower()
        )


        for index, label in (
            first_column.items()
        ):

            if wanted_lower in (
                label.lower()
            ):

                return table.loc[
                    index
                ]


    return None


# ----------------------------------------------------
# Extract all hourly values from a row
# ----------------------------------------------------

def row_values(
    table,
    possible_names,
):

    row = find_row(
        table,
        possible_names,
    )


    if row is None:

        return []


    values = []


    for column in table.columns:

        # The first column is the row label.

        if column == table.columns[0]:

            continue


        value = clean_text(
            row[column]
        )


        if value:

            values.append(
                value
            )


    return values


# ----------------------------------------------------
# Find the most recent useful table
# ----------------------------------------------------

def find_latest_table(
    tables,
):

    candidates = []


    for table in tables:

        if table.empty:

            continue


        wind = find_row(
            table,
            [
                "Wind direction and speed (knots)",
                "Wind Direction and speed",
            ],
        )


        pressure = find_row(
            table,
            [
                "Pressure (hPa)",
                "Pressure",
            ],
        )


        if (
            wind is not None
            and pressure is not None
        ):

            candidates.append(
                table
            )


    if not candidates:

        return None


    # The Met Office page presents the
    # days chronologically. The final
    # suitable table is therefore the
    # current/latest one.

    return candidates[-1]


# ----------------------------------------------------
# Extract date from page
# ----------------------------------------------------

def extract_dates(
    html,
):

    text = re.sub(
        r"<[^>]+>",
        " ",
        html,
    )


    text = re.sub(
        r"\s+",
        " ",
        text,
    )


    pattern = (
        r"\b"
        r"(?:Monday|Tuesday|Wednesday|"
        r"Thursday|Friday|Saturday|Sunday)"
        r"\s+"
        r"\("
        r"(\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"\s+\d{4})"
        r"\)"
    )


    matches = re.findall(
        pattern,
        text,
    )


    dates = []


    for value in matches:

        try:

            dates.append(
                datetime.strptime(
                    value,
                    "%d %B %Y",
                ).date()
            )

        except ValueError:

            pass


    if not dates:

        return None


    return max(
        dates
    )


# ----------------------------------------------------
# Extract station data
# ----------------------------------------------------

def extract_station(
    name,
    configuration,
):

    page_id = configuration[
        "page_id"
    ]


    url = (
        MET_OFFICE_BASE
        + page_id
    )


    print(
        f"\nFetching {name}"
    )

    print(
        url
    )


    html = fetch_page(
        url
    )


    # If the Met Office explicitly says
    # that no recent observation exists,
    # return a valid station with null data.

    if (
        "No recent observations available"
        in html
    ):

        print(
            f"{name}: no recent "
            "observations"
        )


        return {

            "name": name,

            "type":
                configuration["type"],

            "source_url": url,

            "observation_time": None,

            "wind_speed_knots": None,

            "wind_direction": None,

            "visibility_nm": None,

            "wave_height_m": None,

            "sea_temperature_c": None,

            "pressure_hpa": None,

            "pressure_trend": "unknown",

            "pressure_change_hpa": None,

        }


    # Pandas/lxml converts the HTML tables
    # used by the Met Office page into
    # DataFrames.

    tables = pd.read_html(
        io.StringIO(html)
    )


    table = find_latest_table(
        tables
    )


    if table is None:

        raise RuntimeError(
            f"Could not find a usable "
            f"observation table for "
            f"{name}."
        )


    # ----------------------------------------------
    # Observation time
    # ----------------------------------------------

    date_value = extract_dates(
        html
    )


    time_columns = []


    for column in table.columns:

        column_text = clean_text(
            column
        )


        if re.match(
            r"^\d{2}:\d{2}$",
            column_text,
        ):

            time_columns.append(
                column
            )


    if not time_columns:

        raise RuntimeError(
            f"Could not identify observation "
            f"times for {name}."
        )


    latest_column = (
        time_columns[-1]
    )


    latest_time = clean_text(
        latest_column
    )


    observation_time = None


    if date_value is not None:

        observation_time = (
            f"{date_value.isoformat()}"
            f"T{latest_time}:00+00:00"
        )


    # ----------------------------------------------
    # Wind
    # ----------------------------------------------

    wind_row = find_row(
        table,
        [
            "Wind direction and speed (knots)",
            "Wind Direction and speed",
        ],
    )


    wind_speed = None

    wind_direction = None


    if wind_row is not None:

        wind_speed, wind_direction = (
            parse_wind(
                wind_row[
                    latest_column
                ]
            )
        )


    # ----------------------------------------------
    # Visibility
    # ----------------------------------------------

    visibility_values = row_values(
        table,
        [
            "Visibility (NM)",
            "Visibility",
        ],
    )


    visibility = None


    if visibility_values:

        latest_visibility = (
            visibility_values[-1]
        )


        visibility = numeric_from_text(
            latest_visibility
        )


    # ----------------------------------------------
    # Pressure
    # ----------------------------------------------

    pressure_values = row_values(
        table,
        [
            "Pressure (hPa)",
            "Pressure",
        ],
    )


    pressure = None

    pressure_history = []


    for value in pressure_values:

        number = numeric_from_text(
            value
        )


        if number is not None:

            pressure_history.append(
                number
            )


    if pressure_history:

        pressure = (
            pressure_history[-1]
        )


    # ----------------------------------------------
    # Pressure trend
    #
    # Compare latest pressure with the
    # pressure approximately three hours
    # earlier.
    # ----------------------------------------------

    pressure_change = None

    pressure_trend = "unknown"


    if len(
        pressure_history
    ) >= 4:

        earlier = (
            pressure_history[-4]
        )

        pressure_change = round(
            pressure
            - earlier,
            1,
        )


        if pressure_change > 0.5:

            pressure_trend = "rising"

        elif pressure_change < -0.5:

            pressure_trend = "falling"

        else:

            pressure_trend = "steady"


    # ----------------------------------------------
    # Sea temperature
    # ----------------------------------------------

    sea_values = row_values(
        table,
        [
            "Sea temperature (°C)",
            "Sea Temperature",
        ],
    )


    sea_temperature = None


    if sea_values:

        sea_temperature = (
            numeric_from_text(
                sea_values[-1]
            )
        )


    # ----------------------------------------------
    # Wave height
    # ----------------------------------------------

    wave_values = row_values(
        table,
        [
            "Wave height (metres)",
            "Wave Height",
        ],
    )


    wave_height = None


    if wave_values:

        wave_height = (
            numeric_from_text(
                wave_values[-1]
            )
        )


    result = {

        "name": name,

        "type":
            configuration["type"],

        "source_url": url,

        "observation_time":
            observation_time,

        "wind_speed_knots":
            wind_speed,

        "wind_direction":
            wind_direction,

        "visibility_nm":
            visibility,

        "wave_height_m":
            wave_height,

        "sea_temperature_c":
            sea_temperature,

        "pressure_hpa":
            pressure,

        "pressure_trend":
            pressure_trend,

        "pressure_change_hpa":
            pressure_change,

    }


    print(
        f"{name}: "
        f"{wind_direction or '--'} "
        f"{wind_speed if wind_speed is not None else '--'} kt, "
        f"{visibility if visibility is not None else '--'} NM, "
        f"{wave_height if wave_height is not None else '--'} m, "
        f"{sea_temperature if sea_temperature is not None else '--'} °C, "
        f"{pressure if pressure is not None else '--'} hPa, "
        f"{pressure_trend}"
    )


    return result


# ----------------------------------------------------
# Validate configuration
# ----------------------------------------------------

def validate_configuration():

    expected = (
        PAGES["page1"]
        + PAGES["page2"]
    )


    if len(expected) != 8:

        raise RuntimeError(
            "There must be exactly "
            "eight stations."
        )


    if len(set(expected)) != 8:

        raise RuntimeError(
            "Duplicate station names "
            "were found."
        )


    for station in expected:

        if station not in STATIONS:

            raise RuntimeError(
                f"Station {station} "
                f"is missing from STATIONS."
            )


# ----------------------------------------------------
# Main
# ----------------------------------------------------

def main():

    validate_configuration()


    stations = {}


    for name in (
        PAGES["page1"]
        + PAGES["page2"]
    ):

        try:

            stations[name] = (
                extract_station(
                    name,
                    STATIONS[name],
                )
            )

        except Exception as error:

            print(
                f"\nERROR processing "
                f"{name}: {error}",
                file=sys.stderr,
            )

            raise


    output = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source":
            "Met Office Marine Observations",

        "pages": {

            "page1":
                PAGES["page1"],

            "page2":
                PAGES["page2"],

        },

        "stations":
            stations,

    }


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )


    print(
        "\n========================================"
    )

    print(
        "Marine data update complete"
    )

    print(
        "========================================"
    )

    print(
        f"Written: {OUTPUT_FILE}"
    )

    print(
        "Page 1:"
    )

    for station in PAGES[
        "page1"
    ]:

        print(
            f"  - {station}"
        )


    print(
        "Page 2:"
    )

    for station in PAGES[
        "page2"
    ]:

        print(
            f"  - {station}"
        )


if __name__ == "__main__":

    main()
