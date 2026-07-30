from src.ingestion.pipeline import IngestionPipeline


def main() -> None:
    """
    Launch the PDF ingestion pipeline.
    """

    pipeline = IngestionPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()