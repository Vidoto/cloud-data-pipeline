import json
import os
from datetime import datetime, timezone
from pathlib import Path


# ==========================================
# SETTINGS
# ==========================================

DATA_DIR = Path(
    os.getenv(
        "PIPELINE_DATA_DIR",
        "/tmp/data" if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else "data"
    )
)

METADATA_DIR = DATA_DIR / "metadata"


# ==========================================
# SAVE METADATA
# ==========================================

def save_metadata(
    source_id,
    row_count,
    duration_seconds,
    checkpoint=None
):

    # Create the folder if it does not exist
    METADATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Build the run metadata
    metadata = {

        "source_id": source_id,

        "ingestion_timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "row_count":
            row_count,

        "execution_duration_seconds":
            round(
                duration_seconds,
                4
            ),

        "checkpoint":
            checkpoint
    }

    # Create a unique file name
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output_file = (
        METADATA_DIR /
        f"{source_id}_{timestamp}.json"
    )

    # Save the JSON file
    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=4
        )

    return metadata
