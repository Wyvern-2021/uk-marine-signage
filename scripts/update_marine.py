from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = Path("data/marine.json")

USER_AGENT = (
    "UK-Marine-Signage/1.0 "
    "(GitHub Actions; public Met Office observations)"
)

REQUEST_TIMEOUT = 45


# ============================================================
# REQUESTED STATIONS
# ============================================================

PAGE_1 = [
    {
        "id": "M5",
        "name": "M5",
        "descriptor": "Celtic Sea",
        "url": (
            "https://weather.metoffice.gov.uk/"
            "specialist-forecasts/coast-and-sea/"
            "observations/162094"
        ),
    },
    {
        "id": "SEVEN_STONES",
        "name": "Seven Stones",
        "descriptor": "Land's End",
        "url": (
            "https://weather.metoffice.gov.uk/"
            "specialist-forecasts/coast-and-sea/"
            "observations/162107"
        ),
    },
    {
        "id": "CHANNEL",
        "name": "Channel",
        "descriptor": "English Channel",
        "url": (
            "https://weather.metoffice.gov.uk/"
            "specialist-forecasts/coast-and-sea/"
            "observations/162103"
        ),
    },
    {
        "id": "SANDETTIE",
        "name": "Sandettie",
        "descriptor": "East Channel",
        "url": (
            "https://weather.metoffice.gov.uk/"
            "specialist-forecasts/coast-and-sea/"
            "observations/162304"
        ),
    },
]


PAGE_2 = [
    {
        "id": "DONNA_NOOK",
        "name": "Donna Nook",
        "descriptor": "East Coast",
        "url": (
            "https://weather.metoffice.gov.uk/"
            "specialist-forecasts/coast-and-sea/"
            "observations/3385"
        ),
    },
    {
        "id": "BOULMER",
        "name": "Boulmer",
        "descriptor": "NE Coast, England",
        "url": (
            "https://weather.metoffice.gov.uk/"
            "specialist-forecasts/coast-and-sea/"
            "observations/3240"
        ),
    },
    {
        "id": "LERWICK",
        "name": "Lerwick",
        "descriptor": "Shetland",
        "url": (
            "https://weather.metoffice.gov.uk/"
            "specialist-forecasts/coast-and-sea/"
            "observations/3005"
        ),
    },
    {
        "id": "K7",
        "name": "K7",
        "descriptor": "North Atlantic",
        "url": (
            "https://weather.metoffice.gov.uk/"
            "specialist-forecasts/coast-and-sea/"
            "observations/164046"
        ),
    },
]


ALL_STATIONS = PAGE_1 + PAGE_2


# ============================================================
# HELPERS
# ============================================================

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_number(value: str):
    if value is None:
        return None

    text = clean_text(value)

    if not text:
        return None

    if "no data" in text.lower():
        return None

    match = re.search(
        r"[-+]?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_wind(value: str):
    """
    Examples:
        SW 14
        WSW 8
        S 3
        - No data
    """

    text = clean_text(value)

    if not text or "no data" in text.lower():
        return None, None

    match = re.match(
        r"^([A-Z]{1,3})\s+"
        r"([-+]?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None, None

    direction = match.group(1).upper()

    try:
        speed = float(match.group(2))
    except ValueError:
        speed = None

    return direction, speed


def parse_day_heading(text: str):
    """
    Converts:

        Monday (5 October 2026)

    into a date object.
    """

    text = clean_text(text)

    match = re.match(
        r"^[A-Za-z]+\s+\("
        r"(\d{1,2})\s+"
        r"([A-Za-z]+)\s+"
        r"(\d{4})"
        r"\)$",
        text,
    )

    if not match:
        return None

    day = int(match.group(1))
    month = match.group(2)
    year = int(match.group(3))

    try:
        return datetime.strptime(
            f"{day} {month} {year}",
            "%d %B %Y",
        ).date()
    except ValueError:
        return None


def metric_key(label: str):
    """
    Convert Met Office row labels into our JSON keys.
    """

    text = clean_text(label).lower()

    if (
        "wind direction and speed" in text
        or "wind direction" in text
    ):
        return "wind"

    if text.startswith("visibility"):
        return "visibility_nm"

    if text.startswith("pressure"):
        return "pressure_hpa"

    if "sea temperature" in text:
        return "sea_temperature_c"

    if "wave height" in text:
        return "wave_height_m"

    return None


# ============================================================
# SCRAPE ONE MET OFFICE STATION PAGE
# ============================================================

def scrape_station(station):
    print()
    print("=" * 60)
    print(
        f"Processing {station['name']} "
        f"({station['descriptor']})"
    )
    print("=" * 60)

    response = requests.get(
        station["url"],
        headers={
            "User-Agent": USER_AGENT
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    # --------------------------------------------------------
    # Confirm the page really is the requested station.
    # --------------------------------------------------------

    page_text = clean_text(
        soup.get_text(" ", strip=True)
    )

    if station["name"].lower() not in page_text.lower():

        raise RuntimeError(
            "The returned Met Office page does not "
            f"appear to be the expected station: "
            f"{station['name']}"
        )

    # --------------------------------------------------------
    # Find daily observation tables.
    # --------------------------------------------------------

    observations = {}

    current_date = None

    for heading in soup.find_all(
        ["h2", "h3"]
    ):

        heading_text = clean_text(
            heading.get_text(
                " ",
                strip=True,
            )
        )

        parsed_date = parse_day_heading(
            heading_text
        )

        if parsed_date is not None:
            current_date = parsed_date

        if current_date is None:
            continue

        table = heading.find_next(
            "table"
        )

        if table is None:
            continue

        # Make sure the table belongs to
        # this date section.
        if table.find_previous(
            ["h2", "h3"]
        ) != heading:
            continue

        rows = table.find_all("tr")

        if not rows:
            continue

        # ----------------------------------------------------
        # Find the time header.
        # ----------------------------------------------------

        header_cells = rows[0].find_all(
            ["th", "td"]
        )

        if not header_cells:
            continue

        times = []

        for cell in header_cells[1:]:

            time_text = clean_text(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )

            if re.fullmatch(
                r"\d{2}:\d{2}",
                time_text,
            ):
                times.append(
                    time_text
                )
            else:
                times.append(None)

        if not any(times):
            continue

        # ----------------------------------------------------
        # Read each measurement row.
        # ----------------------------------------------------

        for row in rows[1:]:

            cells = row.find_all(
                ["th", "td"]
            )

            if len(cells) < 2:
                continue

            label = clean_text(
                cells[0].get_text(
                    " ",
                    strip=True,
                )
            )

            key = metric_key(
                label
            )

            if key is None:
                continue

            values = [
                clean_text(
                    cell.get_text(
                        " ",
                        strip=True,
                    )
                )
                for cell in cells[1:]
            ]

            for index, time_text in enumerate(
                times
            ):

                if time_text is None:
                    continue

                if index >= len(values):
                    continue

                value = values[index]

                try:
                    hour = int(
                        time_text[:2]
                    )

                    minute = int(
                        time_text[3:5]
                    )

                    timestamp = datetime(
                        current_date.year,
                        current_date.month,
                        current_date.day,
                        hour,
                        minute,
                        tzinfo=timezone.utc,
                    )

                except ValueError:
                    continue

                iso_time = timestamp.isoformat()

                if iso_time not in observations:

                    observations[
                        iso_time
                    ] = {
                        "timestamp": iso_time
                    }

                if key == "wind":

                    direction, speed = (
                        parse_wind(value)
                    )

                    observations[
                        iso_time
                    ][
                        "wind_direction"
                    ] = direction

                    observations[
                        iso_time
                    ][
                        "wind_speed_knots"
                    ] = speed

                elif key == "visibility_nm":

                    observations[
                        iso_time
                    ][
                        "visibility_nm"
                    ] = parse_number(
                        value
                    )

                elif key == "pressure_hpa":

                    observations[
                        iso_time
                    ][
                        "pressure_hpa"
                    ] = parse_number(
                        value
                    )

                elif key == "sea_temperature_c":

                    observations[
                        iso_time
                    ][
                        "sea_temperature_c"
                    ] = parse_number(
                        value
                    )

                elif key == "wave_height_m":

                    observations[
                        iso_time
                    ][
                        "wave_height_m"
                    ] = parse_number(
                        value
                    )

    # --------------------------------------------------------
    # Remove completely empty observations.
    # --------------------------------------------------------

    observations = {
        timestamp: record
        for timestamp, record
        in observations.items()
        if any(
            value is not None
            for key, value in record.items()
            if key != "timestamp"
        )
    }

    if not observations:

        print(
            "No observations were available."
        )

        return {
            "name": station["name"],
            "descriptor": station["descriptor"],
            "source_url": station["url"],
            "status": "no_current_data",
            "observation_time": None,
            "wind_speed_knots": None,
            "wind_direction": None,
            "visibility_nm": None,
            "wave_height_m": None,
            "sea_temperature_c": None,
            "pressure_hpa": None,
            "pressure_trend": "unknown",
        }

    # --------------------------------------------------------
    # Sort observations chronologically.
    # --------------------------------------------------------

    ordered = sorted(
        observations.values(),
        key=lambda record: record[
            "timestamp"
        ],
    )

    latest = ordered[-1]

    latest_timestamp = latest[
        "timestamp"
    ]

    # --------------------------------------------------------
    # Pressure trend.
    #
    # Compare the latest pressure with the most
    # recent pressure approximately 3 hours earlier.
    #
    # >= 1 hPa  = rising
    # <= -1 hPa = falling
    # otherwise = steady
    # --------------------------------------------------------

    pressure_history = [
        record
        for record in ordered
        if record.get(
            "pressure_hpa"
        ) is not None
    ]

    pressure_trend = "unknown"
    pressure_change = None

    if len(
        pressure_history
    ) >= 2:

        latest_pressure = (
            pressure_history[-1]
            .get("pressure_hpa")
        )

        comparison = None

        for candidate in reversed(
            pressure_history[:-1]
        ):

            try:
                latest_dt = datetime.fromisoformat(
                    latest_timestamp
                )

                candidate_dt = datetime.fromisoformat(
                    candidate["timestamp"]
                )

                hours = (
                    latest_dt - candidate_dt
                ).total_seconds() / 3600

            except ValueError:
                continue

            if hours >= 2.5:

                comparison = candidate

                break

        if comparison is None:

            comparison = (
                pressure_history[-2]
            )

        old_pressure = comparison.get(
            "pressure_hpa"
        )

        if (
            latest_pressure is not None
            and old_pressure is not None
        ):

            pressure_change = round(
                latest_pressure
                - old_pressure,
                1,
            )

            if pressure_change >= 1.0:

                pressure_trend = "rising"

            elif pressure_change <= -1.0:

                pressure_trend = "falling"

            else:

                pressure_trend = "steady"

    result = {
        "name": station["name"],
        "descriptor": station["descriptor"],
        "source_url": station["url"],
        "status": "live",
        "observation_time": latest_timestamp,
        "wind_speed_knots": latest.get(
            "wind_speed_knots"
        ),
        "wind_direction": latest.get(
            "wind_direction"
        ),
        "visibility_nm": latest.get(
            "visibility_nm"
        ),
        "wave_height_m": latest.get(
            "wave_height_m"
        ),
        "sea_temperature_c": latest.get(
            "sea_temperature_c"
        ),
        "pressure_hpa": latest.get(
            "pressure_hpa"
        ),
        "pressure_trend": pressure_trend,
        "pressure_change_hpa": pressure_change,
    }

    print(
        "Latest observation:",
        latest_timestamp,
    )

    print(
        "Wind:",
        result["wind_direction"],
        result["wind_speed_knots"],
        "knots",
    )

    print(
        "Visibility:",
        result["visibility_nm"],
        "NM",
    )

    print(
        "Wave height:",
        result["wave_height_m"],
        "m",
    )

    print(
        "Sea temperature:",
        result["sea_temperature_c"],
        "C",
    )

    print(
        "Pressure:",
        result["pressure_hpa"],
        "hPa",
        result["pressure_trend"],
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    stations = {}

    failures = []

    for station in ALL_STATIONS:

        try:

            stations[
                station["id"]
            ] = scrape_station(
                station
            )

        except Exception as error:

            print(
                f"ERROR processing "
                f"{station['name']}: {error}",
                file=sys.stderr,
            )

            failures.append(
                station["name"]
            )

            stations[
                station["id"]
            ] = {
                "name": station["name"],
                "descriptor": station[
                    "descriptor"
                ],
                "source_url": station[
                    "url"
                ],
                "status": "error",
                "observation_time": None,
                "wind_speed_knots": None,
                "wind_direction": None,
                "visibility_nm": None,
                "wave_height_m": None,
                "sea_temperature_c": None,
                "pressure_hpa": None,
                "pressure_trend": "unknown",
                "pressure_change_hpa": None,
                "error": str(error),
            }

    output = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "source": (
            "Met Office UK Marine Observations"
        ),

        "source_description": (
            "Official Met Office observation pages"
        ),

        "pages": {
            "page1": [
                station["id"]
                for station in PAGE_1
            ],
            "page2": [
                station["id"]
                for station in PAGE_2
            ],
        },

        "stations": stations,
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 60)
    print(
        f"Written: {OUTPUT_FILE}"
    )
    print("=" * 60)

    if failures:

        print(
            "WARNING: failures occurred for:",
            ", ".join(failures),
        )

        # Do not fail the entire workflow merely
        # because one Met Office station has no
        # current observations.
        #
        # The generated JSON records the station
        # as unavailable.

    else:

        print(
            "All eight requested stations "
            "were processed successfully."
        )


if __name__ == "__main__":
    main()
