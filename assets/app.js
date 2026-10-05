"use strict";


const REFRESH_INTERVAL =
    5 * 60 * 1000;


const PAGE_1 = [
    "M5",
    "SEVEN_STONES",
    "CHANNEL",
    "SANDETTIE"
];


const PAGE_2 = [
    "DONNA_NOOK",
    "BOULMER",
    "LERWICK",
    "K7"
];


const body =
    document.body;


const pageNumber =
    Number(
        body.dataset.page || "1"
    );


const stationIds =
    pageNumber === 2
        ? PAGE_2
        : PAGE_1;


const grid =
    document.getElementById(
        "station-grid"
    );


const pageTitle =
    document.getElementById(
        "page-title"
    );


const lastUpdated =
    document.getElementById(
        "last-updated"
    );


const statusMessage =
    document.getElementById(
        "status-message"
    );


function displayValue(
    value,
    suffix = "",
    decimals = 0
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


    return (
        number.toFixed(decimals)
        + suffix
    );
}


function displayPressure(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "—";
    }


    return (
        Number(value).toFixed(0)
        + " hPa"
    );
}


function pressureTrend(
    trend,
    change
) {

    if (!trend) {

        return "—";
    }


    if (
        trend === "rising"
    ) {

        if (
            change !== null &&
            change !== undefined
        ) {

            return (
                "↑ Rising "
                + Math.abs(
                    Number(change)
                ).toFixed(1)
                + " hPa"
            );
        }

        return "↑ Rising";
    }


    if (
        trend === "falling"
    ) {

        if (
            change !== null &&
            change !== undefined
        ) {

            return (
                "↓ Falling "
                + Math.abs(
                    Number(change)
                ).toFixed(1)
                + " hPa"
            );
        }

        return "↓ Falling";
    }


    if (
        trend === "steady"
    ) {

        return "→ Steady";
    }


    return "—";
}


function formatObservationTime(
    value
) {

    if (!value) {

        return "No current observation";
    }


    const date =
        new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return "No current observation";
    }


    return date.toLocaleString(
        "en-GB",
        {
            timeZone: "UTC",
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false
        }
    ) + " UTC";
}


function stationCard(
    station
) {

    const card =
        document.createElement(
            "section"
        );


    card.className =
        "station-card";


    if (
        station.status !== "live"
    ) {

        card.classList.add(
            "station-unavailable"
        );
    }


    const title =
        document.createElement(
            "h2"
        );


    title.textContent =
        `${station.name} (${station.descriptor})`;


    card.appendChild(
        title
    );


    const observationTime =
        document.createElement(
            "div"
        );


    observationTime.className =
        "observation-time";


    observationTime.textContent =
        formatObservationTime(
            station.observation_time
        );


    card.appendChild(
        observationTime
    );


    const dataGrid =
        document.createElement(
            "div"
        );


    dataGrid.className =
        "data-grid";


    const fields = [
        [
            "Wind",
            station.wind_direction
                ? `${station.wind_direction} ${displayValue(
                    station.wind_speed_knots,
                    " kt",
                    0
                )}`
                : (
                    station.wind_speed_knots !== null &&
                    station.wind_speed_knots !== undefined
                        ? displayValue(
                            station.wind_speed_knots,
                            " kt",
                            0
                        )
                        : "—"
                )
        ],

        [
            "Visibility",
            displayValue(
                station.visibility_nm,
                " NM",
                1
            )
        ],

        [
            "Wave height",
            displayValue(
                station.wave_height_m,
                " m",
                1
            )
        ],

        [
            "Sea temperature",
            displayValue(
                station.sea_temperature_c,
                " °C",
                1
            )
        ],

        [
            "Pressure",
            displayPressure(
                station.pressure_hpa
            )
        ],

        [
            "Trend",
            pressureTrend(
                station.pressure_trend,
                station.pressure_change_hpa
            )
        ]
    ];


    for (
        const [label, value]
        of fields
    ) {

        const item =
            document.createElement(
                "div"
            );


        item.className =
            "data-item";


        const labelElement =
            document.createElement(
                "span"
            );


        labelElement.className =
            "data-label";


        labelElement.textContent =
            label;


        const valueElement =
            document.createElement(
                "strong"
            );


        valueElement.className =
            "data-value";


        valueElement.textContent =
            value;


        item.appendChild(
            labelElement
        );


        item.appendChild(
            valueElement
        );


        dataGrid.appendChild(
            item
        );
    }


    card.appendChild(
        dataGrid
    );


    if (
        station.status !== "live"
    ) {

        const unavailable =
            document.createElement(
                "div"
            );


        unavailable.className =
            "unavailable-message";


        unavailable.textContent =
            "No current observation available";


        card.appendChild(
            unavailable
        );
    }


    return card;
}


async function loadData() {

    try {

        statusMessage.textContent =
            "Updating observations…";


        const response =
            await fetch(
                "data/marine.json?"
                + Date.now(),
                {
                    cache: "no-store"
                }
            );


        if (
            !response.ok
        ) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        grid.innerHTML =
            "";


        for (
            const stationId
            of stationIds
        ) {

            const station =
                data.stations[
                    stationId
                ];


            if (!station) {

                console.error(
                    "Missing station:",
                    stationId
                );

                continue;
            }


            grid.appendChild(
                stationCard(
                    station
                )
            );
        }


        const generated =
            new Date(
                data.generated_at
            );


        if (
            !Number.isNaN(
                generated.getTime()
            )
        ) {

            lastUpdated.textContent =
                "Data file updated "
                + generated.toLocaleString(
                    "en-GB",
                    {
                        timeZone: "UTC",
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    }
                )
                + " UTC";
        }


        statusMessage.textContent =
            "Live Met Office observations";


    } catch (error) {

        console.error(
            error
        );


        statusMessage.textContent =
            "Unable to refresh data — displaying last available data";
    }
}


pageTitle.textContent =
    pageNumber === 2
        ? "UK MARINE OBSERVATIONS — PAGE 2"
        : "UK MARINE OBSERVATIONS — PAGE 1";


loadData();


setInterval(
    loadData,
    REFRESH_INTERVAL
);
