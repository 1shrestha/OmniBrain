"""
OmniBrain - PDF Ingestion Engine

Module:
    Ingestion Pipeline

Purpose:
    Orchestrates the complete PDF ingestion workflow using the new
    layout-aware chunking pipeline.
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
from src.preprocessing.layout.parser import LayoutParser

from src.chunking.layout_chunker import LayoutChunker

from src.embeddings.embedding_generator import EmbeddingGenerator
from src.embeddings.image_embedding import ImageEmbeddingGenerator

from src.vector_store.qdrant_store import QdrantStore
from src.serialization.chunk_serializer import ChunkSerializer


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

            layout_document = self.parse_layout(pdf_path, document)

            # Attach metadata required by LayoutChunker
            layout_document.metadata["document_id"] = metadata_data["document_id"]
            layout_document.metadata["source_path"] = str(pdf_path)

            chunk_collection = self.generate_chunks(layout_document)

            serializer = ChunkSerializer()
            chunk_file = serializer.save(chunk_collection)

            text_embeddings = self.generate_embeddings(chunk_file)
            text_vectors_uploaded = self.upload_vectors(text_embeddings)

            image_data = self.extract_images(pdf_path, document, metadata_data)

            image_embeddings = self.generate_image_embeddings(image_data)
            image_vectors_uploaded = self.upload_image_vectors(image_embeddings)

            table_data = self.extract_tables(pdf_path, metadata_data)

            self.generate_report(
                pdf_path,
                metadata_data,
                text_data,
                chunk_collection,
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

    def parse_layout(self, pdf_path, document):
        parser = LayoutParser()

        layout_document = parser.parse_document(
            document=document,
            pdf_path=str(pdf_path),
            document_name=pdf_path.stem,
        )

        print("Layout Parsed")
        return layout_document

    def generate_chunks(self, layout_document):
        chunker = LayoutChunker()

        collection = chunker.chunk_document(layout_document)

        print(f"Valid Chunks : {collection.chunk_count}")

        return collection

    def generate_embeddings(self, chunk_file):
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
        chunk_collection,
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
            chunks={
                "chunk_count": chunk_collection.chunk_count,
                "statistics": {
                    "total_chunks": chunk_collection.statistics.total_chunks,
                    "total_characters": chunk_collection.statistics.total_characters,
                    "total_words": chunk_collection.statistics.total_words,
                    "average_chunk_size": chunk_collection.statistics.average_chunk_size,
                    "smallest_chunk_size": chunk_collection.statistics.smallest_chunk_size,
                    "largest_chunk_size": chunk_collection.statistics.largest_chunk_size,
                    "table_chunks": chunk_collection.statistics.table_chunks,
                    "empty_chunks_removed": chunk_collection.statistics.empty_chunks_removed,
                    "duplicate_chunks_removed": chunk_collection.statistics.duplicate_chunks_removed,
                    "integrity_failures_removed": chunk_collection.statistics.integrity_failures_removed,
                    "oversized_chunks_flagged": chunk_collection.statistics.oversized_chunks_flagged,
                    "undersized_chunks_flagged": chunk_collection.statistics.undersized_chunks_flagged,
                },
            },
            images=image_data,
            tables=table_data,
            text_embeddings=text_embeddings,
            text_vectors_uploaded=text_vectors_uploaded,
            image_embeddings=image_embeddings,
            image_vectors_uploaded=image_vectors_uploaded,
        )

        report.save(report_data)

        print("Report Generated")
