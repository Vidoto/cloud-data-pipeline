# Import os for accessing environment variables
import os

# Import mimetypes to preserve the content type in S3
import mimetypes

# Import Path for working with file paths
from pathlib import Path

# Import json for working with checkpoints
import json

# Import boto3, the AWS SDK for Python
import boto3

# Import ClientError for handling S3 errors
from botocore.exceptions import ClientError

# Load variables from the .env file
from dotenv import load_dotenv


# ==================================================
# SETTINGS
# ==================================================

# Load variables from the .env file
load_dotenv()

# Get the S3 bucket name
BUCKET_NAME = os.getenv("AWS_S3_BUCKET")

# Check whether the bucket name is configured
if not BUCKET_NAME:
    raise ValueError(
        "AWS_S3_BUCKET was not found in the .env file"
    )


# Create the Amazon S3 client
s3_client = boto3.client("s3")


# ==================================================
# FILE UPLOAD FUNCTION
# ==================================================

def upload_file(
    local_file,
    folder_name,
    file_name=None
):
    

    # Convert the path to a Path object
    local_file = Path(local_file)

    # Check whether the file exists
    if not local_file.exists():
        raise FileNotFoundError(
            f"File not found: {local_file}"
        )

    # If no file name was provided,
    # use the original file name
    if file_name is None:
        file_name = local_file.name

    # Build the object path in S3
    s3_key = f"{folder_name}/{file_name}"

    # Preserve the content type when the file extension is known
    content_type, _ = mimetypes.guess_type(
        str(local_file)
    )

    upload_options = {}

    if content_type:
        upload_options["ContentType"] = content_type

    # Upload the file to S3
    s3_client.upload_file(
        str(local_file),
        BUCKET_NAME,
        s3_key,
        ExtraArgs=upload_options
    )

    print(
        f"Uploaded to S3: "
        f"s3://{BUCKET_NAME}/{s3_key}"
    )


# ==================================================
# FILE DOWNLOAD FUNCTION
# ==================================================

def download_file(
    folder_name,
    file_name,
    local_file
):
    """Downloads an S3 object when it already exists.

    Returns True when the file was downloaded and False when the
    object is not present yet. A missing object is expected on the
    first pipeline execution.
    """

    local_file = Path(local_file)
    local_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    s3_key = f"{folder_name}/{file_name}"

    try:

        s3_client.download_file(
            BUCKET_NAME,
            s3_key,
            str(local_file)
        )

        print(
            f"Downloaded from S3: "
            f"s3://{BUCKET_NAME}/{s3_key}"
        )

        return True

    except ClientError as error:

        error_code = error.response["Error"]["Code"]

        if error_code in ("NoSuchKey", "404"):

            print(
                f"S3 object not found yet: "
                f"s3://{BUCKET_NAME}/{s3_key}"
            )

            return False

        raise


# ==================================================
# LOAD THE S3 CHECKPOINT
# ==================================================

def load_checkpoint_from_s3(
    folder_name="checkpoint",
    file_name="openweather_checkpoint.json"
):
    """
    Reads the checkpoint directly from Amazon S3.

    Returns:
        int  -> the last processed timestamp
        None -> if no checkpoint exists yet
    """

    # Build the checkpoint path in S3
    s3_key = f"{folder_name}/{file_name}"

    try:

        # Download the object from S3
        response = s3_client.get_object(
            Bucket=BUCKET_NAME,
            Key=s3_key
        )

        # Read the contents
        downloaded_data = response["Body"].read()

        # Convert the JSON to Python
        checkpoint_data = json.loads(
            downloaded_data.decode("utf-8")
        )

        # Return the saved timestamp
        return checkpoint_data.get("last_timestamp")

    except ClientError as error:

        # Check whether the object does not exist
        error_code = error.response["Error"]["Code"]

        if error_code in ("NoSuchKey", "404"):

            # First run
            return None

        # Stop if this is a different error
        raise


# ==================================================
# SAVE THE S3 CHECKPOINT
# ==================================================

def save_checkpoint_to_s3(
    timestamp,
    folder_name="checkpoint",
    file_name="openweather_checkpoint.json"
):
    """
    Saves the timestamp from the latest run
    directly to Amazon S3.
    """

    # Make sure the timestamp is a Python int
    timestamp = int(timestamp)

    # Create the checkpoint payload
    checkpoint_data = {
        "last_timestamp": timestamp
    }

    # Convert the dictionary to JSON
    json_data = json.dumps(
        checkpoint_data,
        indent=4
    )

    # Build the checkpoint path
    s3_key = f"{folder_name}/{file_name}"

    # Upload the JSON directly to S3
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=json_data.encode("utf-8"),
        ContentType="application/json"
    )

    print(
        f"Checkpoint saved to S3: "
        f"s3://{BUCKET_NAME}/{s3_key}"
    )


# ==================================================
# FILE TEST
# ==================================================

if __name__ == "__main__":

    # Test uploading the OpenWeather RAW file
    upload_file(
        "data/raw/openweather_raw.json",
        "raw"
    )
