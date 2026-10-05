import csv
import json
import math
import os
from datetime import datetime, timezone


SOURCE_DIRECTORY = "data/source"

OUTPUT_FILE = "data/marine.json"


STATIONS = {

    "K1": "K1",
    "K2": "K2",
    "K7": "K7",
    "Channel": "Channel",

    "K4": "K4",
    "M2": "M2",
    "M4": "M4",
    "M5": "M5"

}


# -------------------------------------------------
# Candidate parameter names
#
# The Met Office dataset can contain several
# related observation fields. We select the
# preferred marine observation first.
# -------------------------------------------------

FIELDS = {

    "wind_speed_knots": [

        "wind_speed_1_hour_20_second_mean",
        "wind_speed",
        "wind_speed_at_10m"

    ],

    "wind_direction": [

        "wind_direction_1_hour_20_second_mean",
        "wind_direction",
        "wind_from_direction"

    ],

    "visibility_nm": [

        "visibility",
        "visibility_1_hour_20_second_mean"

    ],

    "wave_height_m": [

        "significant_wave_height",
        "wave_height",
        "sea_surface_wave_significant_height"

    ],

    "sea_temperature_c": [

        "sea_temperature",
        "sea_surface_temperature",
        "sea_water_temperature"

    ],

    "pressure_hpa": [

        "air_pressure_near_surface_1_hour_20_second_mean",
        "air_pressure_near_surface",
        "air_pressure"

    ]

}


# -------------------------------------------------
# Utility functions
# -------------------------------------------------

def clean(value):

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def number(value):

    value = clean(value)

    if value is None:
        return None

    try:

        result = float(value)

        if math.isnan(result):
            return None

        return result

    except (ValueError, TypeError):

        return None


def parse_time(value):

    value = clean(value)

    if not value:
        return None

    try:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

    except ValueError:

        return None


def find_field(
    row,
    candidates
):

    for field in candidates:

        if field in row:

            value =
                clean(row[field])


            if value is not None:

                return value

    return None


# -------------------------------------------------
# Station matching
# -------------------------------------------------

def normalise_station_name(
    value
):

    if not value:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def station_match(
    actual,
    requested
):

    actual_normalised =
        normalise_station_name(
            actual
        )


    requested_normalised =
        normalise_station_name(
            requested
        )


    if (
        actual_normalised ==
        requested_normalised
    ):
        return True


    return (
        actual_normalised.startswith(
            requested_normalised + " "
        )
        or
        requested_normalised in
        actual_normalised
    )


# -------------------------------------------------
# Extract station name
# -------------------------------------------------

def get_station_name(
    row
):

    candidates = [

        "station_name",
        "station",
        "name",
        "location",
        "site_name",
        "platform"

    ]


    for field in candidates:

        if field in row:

            value =
                clean(row[field])


            if value:

                return value


    return None


# -------------------------------------------------
# Read every CSV file
# -------------------------------------------------

def read_rows():

    rows = []


    if not os.path.isdir(
        SOURCE_DIRECTORY
    ):

        raise RuntimeError(
            f"Missing directory: "
            f"{SOURCE_DIRECTORY}"
        )


    for root, _, files in os.walk(
        SOURCE_DIRECTORY
    ):

        for filename in files:

            if not filename.lower().endswith(
                ".csv"
            ):
                continue


            path =
                os.path.join(
                    root,
                    filename
                )


            print(
                f"Reading {path}"
            )


            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8-sig",
                    newline=""
                ) as file:

                    reader =
                        csv.DictReader(
                            file,
                            delimiter="|"
                        )


                    for row in reader:

                        rows.append(
                            row
                        )


            except Exception as error:

                print(
                    f"WARNING: "
                    f"Could not read "
                    f"{path}: "
                    f"{error}"
                )


    return rows


# -------------------------------------------------
# Build station history
# -------------------------------------------------

def build_history(rows):

    history = {

        station: []

        for station
        in STATIONS

    }


    for row in rows:

        station_name =
            get_station_name(
                row
            )


        if not station_name:
            continue


        matched = None


        for requested
        in STATIONS:

            if station_match(
                station_name,
                requested
            ):

                matched =
                    requested

                break


        if matched is None:
            continue


        timestamp =
            parse_time(
                row.get(
                    "timestep"
                )
            )


        if timestamp is None:
            continue


        history[
            matched
        ].append(
            (
                timestamp,
                row
            )
        )


    for station
    in history:

        history[station].sort(
            key=lambda item:
                item[0]
        )


    return history


# -------------------------------------------------
# Select nearest historical pressure
# -------------------------------------------------

def find_pressure_before(
    history,
    target_time
):

    best = None


    for timestamp, row
    in history:

        if timestamp > target_time:
            break


        pressure =
            number(
                find_field(
                    row,
                    FIELDS[
                        "pressure_hpa"
                    ]
                )
            )


        if pressure is None:
            continue


        best = (
            timestamp,
            pressure
        )


    return best


# -------------------------------------------------
# Calculate pressure trend
# -------------------------------------------------

def calculate_pressure_trend(
    station_history,
    latest_time,
    latest_pressure
):

    if (
        latest_pressure is None
        or latest_time is None
    ):

        return (
            "unknown",
            None
        )


    target_time =
        latest_time.replace(
            minute=0,
            second=0,
            microsecond=0
        )


    # Three-hour trend.

    target_time = (
        target_time
        -
        __import__(
            "datetime"
        ).timedelta(
            hours=3
        )
    )


    previous =
        find_pressure_before(
            station_history,
            target_time
        )


    if previous is None:

        return (
            "unknown",
            None
        )


    previous_time,
    previous_pressure = previous


    change = (
        latest_pressure
        -
        previous_pressure
    )


    # Treat changes smaller than
    # 0.5 hPa as effectively steady.

    if abs(change) < 0.5:

        return (
            "steady",
            round(change, 1)
        )


    if change > 0:

        return (
            "rising",
            round(change, 1)
        )


    return (
        "falling",
        round(change, 1)
    )


# -------------------------------------------------
# Create simplified station record
# -------------------------------------------------

def simplify_station(
    station_history
):

    if not station_history:

        return None


    # Latest record.

    latest_time,
    latest_row = (
        station_history[-1]
    )


    wind_speed =
        number(
            find_field(
                latest_row,
                FIELDS[
                    "wind_speed_knots"
                ]
            )
        )


    wind_direction =
        find_field(
            latest_row,
            FIELDS[
                "wind_direction"
            ]
        )


    visibility =
        number(
            find_field(
                latest_row,
                FIELDS[
                    "visibility_nm"
                ]
            )
        )


    wave_height =
        number(
            find_field(
                latest_row,
                FIELDS[
                    "wave_height_m"
                ]
            )
        )


    sea_temperature =
        number(
            find_field(
                latest_row,
                FIELDS[
                    "sea_temperature_c"
                ]
            )
        )


    pressure =
        number(
            find_field(
                latest_row,
                FIELDS[
                    "pressure_hpa"
                ]
            )
        )


    trend,
    change = calculate_pressure_trend(
        station_history,
        latest_time,
        pressure
    )


    return {

        "observation_time":
            latest_time.isoformat(),

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
            trend,

        "pressure_change_hpa":
            change,

        "pressure_period_hours":
            3

    }


# -------------------------------------------------
# Main
# -------------------------------------------------

def main():

    print(
        "Reading Met Office marine data..."
    )


    rows =
        read_rows()


    print(
        f"Rows read: {len(rows)}"
    )


    history =
        build_history(
            rows
        )


    stations = {}


    for station_name
    in STATIONS:

        record =
            simplify_station(
                history[
                    station_name
                ]
            )


        if record:

            stations[
                station_name
            ] = record


            print(
                f"{station_name}: "
                f"{record}"
            )

        else:

            print(
                f"{station_name}: "
                f"NO DATA"
            )


    output = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source":
            "Met Office UK Marine Observations",

        "stations":
            stations

    }


    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )


    print(
        f"Created {OUTPUT_FILE}"
    )


if __name__ == "__main__":

    main()
