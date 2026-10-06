import logging

from src.api.openweather_ingestion import run_openweather
from src.crawler.wikipedia_inflation import run_crawler
from src.curated.create_curated import run_curated
from src.analysis import run_analysis


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info("===== PIPELINE STARTED =====")

    try:

        logger.info("Running OpenWeather ingestion...")
        openweather_result = run_openweather()

        logger.info(
            "OpenWeather ingestion completed: %s",
            openweather_result
        )


        logger.info("Running the Wikipedia crawler...")
        crawler_result = run_crawler()

        logger.info(
            "Wikipedia crawler completed: %s",
            crawler_result
        )


        logger.info("Building the curated dataset...")
        curated_result = run_curated()

        logger.info(
            "Curated dataset created: %s",
            curated_result
        )


        logger.info("Running the analysis...")
        analysis_result = run_analysis()

        logger.info(
            "Analysis completed: %s",
            analysis_result
        )


        logger.info(
            "===== PIPELINE COMPLETED SUCCESSFULLY ====="
        )

        return {
            "statusCode": 200,
            "message": "Pipeline completed successfully"
        }


    except Exception as error:

        logger.exception(
            "Pipeline execution failed: %s",
            error
        )

        raise
