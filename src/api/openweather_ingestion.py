# Import json for working with JSON files
import json

# Import time to measure execution duration
import time

# Import os for Lambda environment detection
import os

# Import Path for working with file paths
from pathlib import Path

# Import pandas for creating and working with DataFrames
import pandas as pd

# Import requests for sending HTTP requests to the API
import requests

# Import the OpenWeather API key
from src.config import OPENWEATHER_API_KEY

# Import the function that saves metadata
from src.metadata.metadata import save_metadata

# Import the Amazon S3 helper functions
from src.aws_storage import (
    upload_file,
    download_file,
    load_checkpoint_from_s3,
    save_checkpoint_to_s3
)


# ==========================================
# SETTINGS
# ==========================================

# Coordinates used to query air quality data
LATITUDE = -23.5505
LONGITUDE = -46.6333


# Use Lambda temporary storage in AWS and the local data folder otherwise
DATA_DIR = Path(
    os.getenv(
        "PIPELINE_DATA_DIR",
        "/tmp/data" if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else "data"
    )
)

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
METADATA_DIR = DATA_DIR / "metadata"


# Set the API RAW file
RAW_FILE = RAW_DIR / "openweather_raw.json"


# Set the PROCESSED file
PROCESSED_FILE = (
    PROCESSED_DIR /
    "openweather_processed.csv"
)


# Set the local checkpoint file
#
# It is still created locally to make
# testing during development.
#
# S3 is the source of truth for the checkpoint.
CHECKPOINT_FILE = (
    CHECKPOINT_DIR /
    "openweather_checkpoint.json"
)


# ==========================================
# 1. FETCH DATA FROM THE API
# ==========================================

def get_air_pollution():

    # Create the RAW folder if it does not already exist
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # OpenWeather air pollution API URL
    url = (
        "https://api.openweathermap.org/"
        "data/2.5/air_pollution"
    )

    # Parameters sent to the API
    params = {
        "lat": LATITUDE,
        "lon": LONGITUDE,
        "appid": OPENWEATHER_API_KEY
    }

    # Send the API request
    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    # Raise an error if the API returns an HTTP error status
    response.raise_for_status()

    # Convert the API response to a Python dictionary
    data = response.json()

    # ======================================
    # SAVE RAW DATA LOCALLY
    # ======================================

    # Open the RAW file for writing
    with open(
        RAW_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        # Save the original API response as JSON
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    # Return the original API data
    return data


# ==========================================
# 2. LOAD THE S3 CHECKPOINT
# ==========================================

def load_checkpoint():

    """
    Gets the last processed timestamp
    directly from Amazon S3.

    S3 is the source of truth for the checkpoint.
    """

    # Read the checkpoint directly from the
    # Amazon S3 "checkpoint" folder
    checkpoint = load_checkpoint_from_s3(
        folder_name="checkpoint",
        file_name="openweather_checkpoint.json"
    )

    # If a checkpoint was found, make sure
    # it a Python integer
    if checkpoint is not None:
        return int(checkpoint)

    # If no checkpoint exists yet
    return None


# ==========================================
# 3. SAVE THE CHECKPOINT
# ==========================================

def save_checkpoint(timestamp):

    """
    Saves the checkpoint to Amazon S3.

    S3 is the authoritative store for the
    incremental ingestion state.
    """

    # Make sure the timestamp is a Python int
    timestamp = int(timestamp)

    # ======================================
    # SAVE TO S3
    # ======================================

    # Save directly to the checkpoint folder in S3
    save_checkpoint_to_s3(
        timestamp=timestamp,
        folder_name="checkpoint",
        file_name="openweather_checkpoint.json"
    )

    # ======================================
    # SAVE LOCALLY
    # ======================================

    # Keep a local copy for testing and development.
    CHECKPOINT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Create the checkpoint payload
    checkpoint = {
        "last_timestamp": timestamp
    }

    # Save a local copy
    with open(
        CHECKPOINT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            checkpoint,
            file,
            ensure_ascii=False,
            indent=4
        )


# ==========================================
# 4. NORMALIZE AND SAVE THE DATA
# ==========================================

def normalize_data(data):

    # Create the processed data folder
    # if it does not already exist
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Get the first record returned by the API
    record = data["list"][0]

    # Get the current observation timestamp
    current_timestamp = int(
        record["dt"]
    )

    # ======================================
    # LOAD THE S3 CHECKPOINT
    # ======================================

    # Get the last processed timestamp
    #
    # IMPORTANT:
    # This value comes from S3,
    # and not from the local file.
    last_timestamp = load_checkpoint()

    # ======================================
    # CHECK FOR DUPLICATES
    # ======================================

    # If the current timestamp has already been processed,
    # do not append the record again
    if (
        last_timestamp is not None
        and current_timestamp <= last_timestamp
    ):
        return None

    # Get the air quality components
    components = record["components"]

    # ======================================
    # ORGANIZE THE DATA
    # ======================================

    normalized = {

        # Location latitude
        "latitude":
            data["coord"]["lat"],

        # Location longitude
        "longitude":
            data["coord"]["lon"],

        # Air quality index
        "aqi":
            record["main"]["aqi"],

        # Carbon monoxide
        "co":
            components["co"],

        # Nitric oxide
        "no":
            components["no"],

        # Nitrogen dioxide
        "no2":
            components["no2"],

        # Ozone
        "o3":
            components["o3"],

        # Sulfur dioxide
        "so2":
            components["so2"],

        # PM2.5 particulate matter
        "pm2_5":
            components["pm2_5"],

        # PM10 particulate matter
        "pm10":
            components["pm10"],

        # Ammonia
        "nh3":
            components["nh3"],

        # Observation timestamp
        "timestamp":
            current_timestamp
    }

    # Create a DataFrame from the normalized record
    df = pd.DataFrame(
        [normalized]
    )

    # ======================================
    # INCREMENTAL INGESTION
    # ======================================

    # Check whether the processed file already exists
    file_exists = PROCESSED_FILE.exists()

    # Append the new record to the CSV file
    df.to_csv(
        PROCESSED_FILE,
        mode="a",
        header=not file_exists,
        index=False
    )

    # ======================================
    # UPDATE THE CHECKPOINT
    # ======================================

    # Save the new timestamp to S3
    save_checkpoint(
        current_timestamp
    )

    # Return the processed DataFrame
    return df


# ==========================================
# 5. UPLOAD FILES TO S3
# ==========================================

def upload_openweather_files():

    # ======================================
    # RAW
    # ======================================

    # Check whether the RAW file exists
    if RAW_FILE.exists():

        # Upload the RAW file to the raw folder in S3
        upload_file(
            RAW_FILE,
            "raw"
        )


    # ======================================
    # PROCESSED
    # ======================================

    # Check whether the processed file exists
    if PROCESSED_FILE.exists():

        # Upload the processed CSV file to S3
        upload_file(
            PROCESSED_FILE,
            "processed"
        )


    # ======================================
    # CHECKPOINT
    # ======================================

    # The checkpoint has already been saved directly to S3
    # by save_checkpoint_to_s3().
    #
    # There is no need to upload it again here.


    # ======================================
    # METADATA
    # ======================================

    # Check whether the metadata folder exists
    if METADATA_DIR.exists():

        # Find the OpenWeather metadata files
        metadata_files = list(
            METADATA_DIR.glob(
                "openweather_air_pollution_*.json"
            )
        )

        # Check whether any files were found
        if metadata_files:

            # Sort the files by name
            # and select the most recent one
            latest_metadata = sorted(
                metadata_files
            )[-1]

            # Upload the latest metadata file to S3
            upload_file(
                latest_metadata,
                "metadata"
            )


# ==========================================
# 6. FULL RUN
# ==========================================

def run_openweather():

    # Start timing the run
    start_time = time.time()

        # ======================================
    # DOWNLOAD THE EXISTING PROCESSED FILE FROM S3
    # ======================================

    # Make sure the folder exists
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Download the existing history from S3
    # so the new record can be added
    # to the existing history.
    download_file(
        "processed",
        "openweather_processed.csv",
        PROCESSED_FILE
    )

    # Fetch data from the API
    data = get_air_pollution()

    # Process and normalize the data
    normalized = normalize_data(
        data
    )

    # Calculate the total execution duration
    duration = time.time() - start_time


    # ======================================
    # WHEN NEW DATA IS FOUND
    # ======================================

    if normalized is not None:

        # Count the new records that were added
        row_count = len(normalized)

        # Get the timestamp of the new record
        # and convert it to a Python int
        checkpoint = int(
            normalized["timestamp"].iloc[-1]
        )


    # ======================================
    # WHEN NO NEW DATA IS FOUND
    # ======================================

    else:

        # No new records were found
        row_count = 0

        # Read the current checkpoint directly from S3
        checkpoint = load_checkpoint()


    # ======================================
    # SAVE METADATA
    # ======================================

    # Create the run metadata
    metadata = save_metadata(

        source_id=
            "openweather_air_pollution",

        row_count=
            row_count,

        duration_seconds=
            duration,

        checkpoint=
            checkpoint
    )


    # ======================================
    # UPLOAD FILES TO S3
    # ======================================

    # Upload RAW, PROCESSED, and METADATA files
    # to S3
    upload_openweather_files()


    # Return the data and metadata
    return {
        "data": normalized,
        "metadata": metadata
    }


# ==========================================
# 7. RUN FROM THE COMMAND LINE
# ==========================================

if __name__ == "__main__":

    # Run the full pipeline
    result = run_openweather()

    # Get the processed data
    normalized = result["data"]

    # Get the metadata
    metadata = result["metadata"]


    # ======================================
    # SHOW THE RESULT
    # ======================================

    # Check whether a new record was found
    if normalized is not None:

        print(
            "\nNew record processed:"
        )

        # Print the new record in the terminal
        print(
            normalized.to_string(
                index=False
            )
        )

    else:

        # Report that no new data was found
        print(
            "\nNo new data found."
        )


    # ======================================
    # SHOW METADATA
    # ======================================

    print(
        "\nRun metadata:"
    )

    # Print the metadata as formatted JSON
    print(
        json.dumps(
            metadata,
            indent=4,
            ensure_ascii=False
        )
    )
