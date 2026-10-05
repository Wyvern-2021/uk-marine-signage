# UK Marine Signage

A full-screen marine observation display using Met Office UK Marine Observations.

## Display

The display consists of two pages.

### Page 1

- K1
- K2
- K7
- Channel

### Page 2

- K4
- M2
- M4
- M5

Each buoy displays:

- Wind speed in knots
- Wind direction
- Visibility in nautical miles
- Wave height in metres
- Sea temperature in °C
- Atmospheric pressure in hPa
- Three-hour pressure trend
- Observation time

Pages automatically rotate every 20 seconds.

## Data

Data is obtained from the Met Office UK Marine Observations open dataset.

The dataset is published on Amazon S3 and is updated approximately hourly.

Raw observations are processed by GitHub Actions into:

data/marine.json

The webpage itself is hosted using GitHub Pages.

## Attribution

Data source:

Met Office UK Marine Observations

Licensed under CC BY-SA.

https://registry.opendata.aws/met-office-uk-marine-observations/

## Important

This display is an information display only.

It must not be relied upon as the sole source of maritime safety information.
