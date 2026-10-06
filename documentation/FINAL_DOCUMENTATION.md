# FINAL TECHNICAL DOCUMENTATION

## Project overview

I built this Python data pipeline to collect air quality readings from the OpenWeather Air Pollution API and inflation figures from a Wikipedia table. It stores the source files and processed datasets in Amazon S3, enriches the Sao Paulo air quality history with Brazil's 2024 inflation figure, and creates a chart from the final dataset.

The pipeline covers ingestion, raw data storage, data cleaning, incremental processing, metadata, curation, and analysis. AWS is the main deployment target in this repository. There are also Azure Functions and Azure Blob Storage files from an alternative experiment, but those files are not connected to the AWS Lambda entry point.

## Architecture overview

This diagram shows the intended AWS flow. The current implementation gaps are described later in the operational readiness section.

The EventBridge Scheduler starts AWS Lambda.

Lambda runs the Python orchestration and calls the OpenWeather API and Wikipedia crawler.

OpenWeather data is saved as Raw JSON in Amazon S3, then normalized and saved as Processed data.

Wikipedia HTML is saved in Amazon S3, then parsed and saved as a Processed table.

The Processed datasets feed the Curated dataset. Python then creates the analysis chart and saves it to S3.

The pipeline also saves its checkpoint and run metadata in S3. Lambda execution logs go to CloudWatch.

## AWS services and why I chose them

Amazon S3 stores the Raw, Processed, Curated, checkpoint, metadata, and analysis files. Keeping these layers in object storage allows the data to remain available between short-lived compute runs.

AWS Lambda runs the Python pipeline without a server that needs to stay online.

Amazon EventBridge Scheduler starts the Lambda on an hourly schedule.

Amazon CloudWatch Logs captures the Lambda output and errors so a run can be reviewed.

IAM roles control which S3 objects the Lambda can access and allow EventBridge Scheduler to invoke the function.

The bucket name used in the project is cloud-data-pipeline-kauan-2026. The S3 prefixes are raw/, processed/, curated/, metadata/, checkpoint/, and analysis/. These prefixes act like folders, but S3 stores objects by key.

## Repository layout

The main AWS entry point is lambda_function.py. It calls the pipeline stages in sequence.

run_pipeline.py is the local command line entry point.

function_app.py contains an alternative Azure Functions timer entry point.

src/api/openweather_ingestion.py calls OpenWeather, normalizes observations, checks the checkpoint, and uploads files.

src/crawler/wikipedia_inflation.py downloads and parses the Wikipedia inflation table.

src/curated/create_curated.py builds the final Curated CSV.

src/metadata/metadata.py creates a JSON record for each source run.

src/analysis.py calculates summary values and creates the PNG chart.

src/aws_storage.py provides the Amazon S3 client and checkpoint read and write helpers.

src/azure_storage.py contains alternative Azure Blob Storage helpers and is not used by the AWS Lambda entry point.

requirements.txt lists the Python dependencies for the AWS pipeline.

Local data folders mirror the S3 prefixes. They are data/raw/, data/processed/, data/checkpoints/, data/metadata/, data/curated/, and data/analysis/.

## Data sources and ingestion

### OpenWeather Air Pollution API

The API request uses these Sao Paulo coordinates. Latitude is -23.5505 and longitude is -46.6333.

The API key is read from the OPENWEATHER_API_KEY environment variable. Requests use a 30 second timeout and call raise_for_status(). If the API returns an HTTP error, the ingestion stops and the error is passed to the caller.

The original response is written as JSON. The normalizer currently reads the first item in the response list and extracts its timestamp, air quality index, and pollutant measurements.

The Raw JSON response contains coord.lat, coord.lon, and a list of observations. Each observation contains dt, main.aqi, and a components object.

The Processed CSV contains latitude as a float, longitude as a float, aqi as an integer, pollutant fields co, no, no2, o3, so2, pm2_5, pm10, and nh3 as floats, and timestamp as an integer.

The timestamp is the Unix timestamp supplied by the API. Pollutant values are stored as returned. This pipeline does not convert their units.

### Wikipedia inflation crawler

The crawler downloads this page:

https://en.wikipedia.org/wiki/List_of_countries_by_inflation_rate

It saves the original HTML in the Raw layer. It uses pandas.read_html() and selects the second table returned by pandas.

Column names are converted to lowercase, surrounding whitespace is removed, spaces are replaced with underscores, and the first column is renamed to country.

Year columns are converted with pandas.to_numeric(..., errors='coerce'). Values that cannot be converted become missing values. This allows the crawler to keep processing when cells contain unexpected symbols, footnotes, or blanks. Rows without a valid country name are removed.

The Raw dataset is the downloaded HTML page. The Processed dataset contains a country string and year columns from 2024 through 2015. Available yearly values are numeric; unavailable or invalid values remain missing.

The crawler performs a full refresh on each run. It replaces the local Raw and Processed files and uploads the latest versions to S3. It does not track row-level changes or use a crawler checkpoint.

## Incremental ingestion and duplicate handling

OpenWeather uses the observation timestamp as its checkpoint. The checkpoint object is stored at checkpoint/openweather_checkpoint.json and contains an integer field named last_timestamp.

For each API response, the pipeline compares the timestamp of the first returned observation with the saved checkpoint. If the new timestamp is greater, the row is appended to the Processed CSV and the checkpoint is updated. If the timestamp is equal to or older than the saved value, the row is skipped. If there is no checkpoint, the observation is treated as the first record.

The intended flow downloads the existing Processed CSV from S3 before appending a new record. This is needed because Lambda local storage is temporary and does not preserve history between runs.

The current logic only checks the first observation returned by OpenWeather. It does not implement pagination, historical backfill, or recovery of late observations with older timestamps. The API response is not paginated by this implementation.

The checkpoint is saved before the final S3 upload stage. If the checkpoint update succeeds but the Processed upload fails, the next run could skip a row that was never saved to S3. A production implementation should only advance the checkpoint after the data is persisted, or use a recovery process that can safely replay the last batch.

## Curated dataset

The curation step reads both Processed CSV files, finds the row for Brazil in the Wikipedia table, and reads the 2024 inflation value. It then adds a country field with the value Brazil and the inflation value to every OpenWeather row.

The final dataset is stored as curated/environment_economic_curated.csv.

The Curated fields are:

country is a string fixed to Brazil by the current code.

latitude and longitude are floating point coordinates from OpenWeather.

aqi is the integer air quality index from OpenWeather.

co, no, no2, o3, so2, pm2_5, pm10, and nh3 are floating point pollutant measurements from OpenWeather.

inflation_rate is the 2024 Brazil inflation value from the Wikipedia table.

timestamp is the Unix timestamp of the air quality observation.

The current implementation does not join each environmental observation to a time-matched economic observation. It adds one annual inflation value to every Sao Paulo air quality record. The inflation value is therefore constant across the current Curated dataset. This demonstrates that the sources can be combined, but it does not support a statistical correlation claim.

## Metadata

The save_metadata() function creates one JSON record for each source run.

The fields are source_id for the source name, ingestion_timestamp for the UTC time in ISO 8601 format, row_count for the processed volume, execution_duration_seconds for the run duration rounded to four decimal places, and checkpoint for the OpenWeather checkpoint or null for the crawler.

The current source identifiers are openweather_air_pollution and wikipedia_inflation. Metadata filenames include the source identifier and a timestamp. The intended S3 prefix is metadata/.

## Analytical output

The analysis module reads the Curated CSV, calculates the average PM2.5, average PM10, and inflation value, and creates analysis/air_quality_analysis.png.

The chart groups observations by timestamp and plots the PM2.5 values. The summary calculations are printed by the script. The chart is generated from the Curated dataset, as required by the case.

This is a descriptive output. Air quality is measured more frequently than annual inflation, and the environmental history is still small. The chart can show changes in the observed PM2.5 values, but the current data does not establish a relationship between environmental and economic conditions.

## Storage layout and naming

The S3 keys are organized by layer.

The raw/ prefix contains raw/openweather_raw.json and raw/wikipedia_inflation.html.

The processed/ prefix contains processed/openweather_processed.csv and processed/wikipedia_inflation_processed.csv.

The curated/ prefix contains curated/environment_economic_curated.csv.

The checkpoint/ prefix contains checkpoint/openweather_checkpoint.json.

The metadata/ prefix contains timestamped JSON files such as metadata/openweather_air_pollution_timestamp.json.

The analysis/ prefix contains analysis/air_quality_analysis.png.

Column names use lowercase snake case where appropriate. The year columns keep four digit names because they represent calendar years in the source table.

## Orchestration and cloud execution

### AWS orchestration

The Lambda handler runs four stages in order. First, it ingests OpenWeather data. Next, it crawls Wikipedia. Then it creates the Curated dataset. Finally, it runs the analysis and creates the chart.

The project documentation names the Lambda function cloud-data-pipeline and the EventBridge schedule cloud-data-pipeline-hourly. The schedule is described as hourly. There is no infrastructure as code template in the repository to create these resources.

### Configuration

Local execution requires OPENWEATHER_API_KEY, AWS_S3_BUCKET, AWS credentials, and a default AWS region. Credentials can be provided through an AWS profile, the environment, or an IAM role.

For Lambda, configure the environment variables on the function and attach an execution role. Do not include .env, local.settings.json, or credentials in the deployment archive. Production secrets should be stored in AWS Secrets Manager or Systems Manager Parameter Store.

### IAM permissions

The Lambda execution role should have access only to the required bucket objects and its CloudWatch log group. The expected S3 permissions are s3:GetObject for reading the checkpoint and existing Processed data, and s3:PutObject for saving pipeline outputs and checkpoints. Add s3:ListBucket only if the implementation needs to list objects.

The role also needs permission to write CloudWatch Logs. The EventBridge Scheduler role needs permission to invoke the Lambda function.

### Deployment steps

Complete the implementation fixes in the readiness section before deploying.

1. Install the dependencies from requirements.txt in an environment compatible with the chosen Lambda runtime.
2. Build a deployment archive containing lambda_function.py, the complete src/ package, and the required dependencies at the archive root.
3. Create or select a Lambda function. Set its handler to lambda_function.lambda_handler, add the environment variables, and attach a least privilege execution role.
4. Upload the archive and run a manual test invocation.
5. Create an hourly EventBridge Scheduler schedule that targets the Lambda. Give its invocation role permission to call the function.
6. Confirm that the expected S3 objects were created and review the run in CloudWatch Logs.

The README lists Python 3.14 as the Lambda runtime. The Dockerfile uses Python 3.11 for local container execution. Check runtime compatibility before building the deployment package.

### Local execution

From the cloud_data_pipeline/ directory, install the dependencies with python -m pip install -r requirements.txt. Configure the API key, S3 bucket, and AWS credentials, then run python run_pipeline.py.

## Error handling and operations

OpenWeather requests use a 30 second timeout and call raise_for_status(). Wikipedia requests also use a 30 second timeout and call raise_for_status().

When the S3 checkpoint object is missing, the storage helper treats it as the first run. Other S3 errors are raised again so the calling process can report a failure.

The Lambda handler, local runner, and Azure timer log exceptions and re-raise them. There is no retry policy or exponential backoff for API, crawler, or S3 operations.

The crawler assumes the inflation table remains the second table returned by pandas.read_html(). A page layout change could cause the wrong table to be selected or the extraction to fail.

The hourly schedule does not use an explicit lock. Two overlapping runs could update the same checkpoint and CSV at the same time.

## Implementation readiness and known gaps

The main pipeline modules are present, but the current code needs several fixes before it can run reliably in AWS Lambda.

1. src/api/openweather_ingestion.py imports download_file from src/aws_storage.py, but that function is not defined in the AWS storage module. The OpenWeather module cannot be imported until this dependency is resolved, which also prevents the Lambda handler from loading.
2. OpenWeather files use /tmp/data/ paths. The crawler, metadata, curation, and analysis modules use relative data/ paths. Lambda deployment files are not a writable data directory, so these stages need a consistent temporary path and explicit reads and writes to S3.
3. Metadata creation writes to data/metadata/, while the OpenWeather upload logic looks in /tmp/data/metadata/. This mismatch can prevent metadata from being uploaded.
4. The requirements file does not include the Azure packages used by function_app.py and src/azure_storage.py. If the Azure path is kept, it needs its own dependencies and deployment configuration.
5. The repository has no deployment template for Lambda, EventBridge Scheduler, S3, or IAM.
6. Raw and Processed objects use fixed names, so new uploads replace previous objects. Metadata filenames include timestamps, but source snapshots are not versioned by run.

These issues are listed because they affect whether the cloud execution criteria can be met with the current repository.

## Assumptions and limitations

The pipeline assumes that the OpenWeather API key is valid and that the AWS account can access the configured bucket.

Sao Paulo is the environmental observation location. Brazil is the economic reference country.

The curation step applies the 2024 annual inflation figure to every air quality observation.

The hourly OpenWeather ingestion currently reads only the first observation in each API response.

Wikipedia is a public source and may change its table order or formatting.

The current sample is enough to demonstrate the pipeline flow, but not enough to estimate an environmental and economic correlation. The chart should not be presented as evidence of causality or correlation.

## Acceptance criteria status

Python API ingestion and web crawling are present in the source code.

Raw and Processed S3 upload helpers are present, but Lambda path consistency still needs to be fixed and verified.

OpenWeather uses a timestamp checkpoint to avoid duplicate observations. The Wikipedia crawler performs a full refresh.

Metadata includes the source name, UTC ingestion time, row count, execution duration, and checkpoint. Cloud persistence still needs validation.

The Curated dataset uses both sources, but the current implementation repeats Brazil's 2024 inflation value across all environmental rows instead of joining observations by time.

The analysis script reads the Curated dataset and creates a PM2.5 PNG chart.

AWS Lambda and EventBridge Scheduler are described in the project, but the repository does not include infrastructure as code and the import and path issues remain.

This document includes the architecture overview, pipeline details, data schemas, cloud responsibilities, operational considerations, and deployment guidance.

A separate presentation explaining the analytical output, technical decisions, and challenges is not included in the current repository snapshot.