# Cloud Data Pipeline

This project consists of a Python based data pipeline running on AWS. The main goal is to combine air quality data collected from OpenWeather with inflation data collected from Wikipedia.

The project was developed to demonstrate practical data engineering concepts such as data ingestion, web scraping, incremental processing, layered storage, data curation, metadata management, and analytical output generation.

## Architecture

The pipeline uses EventBridge Scheduler to trigger the AWS Lambda function at regular intervals.

The Lambda function executes the data ingestion and processing stages. OpenWeather provides the air quality data, while Wikipedia provides the inflation data.

After the data is collected, it is stored in Amazon S3 and organized into different processing stages. The data moves through the Raw, Processed, and Curated layers. The Curated layer is then used to generate the analytical output.

The main Lambda function is responsible for starting and controlling the entire pipeline execution.

## AWS Services

Amazon S3 is used as the main storage layer for the project. It stores raw, processed, and curated datasets, as well as metadata, checkpoints, and analytical results.

AWS Lambda is responsible for running the pipeline. This allows the processing to run without maintaining a dedicated server.

Amazon EventBridge Scheduler is used to automate pipeline execution. The current configuration runs the pipeline once every hour.

Amazon CloudWatch is used to monitor Lambda execution logs and help identify possible execution issues.

The S3 bucket used by the project is cloud-data-pipeline-kauan-2026.

The main directories used in S3 are Raw, Processed, Curated, Metadata, Checkpoint, and Analysis.

## Data Sources

### OpenWeather Air Pollution API

The OpenWeather Air Pollution API provides information related to air quality for a specific geographic location.

In this project, the data is collected for the São Paulo region using latitude and longitude coordinates.

The collected information includes the air quality index and concentrations of different pollutants, such as carbon monoxide, nitrogen dioxide, ozone, sulfur dioxide, PM2.5, PM10, and ammonia.

The API response is initially stored in its original format and later normalized to make the data easier to process.

### Wikipedia

The second data source is Wikipedia, from which the pipeline extracts a table containing inflation information for different countries.

The crawler downloads the page, identifies the required table, normalizes the column names, and converts the values into numeric formats whenever possible.

Values that cannot be converted are treated as missing data. Records without an identified country are also removed during the cleaning process.

## Data Processing

The pipeline is structured into different processing stages.

The Raw layer keeps the data collected directly from the external sources. This allows the original data to be preserved for future reference or reprocessing.

The Processed layer contains cleaned and normalized data. At this stage, the fields have standardized names and the values are prepared for the next stages of the pipeline.

The Curated layer contains the result of combining the environmental data with the economic indicator used in the project.

This structure makes the pipeline easier to understand and provides a clear separation between each stage of data processing.

## Incremental Processing

The OpenWeather ingestion process uses a checkpoint based on the observation timestamp.

After each execution, the latest processed timestamp is stored in S3. During the next execution, the pipeline compares new observations with the stored checkpoint.

Only observations newer than the checkpoint are processed.

This approach prevents previously processed records from being processed again and reduces the amount of data handled during each execution.

The Wikipedia data follows a different approach. Since the public table can be updated over time, the crawler collects the table again during each pipeline execution.

## Curated Dataset

The Curated dataset combines the air quality information collected in São Paulo with Brazil's inflation indicator for 2024.

The annual inflation value is associated with the environmental observations used in the project.

This integration demonstrates how information from different data sources can be combined within the same data pipeline.

It is important to point out that the current dataset does not contain economic data aligned with each environmental observation. Therefore, the current results should be interpreted as descriptive analysis rather than statistical evidence of a relationship between inflation and air quality.

## Analysis

The analysis stage uses the Curated dataset as its source.

The processing calculates the average PM2.5 value, the average PM10 value, and Brazil's 2024 inflation value.

The pipeline then generates the files used as the analytical output.

The main results are a PNG image and an HTML report.

The analysis was created programmatically to demonstrate that the pipeline does not only collect and store data, but can also use the processed information to generate an analytical result.

Since the current dataset is relatively small and the environmental data has a higher frequency than the annual inflation indicator, the current results are not sufficient to establish a statistically significant correlation.

## Local Execution

To run the project locally, the required Python dependencies must first be installed.

The environment variables required to access the S3 bucket and the OpenWeather API must then be configured.

AWS credentials should also be configured using the standard AWS credential mechanism or a locally configured AWS profile.

The local pipeline execution is started through the run_pipeline.py file.

Credentials should never be stored directly in the source code or committed to GitHub.

Local configuration files such as .env and local.settings.json are included in the .gitignore file and are not part of the repository.

## AWS Execution

In AWS, the pipeline runs through an AWS Lambda function.

The Lambda function collects data from the external sources, executes the processing stages, and stores the results in Amazon S3.

EventBridge Scheduler is responsible for automatically triggering the function according to the configured schedule.

The Lambda execution role must have the required permissions to access S3 and send logs to CloudWatch.

The Lambda function uses lambda_function.lambda_handler as its entry point.

## Project Structure

The project is organized into modules so that each pipeline stage has a clear responsibility.

The src directory contains the modules responsible for API ingestion, web crawling, Curated dataset creation, metadata management, analysis, and Amazon S3 communication.

The lambda_function.py file is responsible for starting the pipeline when the Lambda function is executed.

The run_pipeline.py file allows the complete pipeline to be executed locally.

The data directory contains files generated by the processing and analysis stages.

The documentation directory contains the detailed technical documentation for the project.

## Technologies Used

Python

Pandas

Requests

Boto3

Pillow

AWS Lambda

Amazon S3

Amazon EventBridge Scheduler

Amazon CloudWatch

OpenWeather API

Wikipedia

## Project Objective

The main objective of this project was to develop an end to end data engineering solution using Python and cloud services.

Throughout the development process, the project covered concepts such as data ingestion, incremental processing, web scraping, layered storage, state management, integration of different data sources, and analytical output generation.

The architecture was also designed to allow new data sources and additional processing stages to be added in the future without requiring a complete redesign of the existing pipeline.
