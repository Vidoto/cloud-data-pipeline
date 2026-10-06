# Import time to measure execution duration
import time

# Import os for Lambda environment detection
import os

# Import Path for working with files and directories
from pathlib import Path

# Import requests for accessing the Wikipedia page
import requests

# Import pandas for reading and processing the HTML table
import pandas as pd

# Import StringIO so pandas can read the HTML
from io import StringIO

# Import the function that saves metadata
from src.metadata.metadata import save_metadata

# Import the function that uploads files to Amazon S3
from src.aws_storage import upload_file


# ==========================================
# SETTINGS
# ==========================================

# URL of the Wikipedia source page
URL = (
    "https://en.wikipedia.org/wiki/"
    "List_of_countries_by_inflation_rate"
)

# Use Lambda temporary storage in AWS and the local data folder otherwise
DATA_DIR = Path(
    os.getenv(
        "PIPELINE_DATA_DIR",
        "/tmp/data" if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else "data"
    )
)

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"

# Set the RAW file
RAW_FILE = (
    RAW_DIR /
    "wikipedia_inflation.html"
)

# Set the PROCESSED file
PROCESSED_FILE = (
    PROCESSED_DIR /
    "wikipedia_inflation_processed.csv"
)


# ==========================================
# 1. DOWNLOAD THE WIKIPEDIA PAGE
# ==========================================

def download_page():

    # Create the RAW folder if it does not already exist
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Set a User-Agent to identify
    # our crawler to the server
    headers = {
        "User-Agent":
            "CloudDataPipeline/1.0"
    }

    # Send a request to Wikipedia
    response = requests.get(
        URL,
        headers=headers,
        timeout=30
    )

    # Stop if the request returned an error
    response.raise_for_status()

    # Get the page's HTML content
    html = response.text

    # Save the original HTML as RAW data
    with open(
        RAW_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(html)

    # Return the HTML for the next processing step
    return html


# ==========================================
# 2. EXTRACT THE TABLE
# ==========================================

def extract_table(html):

    # Wrap the HTML so pandas can parse it
    html_buffer = StringIO(html)

    # Extract all tables on the page
    tables = pd.read_html(
        html_buffer
    )

    # The inflation table is the second table
    # found on the page
    df = tables[1].copy()

    # Return the table
    return df


# ==========================================
# 3. NORMALIZE COLUMNS
# ==========================================

def normalize_columns(df):

    # Convert column names to strings
    df.columns = [
        str(column)
        for column in df.columns
    ]

    # Remove extra spaces from names
    df.columns = [
        column.strip()
        for column in df.columns
    ]

    # Convert column names to lowercase
    df.columns = [
        column.lower()
        for column in df.columns
    ]

    # Replace spaces with underscores
    df.columns = [
        column.replace(
            " ",
            "_"
        )
        for column in df.columns
    ]

    # Rename the country column
    if df.columns[0] != "country":

        df = df.rename(
            columns={
                df.columns[0]:
                    "country"
            }
        )

    # Return the normalized DataFrame
    return df


# ==========================================
# 4. CLEAN THE DATA
# ==========================================

def clean_data(df):

    # Remove extra spaces from country names
    df["country"] = (
        df["country"]
        .astype(str)
        .str.strip()
    )

    # Identify the columns that represent years
    year_columns = [
        column
        for column in df.columns
        if str(column).isdigit()
    ]

    # Convert the values in the year columns
    # to numbers
    for column in year_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Count the missing values
    missing_values = (
        df[year_columns]
        .isna()
        .sum()
        .sum()
    )

    # Print the number found in the terminal
    print(
        f"Missing values found: "
        f"{missing_values}"
    )

    # Remove rows without a country
    df = df[
        df["country"].notna()
    ]

    # Remove empty names
    df = df[
        df["country"].str.strip() != ""
    ]

    # Return the cleaned data
    return df


# ==========================================
# 5. SAVE PROCESSED DATA
# ==========================================

def save_processed_data(df):

    # Create the processed folder if it does not exist
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save the DataFrame as a CSV file
    df.to_csv(
        PROCESSED_FILE,
        index=False,
        encoding="utf-8"
    )

    # Show where the file was saved
    print(
        "\nProcessed file saved to:"
    )

    print(
        PROCESSED_FILE
    )


# ==========================================
# 6. UPLOAD FILES TO AMAZON S3
# ==========================================

def upload_wikipedia_files():

    # ======================================
    # RAW
    # ======================================

    # Check whether the RAW HTML file exists
    if RAW_FILE.exists():

        # Upload the HTML file to the raw folder in S3
        upload_file(
            RAW_FILE,
            "raw"
        )

    # ======================================
    # PROCESSED
    # ======================================

    # Check whether the processed CSV file exists
    if PROCESSED_FILE.exists():

        # Upload the CSV file to the processed folder in S3
        upload_file(
            PROCESSED_FILE,
            "processed"
        )

    # ======================================
    # METADATA
    # ======================================

    # Find the crawler metadata files
    metadata_files = list(
        METADATA_DIR.glob(
            "wikipedia_inflation_*.json"
        )
    )

    # Check whether any metadata files were found
    if metadata_files:

        # Sort the files and get the most recent one
        latest_metadata = sorted(
            metadata_files
        )[-1]

        # Upload the metadata file to S3
        upload_file(
            latest_metadata,
            "metadata"
        )


# ==========================================
# 7. FULL RUN
# ==========================================

def run_crawler():

    # Start measuring the execution time
    start_time = time.time()

    # Download the Wikipedia page
    html = download_page()

    # Extract the inflation table
    df = extract_table(
        html
    )

    # Normalize the column names
    df = normalize_columns(
        df
    )

    # Clean and convert the data
    df = clean_data(
        df
    )

    # Save the processed CSV file
    save_processed_data(
        df
    )

    # Calculate the execution duration
    duration = (
        time.time()
        - start_time
    )

    # ======================================
    # SAVE METADATA
    # ======================================

    metadata = save_metadata(

        # Source identifier
        source_id=
            "wikipedia_inflation",

        # Record count
        row_count=
            len(df),

        # Execution time
        duration_seconds=
            duration,

        # The crawler does not use a checkpoint
        checkpoint=
            None
    )

    # ======================================
    # UPLOAD TO S3
    # ======================================

    # Upload RAW, PROCESSED, and METADATA files
    # to Amazon S3
    upload_wikipedia_files()

    # Return the data and metadata
    return {
        "data": df,
        "metadata": metadata
    }


# ==========================================
# 8. RUN FROM THE COMMAND LINE
# ==========================================

if __name__ == "__main__":

    # Run the full crawler
    result = run_crawler()

    # Get the processed data
    df = result["data"]

    # Get the metadata
    metadata = result["metadata"]

    # ======================================
    # SHOW THE RESULT
    # ======================================

    print(
        "\nCrawler completed!"
    )

    print(
        f"Total countries: {len(df)}"
    )

    # Show the column names
    print(
        "\nColumns:"
    )

    print(
        list(df.columns)
    )

    # ======================================
    # SHOW METADATA
    # ======================================

    print(
        "\nMetadata:"
    )

    print(
        metadata
    )
