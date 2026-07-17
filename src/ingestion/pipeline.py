"""
OmniBrain - PDF Ingestion Engine

Module:
    Ingestion Pipeline

Purpose:
    Orchestrates the complete PDF ingestion workflow.
"""

from __future__ import annotations

from pathlib import Path

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

from src.embeddings.embedding_generator import EmbeddingGenerator
from src.vector_store.qdrant_store import QdrantStore


class IngestionPipeline:
    """
    Complete PDF ingestion workflow.
    """

    def __init__(self):

        Settings.create_directories()

    def run(self):

        pdf_files = list(
            Settings.INPUT_PDF_DIR.glob("*.pdf")
        )

        if not pdf_files:

            print(
                "No PDF found inside data/input/pdfs"
            )

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

            document = reader.open()

            print(
                f"\nOpened PDF : {pdf_path.name}"
            )

            print(
                f"Pages      : {reader.page_count}"
            )

            metadata_data = self.extract_metadata(
                pdf_path,
                document,
            )

            text_data = self.extract_text(
                pdf_path,
                document,
            )

            text_data = self.clean_text(
                text_data
            )

            chunk_data = self.generate_chunks(
                pdf_path,
                text_data,
                metadata_data,
            )           
            embeddings = self.generate_embeddings(
                pdf_path
            )

            self.upload_vectors(
                embeddings
            )

            image_data = self.extract_images(
                pdf_path,
                document,
                metadata_data,
            )

            table_data = self.extract_tables(
                pdf_path,
                metadata_data,
            )

            self.generate_report(
                pdf_path,
                metadata_data,
                text_data,
                chunk_data,
                image_data,
                table_data,
            )

            print(
                "\nPipeline Completed Successfully"
            )

        finally:

            reader.close()

    def extract_metadata(
        self,
        pdf_path,
        document,
    ):

        metadata = MetadataExtractor(
            pdf_path,
            document,
        )

        metadata_data = metadata.extract()

        metadata.save(
            metadata_data
        )

        print("Metadata Extracted")

        return metadata_data

    def extract_text(
        self,
        pdf_path,
        document,
    ):

        extractor = TextExtractor(
            pdf_path,
            document,
        )

        text_data = extractor.extract()

        extractor.save(
            text_data
        )

        print(
            f"Text Extracted ({text_data['page_count']} pages)"
        )

        print(
            f"OCR Pages : {text_data['ocr_pages']}"
        )

        return text_data

    def clean_text(
        self,
        text_data,
    ):

        cleaner = TextCleaner()

        for page in text_data["pages"]:

            page["text"] = cleaner.clean(
                page["text"]
            )

        print(
            "Text Cleaned"
        )

        return text_data

    def generate_chunks(
        self,
        pdf_path,
        text_data,
        metadata_data,
    ):

        chunker = TextChunker(
            pdf_path
        )

        chunk_data = chunker.chunk(
            text_data=text_data,
            metadata=metadata_data,
        )

        print(
            f"Chunks Generated : {chunk_data['chunk_count']}"
        )

        validator = ChunkValidator()

        chunk_data = validator.validate(
            chunk_data
        )

        chunker.save(
            chunk_data
        )

        print(
            f"Valid Chunks : {chunk_data['chunk_count']}"
        )

        return chunk_data
        def generate_embeddings(
        self,
        pdf_path,
        ):
            """
        Generate embeddings from validated chunks.
        """

        chunk_file = (
            Settings.CHUNK_OUTPUT_DIR /
            f"{pdf_path.stem}_chunks.json"
        )

        generator = EmbeddingGenerator()

        embeddings = generator.generate(
            chunk_file
        )

        print(
            f"Embeddings Generated : {len(embeddings)}"
        )

        return embeddings

    def upload_vectors(
        self,
        embeddings,
    ):
        """
        Upload embeddings to the vector database.
        """

        store = QdrantStore()

        store.upload_embeddings(
            embeddings
        )

        print(
            f"Vectors Uploaded : {store.count_vectors()}"
        )

    def extract_images(
        self,
        pdf_path,
        document,
        metadata_data,
    ):
        """
        Extract images from the PDF.
        """

        extractor = ImageExtractor(
            pdf_path,
            document,
            metadata_data,
        )

        image_data = extractor.extract()

        print(
            f"Images Extracted : {image_data['unique_images']}"
        )

        return image_data

    def extract_tables(
        self,
        pdf_path,
        metadata_data,
    ):
        """
        Extract tables from the PDF.
        """

        extractor = TableExtractor(
            pdf_path,
            metadata_data,
        )

        table_data = extractor.extract()

        print(
            f"Tables Extracted : {table_data['count']}"
        )

        return table_data

    def generate_report(
        self,
        pdf_path,
        metadata_data,
        text_data,
        chunk_data,
        image_data,
        table_data,
    ):
        """
        Generate the ingestion report.
        """

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

        report.save(
            report_data
        )

        print(
            "Report Generated"
        )