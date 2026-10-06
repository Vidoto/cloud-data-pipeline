import logging

from src.api.openweather_ingestion import run_openweather
from src.crawler.wikipedia_inflation import run_crawler
from src.curated.create_curated import run_curated
from src.analysis import run_analysis


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logging.info("===== PIPELINE STARTED =====")

    try:
        logging.info("Running OpenWeather ingestion...")
        openweather_result = run_openweather()
        logging.info("OpenWeather ingestion completed: %s", openweather_result)

        logging.info("Running the Wikipedia crawler...")
        crawler_result = run_crawler()
        logging.info("Wikipedia crawler completed: %s", crawler_result)

        logging.info("Building the curated dataset...")
        curated_result = run_curated()
        logging.info("Curated dataset created: %s", curated_result)

        logging.info("Running the analysis...")
        analysis_result = run_analysis()
        logging.info("Analysis completed: %s", analysis_result)

        logging.info("===== PIPELINE COMPLETED SUCCESSFULLY =====")

    except Exception as error:
        logging.exception("Pipeline execution failed: %s", error)
        raise


if __name__ == "__main__":
    main()
