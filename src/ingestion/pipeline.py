"""
OmniBrain - PDF Ingestion Engine

Module: Ingestion Pipeline

Purpose:
    Orchestrates the complete PDF ingestion workflow.
"""

from configs.settings import Settings

from src.ingestion.pdf_reader import PDFReader
from src.ingestion.metadata import MetadataExtractor
from src.ingestion.text_extractor import TextExtractor
from src.ingestion.image_extractor import ImageExtractor
from src.ingestion.table_extractor import TableExtractor
from src.ingestion.report_generator import ReportGenerator

from src.preprocessing.cleaner import TextCleaner

from src.chunking.text_chunker import TextChunker
from src.chunking.validator import ChunkValidator


class IngestionPipeline:
    """
    Complete PDF ingestion workflow.
    """

    def __init__(self) -> None:

        Settings.create_directories()

    def run(self) -> None:

        pdf_files = list(
            Settings.INPUT_PDF_DIR.glob("*.pdf")
        )

        if not pdf_files:
            print("No PDF found inside data/input/pdfs")
            return

        if len(pdf_files) > 1:
            print("Multiple PDFs found.")
            print(
                "Please keep only one PDF inside data/input/pdfs"
            )
            return

        pdf_path = pdf_files[0]

        print("\n" + "=" * 60)
        print("          OMNIBRAIN PDF INGESTION")
        print("=" * 60)

        reader = PDFReader(pdf_path)

        try:

            # Open PDF

            document = reader.open()

            print(f"\nOpened PDF : {pdf_path.name}")
            print(f"Pages      : {reader.page_count}")

            # Metadata Extraction

            metadata = MetadataExtractor(
                pdf_path,
                document,
            )

            metadata_data = metadata.extract()

            metadata.save(metadata_data)

            print("Metadata Extracted")

            # Text Extraction

            text = TextExtractor(
                pdf_path,
                document,
            )

            text_data = text.extract()

            text.save(text_data)

            print(
                f"Text Extracted "
                f"({text_data['page_count']} pages)"
            )

            print(
                f"OCR Pages : "
                f"{text_data['ocr_pages']}"
            )

            # Text Cleaning

            cleaner = TextCleaner()

            for page in text_data["pages"]:

                page["text"] = cleaner.clean(
                    page["text"]
                )

            print("Text Cleaned")

            # Text Chunking

            chunker = TextChunker(
                pdf_path
            )

            chunk_data = chunker.chunk(
                text_data=text_data,
                metadata=metadata_data,
            )

            print(
                f"Chunks Generated : "
                f"{chunk_data['chunk_count']}"
            )

            # Chunk Validation

            validator = ChunkValidator()

            chunk_data = validator.validate(
                chunk_data
            )

            chunker.save(
                chunk_data
            )

            print(
                f"Valid Chunks : "
                f"{chunk_data['chunk_count']}"
            )

            # Image Extraction

            images = ImageExtractor(
                pdf_path,
                document,
                metadata_data,
            )

            image_data = images.extract()

            print(
                f"Images Extracted : "
                f"{image_data['unique_images']}"
            )

            # Table Extraction

            tables = TableExtractor(
                pdf_path,
                metadata_data,
            )

            table_data = tables.extract()

            print(
                f"Tables Extracted : "
                f"{table_data['count']}"
            )

            # Report Generation

            report = ReportGenerator(
                pdf_path
            )

            report_data = report.generate(
                metadata=metadata_data,
                text=text_data,
                chunks=chunk_data,
                images=image_data,
                tables=table_data,
            )

            report.save(report_data)

            print("Report Generated")

            print(
                "\nPipeline Completed Successfully"
            )

        finally:

            reader.close()