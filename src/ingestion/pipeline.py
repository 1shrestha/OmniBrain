"""
OmniBrain - PDF Ingestion Engine

Module:
    Ingestion Pipeline

Purpose:
    Orchestrates the complete PDF ingestion workflow.
"""

from __future__ import annotations

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
from src.embeddings.image_embedding import ImageEmbeddingGenerator

from src.vector_store.qdrant_store import QdrantStore


class IngestionPipeline:

    def __init__(self):
        Settings.create_directories()
        Settings.print_device_info()
        self.store = QdrantStore()

    def run(self):

        pdf_files = list(Settings.INPUT_PDF_DIR.glob("*.pdf"))

        if not pdf_files:
            print("No PDF found inside data/input/pdfs")
            return

        if len(pdf_files) > 1:
            print("Multiple PDFs found.")
            print("Please keep only one PDF inside data/input/pdfs")
            return

        pdf_path = pdf_files[0]

        print("\n" + "=" * 60)
        print("          OMNIBRAIN PDF INGESTION")
        print("=" * 60)

        reader = PDFReader(pdf_path)

        try:
            document = reader.open()

            print(f"\nOpened PDF : {pdf_path.name}")
            print(f"Pages      : {reader.page_count}")

            metadata_data = self.extract_metadata(pdf_path, document)
            text_data = self.extract_text(pdf_path, document)
            text_data = self.clean_text(text_data)

            chunk_data = self.generate_chunks(pdf_path, text_data, metadata_data)

            text_embeddings = self.generate_embeddings(pdf_path)
            text_vectors_uploaded = self.upload_vectors(text_embeddings)

            image_data = self.extract_images(pdf_path, document, metadata_data)

            image_embeddings = self.generate_image_embeddings(image_data)
            image_vectors_uploaded = self.upload_image_vectors(image_embeddings)

            table_data = self.extract_tables(pdf_path, metadata_data)

            self.generate_report(
                pdf_path,
                metadata_data,
                text_data,
                chunk_data,
                image_data,
                table_data,
                len(text_embeddings),
                text_vectors_uploaded,
                len(image_embeddings),
                image_vectors_uploaded,
            )

            print("\n" + "=" * 60)
            print("Pipeline Completed Successfully")
            print("=" * 60)

        finally:
            reader.close()

    def extract_metadata(self, pdf_path, document):
        extractor = MetadataExtractor(pdf_path, document)
        data = extractor.extract()
        extractor.save(data)
        print("Metadata Extracted")
        return data

    def extract_text(self, pdf_path, document):
        extractor = TextExtractor(pdf_path, document)
        data = extractor.extract()
        extractor.save(data)
        print(f"Text Extracted ({data['page_count']} pages)")
        print(f"OCR Pages : {data['ocr_pages']}")
        return data

    def clean_text(self, text_data):
        cleaner = TextCleaner()
        for page in text_data["pages"]:
            page["text"] = cleaner.clean(page["text"])
        print("Text Cleaned")
        return text_data

    def generate_chunks(self, pdf_path, text_data, metadata_data):
        chunker = TextChunker(pdf_path)
        data = chunker.chunk(text_data=text_data, metadata=metadata_data)
        print(f"Chunks Generated : {data['chunk_count']}")
        data = ChunkValidator().validate(data)
        chunker.save(data)
        print(f"Valid Chunks : {data['chunk_count']}")
        return data

    def generate_embeddings(self, pdf_path):
        chunk_file = Settings.CHUNK_OUTPUT_DIR / f"{pdf_path.stem}_chunks.json"
        embeddings = EmbeddingGenerator().generate(chunk_file)
        print(f"Embeddings Generated : {len(embeddings)}")
        return embeddings

    def upload_vectors(self, embeddings):
        self.store.upload_embeddings(embeddings)
        count = self.store.count_vectors()
        print(f"Vectors Uploaded : {count}")
        return count

    def extract_images(self, pdf_path, document, metadata_data):
        extractor = ImageExtractor(pdf_path, document, metadata_data)
        data = extractor.extract()
        print(f"Images Extracted : {data['unique_images']}")
        return data

    def generate_image_embeddings(self, image_data):
        generator = ImageEmbeddingGenerator()
        embeddings = generator.generate_embeddings(image_data)
        print(f"Image Embeddings Generated : {len(embeddings)}")
        return embeddings

    def upload_image_vectors(self, embeddings):
        if not embeddings:
            print("Image Vectors Uploaded : 0")
            return 0

        uploaded = self.store.upload_image_embeddings(embeddings)
        print(f"Image Vectors Uploaded : {uploaded}")
        return uploaded

    def extract_tables(self, pdf_path, metadata_data):
        extractor = TableExtractor(pdf_path, metadata_data)
        data = extractor.extract()
        print(f"Tables Extracted : {data['count']}")
        return data

    def generate_report(
        self,
        pdf_path,
        metadata_data,
        text_data,
        chunk_data,
        image_data,
        table_data,
        text_embeddings,
        text_vectors_uploaded,
        image_embeddings,
        image_vectors_uploaded,
    ):
        report = ReportGenerator(pdf_path)
        report_data = report.generate(
            metadata=metadata_data,
            text=text_data,
            chunks=chunk_data,
            images=image_data,
            tables=table_data,
            text_embeddings=text_embeddings,
            text_vectors_uploaded=text_vectors_uploaded,
            image_embeddings=image_embeddings,
            image_vectors_uploaded=image_vectors_uploaded,
        )
        report.save(report_data)
        print("Report Generated")
