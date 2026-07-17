"""
Module: Table Extractor

Purpose:
    Extract tabular data from PDF documents and save
    each detected table as a CSV file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber

from configs.settings import Settings


class TableExtractor:
    """
    Extract tables from PDF documents.
    """

    def __init__(
        self,
        pdf_path: Path,
        metadata: dict[str, Any],
    ) -> None:

        self.pdf_path = Path(pdf_path)
        self.metadata = metadata

    def extract(self) -> dict[str, Any]:
        """
        Extract tables from the PDF.
        """

        output_directory = (
            Settings.TABLE_DIR /
            self.pdf_path.stem
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        extracted_tables = []

        total_tables = 0

        with pdfplumber.open(
            self.pdf_path
        ) as pdf:

            for page_number, page in enumerate(
                pdf.pages,
                start=1,
            ):

                tables = page.extract_tables()

                if not tables:
                    continue

                for table_index, table in enumerate(
                    tables,
                    start=1,
                ):

                    if not table:
                        continue

                    dataframe = pd.DataFrame(
                        table
                    )

                    if dataframe.empty:
                        continue

                    csv_name = (
                        f"page_{page_number:03d}"
                        f"_table_{table_index:03d}.csv"
                    )

                    csv_path = (
                        output_directory /
                        csv_name
                    )

                    dataframe.to_csv(
                        csv_path,
                        index=False,
                        header=False,
                    )

                    relative_path = (
                        csv_path.relative_to(
                            Settings.PROJECT_ROOT
                        )
                    )

                    table_id = (
                        f"{self.metadata['document_id'][:8]}"
                        f"_p{page_number:03}"
                        f"_t{table_index:03}"
                    )

                    empty_cells = int(
                        dataframe.isna().sum().sum()
                    )

                    extracted_tables.append(
                        {
                            "table_id": table_id,

                            "document_id": self.metadata[
                                "document_id"
                            ],

                            "document": self.pdf_path.name,

                            "page_number": page_number,

                            "table_index": table_index,

                            "rows": dataframe.shape[0],

                            "columns": dataframe.shape[1],

                            "empty_cells": empty_cells,

                            "format": "csv",

                            "path": str(
                                relative_path
                            ),

                            "extraction_method": "pdfplumber",
                        }
                    )

                    total_tables += 1

        return {

            "document_id": self.metadata[
                "document_id"
            ],

            "document": self.pdf_path.name,

            "count": total_tables,

            "tables": extracted_tables,
        }