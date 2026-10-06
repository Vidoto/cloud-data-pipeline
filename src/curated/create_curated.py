# Import pandas for reading and processing the data
import pandas as pd

# Import os for Lambda environment detection
import os

# Import Path for working with file paths
from pathlib import Path

# Import the upload function for Amazon S3
from src.aws_storage import upload_file


# ==========================================
# SETTINGS
# ==========================================

# Use Lambda temporary storage in AWS and the local data folder otherwise
DATA_DIR = Path(
    os.getenv(
        "PIPELINE_DATA_DIR",
        "/tmp/data" if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else "data"
    )
)

# Processed OpenWeather file
OPENWEATHER_FILE = DATA_DIR / "processed/openweather_processed.csv"

# Processed file created by the Wikipedia crawler
WIKIPEDIA_FILE = DATA_DIR / "processed/wikipedia_inflation_processed.csv"

# Folder where the curated dataset will be saved
CURATED_DIR = DATA_DIR / "curated"

# Final curated file
CURATED_FILE = (
    CURATED_DIR /
    "environment_economic_curated.csv"
)


# ==========================================
# 1. LOAD THE DATA
# ==========================================

def load_data():

    # Check whether the OpenWeather file exists
    if not OPENWEATHER_FILE.exists():

        raise FileNotFoundError(
            f"File not found: "
            f"{OPENWEATHER_FILE}"
        )

    # Check whether the Wikipedia file exists
    if not WIKIPEDIA_FILE.exists():

        raise FileNotFoundError(
            f"File not found: "
            f"{WIKIPEDIA_FILE}"
        )

    # Load the OpenWeather data
    openweather = pd.read_csv(
        OPENWEATHER_FILE
    )

    # Load the Wikipedia data
    wikipedia = pd.read_csv(
        WIKIPEDIA_FILE
    )

    # Show the number of loaded records
    print(
        f"OpenWeather records: "
        f"{len(openweather)}"
    )

    print(
        f"Wikipedia records: "
        f"{len(wikipedia)}"
    )

    # Return both DataFrames
    return openweather, wikipedia


# ==========================================
# 2. FIND BRAZIL
# ==========================================

def find_brazil_inflation(wikipedia):

    # Create a normalized version of the country names
    # to make it easier to find Brazil
    wikipedia["country_normalized"] = (
        wikipedia["country"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Find Brazil in the table
    brazil = wikipedia[
        wikipedia["country_normalized"] == "brazil"
    ]

    # Check whether Brazil was found
    if brazil.empty:

        raise ValueError(
            "Brazil was not found in the "
            "Wikipedia table."
        )

    # Get the 2024 inflation value
    inflation = brazil["2024"].iloc[0]

    # Show the value found
    print(
        f"Brazil inflation in 2024: "
        f"{inflation}%"
    )

    # Return the inflation value
    return inflation


# ==========================================
# 3. CREATE THE CURATED DATASET
# ==========================================

def create_curated_dataset(
    openweather,
    inflation
):

    # Create a copy to avoid changes
    # in the original DataFrame
    curated = openweather.copy()

    # Add the corresponding country
    curated["country"] = "Brazil"

    # Add the inflation value found on Wikipedia
    curated["inflation_rate"] = inflation

    # Set the column order for the final dataset
    columns = [

        "country",

        "latitude",

        "longitude",

        "aqi",

        "co",

        "no",

        "no2",

        "o3",

        "so2",

        "pm2_5",

        "pm10",

        "nh3",

        "inflation_rate",

        "timestamp"
    ]

    # Keep only the required columns
    curated = curated[
        columns
    ]

    # Return the curated dataset
    return curated


# ==========================================
# 4. SAVE THE CURATED DATASET
# ==========================================

def save_curated_data(curated):

    # Create the curated folder if it does not exist
    CURATED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save the final dataset as a CSV file
    curated.to_csv(
        CURATED_FILE,
        index=False,
        encoding="utf-8"
    )

    # Show the file location
    print(
        "\nCurated dataset saved to:"
    )

    print(
        CURATED_FILE
    )


# ==========================================
# 5. UPLOAD THE CURATED DATASET TO AMAZON S3
# ==========================================

def upload_curated():

    # Check whether the file exists
    if not CURATED_FILE.exists():

        raise FileNotFoundError(
            f"Curated file not found: "
            f"{CURATED_FILE}"
        )

    # Upload the file to the curated folder in S3
    upload_file(
        CURATED_FILE,
        "curated"
    )


# ==========================================
# 6. FULL RUN
# ==========================================

def run_curated():

    # Load both processed datasets
    openweather, wikipedia = load_data()

    # Get Brazil's inflation value
    inflation = find_brazil_inflation(
        wikipedia
    )

    # Create the curated dataset
    curated = create_curated_dataset(
        openweather,
        inflation
    )

    # Save the dataset locally
    save_curated_data(
        curated
    )

    # Upload the dataset to S3
    upload_curated()

    # Return the result
    return curated


# ==========================================
# 7. RUN FROM THE COMMAND LINE
# ==========================================

if __name__ == "__main__":

    # Run the full curation process
    curated = run_curated()

    # Show the final dataset
    print(
        "\nCurated dataset:"
    )

    print(
        curated.to_string(
            index=False
        )
    )
