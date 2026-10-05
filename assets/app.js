const CONFIG = {

    stations: {

        1: [
            "K1",
            "K2",
            "K7",
            "Channel"
        ],

        2: [
            "K4",
            "M2",
            "M4",
            "M5"
        ]

    },


    /*
     * How long each page remains on screen.
     *
     * 20 seconds is a good starting point.
     */
    pageDuration:
        20 * 1000,


    /*
     * The Met Office dataset is updated hourly.
     * Refreshing the JSON every five minutes
     * lets the screen pick up new data quickly.
     */
    dataRefresh:
        5 * 60 * 1000

};


/* -----------------------------------------
   Utility
----------------------------------------- */

function valueOrDash(value) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number.isNaN(Number(value))
    ) {
        return "—";
    }

    return value;

}


function fixed(
    value,
    decimals = 1
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    const number =
        Number(value);

    if (
        Number.isNaN(number)
    ) {
        return "—";
    }

    return number.toFixed(
        decimals
    );

}


/* -----------------------------------------
   Wind direction
----------------------------------------- */

function directionDegrees(
    direction
) {

    const directions = {

        N: 0,
        NNE: 22.5,
        NE: 45,
        ENE: 67.5,

        E: 90,
        ESE: 112.5,
        SE: 135,
        SSE: 157.5,

        S: 180,
        SSW: 202.5,
        SW: 225,
        WSW: 247.5,

        W: 270,
        WNW: 292.5,
        NW: 315,
        NNW: 337.5

    };


    if (
        typeof direction ===
        "number"
    ) {
        return direction;
    }


    return directions[
        String(direction)
            .toUpperCase()
            .trim()
    ] ?? 0;

}


/* -----------------------------------------
   Timestamp
----------------------------------------- */

function formatTime(
    timestamp
) {

    if (!timestamp) {
        return "No time";
    }


    const date =
        new Date(timestamp);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return timestamp;
    }


    return date.toLocaleString(
        "en-GB",
        {

            timeZone:
                "Europe/London",

            day: "2-digit",
            month: "short",

            hour: "2-digit",
            minute: "2-digit",

            hour12: false

        }
    ) + " UTC";

}


/* -----------------------------------------
   Observation age
----------------------------------------- */

function observationAge(
    timestamp
) {

    if (!timestamp) {
        return null;
    }


    const observed =
        new Date(timestamp)
            .getTime();


    const now =
        Date.now();


    const ageMinutes =
        Math.max(
            0,
            Math.round(
                (
                    now -
                    observed
                ) / 60000
            )
        );


    return ageMinutes;

}


/* -----------------------------------------
   Pressure trend
----------------------------------------- */

function trendDetails(
    station
) {

    const trend =
        station.pressure_trend;


    const change =
        Number(
            station.pressure_change_hpa
        );


    if (
        trend === "rising"
    ) {

        return {

            className:
                "trend-rising",

            arrow:
                "↑",

            text:
                `Rising ${
                    Math.abs(change)
                } hPa / 3h`

        };

    }


    if (
        trend === "falling"
    ) {

        return {

            className:
                "trend-falling",

            arrow:
                "↓",

            text:
                `Falling ${
                    Math.abs(change)
                } hPa / 3h`

        };

    }


    return {

        className:
            "trend-steady",

        arrow:
            "→",

        text:
            "Steady"

    };

}


/* -----------------------------------------
   Build card
----------------------------------------- */

function createCard(
    stationName,
    station
) {

    const card =
        document.createElement(
            "section"
        );


    card.className =
        "buoy-card";


    const age =
        observationAge(
            station.observation_time
        );


    const isStale =
        age === null ||
        age > 180;


    const liveClass =
        isStale
            ? "stale"
            : "live";


    const liveText =
        age === null
            ? "● NO DATA"
            : age > 180
                ? `● DATA ${age} MIN OLD`
                : "● LIVE";


    const trend =
        trendDetails(
            station
        );


    const windDirection =
        valueOrDash(
            station.wind_direction
        );


    const windDegrees =
        directionDegrees(
            station.wind_direction
        );


    card.innerHTML = `

        <div class="buoy-header">

            <div>

                <div class="buoy-name">
                    ${stationName}
                </div>

                <div class="buoy-type">
                    MET OFFICE BUOY
                </div>

            </div>


            <div class="observation-time">

                Observed

                <br>

                ${formatTime(
                    station.observation_time
                )}

            </div>

        </div>


        <div class="metrics">


            <!-- WIND -->

            <div class="metric">

                <div class="metric-label">
                    Wind
                </div>


                <div class="metric-value wind-value">

                    <span
                        class="wind-arrow"
                        style="
                            transform:
                            rotate(
                                ${windDegrees}deg
                            );
                        "
                    >
                        ↑
                    </span>


                    <span>
                        ${valueOrDash(
                            station.wind_speed_knots
                        )}

                        <span class="metric-unit">
                            kt
                        </span>
                    </span>


                    <span class="wind-direction">
                        ${windDirection}
                    </span>

                </div>

            </div>


            <!-- VISIBILITY -->

            <div class="metric">

                <div class="metric-label">
                    Visibility
                </div>


                <div class="metric-value">

                    ${fixed(
                        station.visibility_nm,
                        1
                    )}

                    <span class="metric-unit">
                        NM
                    </span>

                </div>

            </div>


            <!-- WAVES -->

            <div class="metric">

                <div class="metric-label">
                    Wave Height
                </div>


                <div class="metric-value">

                    ${fixed(
                        station.wave_height_m,
                        1
                    )}

                    <span class="metric-unit">
                        m
                    </span>

                </div>

            </div>


            <!-- SEA TEMPERATURE -->

            <div class="metric">

                <div class="metric-label">
                    Sea Temperature
                </div>


                <div class="metric-value">

                    ${fixed(
                        station.sea_temperature_c,
                        1
                    )}

                    <span class="metric-unit">
                        °C
                    </span>

                </div>

            </div>


            <!-- PRESSURE -->

            <div class="metric pressure">

                <div class="metric-label">
                    Atmospheric Pressure
                </div>


                <div class="pressure-row">

                    <div class="pressure-main">

                        ${fixed(
                            station.pressure_hpa,
                            0
                        )}

                        <span class="metric-unit">
                            hPa
                        </span>

                    </div>


                    <div
                        class="
                            pressure-trend
                            ${trend.className}
                        "
                    >

                        <span class="trend-arrow">
                            ${trend.arrow}
                        </span>

                        <span>
                            ${trend.text}
                        </span>

                    </div>

                </div>

            </div>

        </div>


        <div class="card-footer">

            <div class="${liveClass}">
                ${liveText}
            </div>


            <div>
                Latest available observation
            </div>

        </div>

    `;


    return card;

}


/* -----------------------------------------
   Load data
----------------------------------------- */

async function loadData() {

    const dashboard =
        document.getElementById(
            "dashboard"
        );


    const status =
        document.getElementById(
            "dataStatus"
        );


    try {

        status.textContent =
            "Updating...";


        const response =
            await fetch(
                `data/marine.json?t=${Date.now()}`,
                {
                    cache:
                        "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${
                    response.status
                }`
            );

        }


        const data =
            await response.json();


        const page =
            window.DASHBOARD_PAGE ||
            1;


        const stations =
            CONFIG.stations[
                page
            ];


        dashboard.innerHTML =
            "";


        for (
            const name
            of stations
        ) {

            const station =
                data.stations?.[
                    name
                ];


            if (station) {

                dashboard.appendChild(
                    createCard(
                        name,
                        station
                    )
                );

            } else {

                dashboard.appendChild(
                    createMissingCard(
                        name
                    )
                );

            }

        }


        status.textContent =
            `DATA UPDATED ${
                formatTime(
                    data.generated_at
                )
            }`;


        status.style.color =
            "#43e38a";


    } catch (error) {

        console.error(
            error
        );


        status.textContent =
            "DATA UPDATE ERROR";


        status.style.color =
            "#ff6868";

    }

}


/* -----------------------------------------
   Missing station
----------------------------------------- */

function createMissingCard(
    name
) {

    const card =
        document.createElement(
            "section"
        );


    card.className =
        "buoy-card";


    card.innerHTML = `

        <div class="buoy-header">

            <div>

                <div class="buoy-name">
                    ${name}
                </div>

                <div class="buoy-type">
                    MET OFFICE BUOY
                </div>

            </div>

        </div>


        <div
            class="metric"
            style="
                flex: 1;
                justify-content: center;
            "
        >

            <div class="metric-label">
                Observation
            </div>

            <div class="metric-value">
                —
            </div>

            <div class="metric-label">
                No current observation
                available
            </div>

        </div>

    `;


    return card;

}


/* -----------------------------------------
   Automatic page rotation
----------------------------------------- */

function startPageRotation() {

    setTimeout(
        function () {

            window.location.href =
                window.NEXT_PAGE;

        },
        CONFIG.pageDuration
    );

}


/* -----------------------------------------
   Start application
----------------------------------------- */

loadData();

startPageRotation();


setInterval(
    loadData,
    CONFIG.dataRefresh
);
