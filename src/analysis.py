import os
import base64
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from src.aws_storage import upload_file


DATA_DIR = Path("/tmp/data") if os.name != "nt" else Path("data")

CURATED_FILE = DATA_DIR / "curated" / "environment_economic_curated.csv"

ANALYSIS_DIR = DATA_DIR / "analysis"

OUTPUT_FILE = ANALYSIS_DIR / "air_quality_analysis.png"

HTML_OUTPUT_FILE = ANALYSIS_DIR / "air_quality_analysis.html"


def load_data():

    if not CURATED_FILE.exists():
        raise FileNotFoundError(
            f"Curated file not found: {CURATED_FILE}"
        )

    return pd.read_csv(CURATED_FILE)


def analyze_data(df):

    pm25_average = df["pm2_5"].mean()

    pm10_average = df["pm10"].mean()

    inflation = None

    if "inflation_rate" in df.columns:

        inflation_values = df["inflation_rate"].dropna()

        if not inflation_values.empty:
            inflation = inflation_values.iloc[0]

    return {
        "pm25_average": pm25_average,
        "pm10_average": pm10_average,
        "inflation_2024": inflation
    }


def create_chart(metrics):

    ANALYSIS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    width = 1000
    height = 600

    image = Image.new(
        "RGB",
        (width, height),
        "white"
    )

    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            36
        )

        subtitle_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            24
        )

        value_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            30
        )

    except Exception:

        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        value_font = ImageFont.load_default()

    draw.text(
        (50, 40),
        "Air Quality Analysis",
        fill="black",
        font=title_font
    )

    draw.text(
        (50, 100),
        "Programmatically generated from the curated dataset",
        fill="black",
        font=subtitle_font
    )

    pm25 = float(metrics["pm25_average"])
    pm10 = float(metrics["pm10_average"])

    inflation = metrics["inflation_2024"]

    if inflation is None:
        inflation_text = "N/A"
    else:
        inflation_text = f"{float(inflation):.2f}%"

    values = [
        ("Average PM2.5", f"{pm25:.2f}"),
        ("Average PM10", f"{pm10:.2f}"),
        ("Brazil Inflation 2024", inflation_text)
    ]

    y = 190

    for label, value in values:

        draw.text(
            (80, y),
            label,
            fill="black",
            font=subtitle_font
        )

        draw.text(
            (650, y),
            value,
            fill="black",
            font=value_font
        )

        draw.line(
            (70, y + 50, 930, y + 50),
            fill="gray",
            width=2
        )

        y += 110

    draw.text(
        (50, 540),
        "Source: OpenWeather + Wikipedia",
        fill="black",
        font=subtitle_font
    )

    image.save(
        OUTPUT_FILE,
        format="PNG"
    )


def create_html_report(metrics):

    with open(
        OUTPUT_FILE,
        "rb"
    ) as image_file:

        image_base64 = base64.b64encode(
            image_file.read()
        ).decode("utf-8")

    inflation = metrics["inflation_2024"]

    if inflation is None:
        inflation_text = "N/A"
    else:
        inflation_text = f"{float(inflation):.2f}%"

    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>Air Quality Analysis</title>

</head>

<body>

<h1>Air Quality Analysis</h1>

<p>
Programmatically generated analytical artifact.
</p>

<h2>Metrics</h2>

<ul>

<li>
Average PM2.5: {metrics["pm25_average"]:.2f}
</li>

<li>
Average PM10: {metrics["pm10_average"]:.2f}
</li>

<li>
Brazil 2024 Inflation: {inflation_text}
</li>

</ul>

<img
src="data:image/png;base64,{image_base64}"
alt="Air Quality Analysis"
/>

</body>

</html>
"""

    with open(
        HTML_OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(html)


def upload_analysis():

    upload_file(
        OUTPUT_FILE,
        "analysis",
        "air_quality_analysis.png"
    )

    upload_file(
        HTML_OUTPUT_FILE,
        "analysis",
        "air_quality_analysis.html"
    )


def run_analysis():

    df = load_data()

    metrics = analyze_data(df)

    create_chart(metrics)

    create_html_report(metrics)

    upload_analysis()

    return {
        "status": "success",
        "png": str(OUTPUT_FILE),
        "html": str(HTML_OUTPUT_FILE)
    }


if __name__ == "__main__":

    run_analysis()