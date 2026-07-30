"""
Module: PDF Reader

Purpose:
    Handles validation, opening, and closing of PDF
    documents using PyMuPDF.

Responsibilities:
    - Validate PDF file
    - Open PDF
    - Close PDF
    - Provide page count
    - Provide raw metadata
    - Detect encrypted PDFs

"""

from pathlib import Path
from typing import Optional

import fitz


class PDFReader:
    """
    PDF Reader class responsible for opening and validating
    PDF documents.

    Attributes
    ----------
    pdf_path : Path
        Absolute path to the PDF file.

    document : Optional[fitz.Document]
        Opened PyMuPDF document.
    """

    def __init__(self, pdf_path: Path) -> None:
        """
        Initialize the PDF Reader.

        Parameters
        ----------
        pdf_path : Path
            Path to the PDF document.
        """

        self.pdf_path = Path(pdf_path)
        self.document: Optional[fitz.Document] = None

    
    # Validation
    

    def validate(self) -> bool:
        """
        Validate the PDF before opening.

        Returns
        -------
        bool
            True if validation succeeds.

        Raises
        ------
        FileNotFoundError
            If the PDF file does not exist.

        ValueError
            If the supplied file is not a PDF.
        """

        if not self.pdf_path.exists():
            raise FileNotFoundError(
                f"PDF not found:\n{self.pdf_path}"
            )

        if not self.pdf_path.is_file():
            raise FileNotFoundError(
                f"Path is not a file:\n{self.pdf_path}"
            )

        if self.pdf_path.suffix.lower() != ".pdf":
            raise ValueError(
                "Only PDF files are supported."
            )

        return True

    
    # Open PDF
    

    def open(self) -> fitz.Document:
        """
        Open the PDF document.

        Returns
        -------
        fitz.Document
            Opened PDF document.

        Raises
        ------
        RuntimeError
            If the document cannot be opened.
        """

        self.validate()

        try:

            self.document = fitz.open(self.pdf_path)

            if self.document.page_count == 0:
                raise RuntimeError(
                    "PDF contains zero pages."
                )

            return self.document

        except Exception as error:
            raise RuntimeError(
                f"Unable to open PDF:\n{error}"
            ) from error

    
    # Close PDF
    

    def close(self) -> None:
        """
        Close the opened PDF.
        """

        if self.document is not None:
            self.document.close()
            self.document = None

    
    # Properties
    

    @property
    def page_count(self) -> int:
        """
        Total number of pages.

        Returns
        -------
        int
        """

        if self.document is None:
            return 0

        return self.document.page_count

    @property
    def metadata(self) -> dict:
        """
        Return raw PDF metadata.

        Returns
        -------
        dict
        """

        if self.document is None:
            return {}

        return self.document.metadata

    @property
    def is_encrypted(self) -> bool:
        """
        Check whether the PDF is encrypted.

        Returns
        -------
        bool
        """

        if self.document is None:
            return False

        return self.document.needs_pass

    
    # Context Manager Support
    

    def __enter__(self) -> fitz.Document:
        """
        Enable use with the 'with' statement.

        Returns
        -------
        fitz.Document
        """

        return self.open()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Automatically close the PDF.
        """

        self.close()