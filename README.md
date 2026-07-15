# OmniBrain – PDF Ingestion Engine

A production-oriented, modular PDF Ingestion Engine that serves as the first component of the **OmniBrain** ecosystem.

The engine transforms unstructured PDF documents into structured, machine-readable data by extracting metadata, text, images, and tables while providing automatic OCR fallback for scanned documents. The extracted information is prepared for downstream AI applications such as Retrieval-Augmented Generation (RAG), semantic search, multimodal reasoning, and intelligent document understanding.

---

# Key Features

## Document Processing

- PDF validation and loading
- Automatic page detection
- Metadata extraction
- Native text extraction using PyMuPDF
- Automatic OCR fallback using EasyOCR
- Embedded image extraction
- Table extraction using pdfplumber
- Structured JSON report generation

---

## OCR Support

OmniBrain intelligently determines whether OCR is required.

```
PDF Page
    │
    ▼
Native Text Extraction
    │
    ├── Text Found
    │       │
    │       ▼
    │   Continue Processing
    │
    └── No Text
            │
            ▼
      EasyOCR Fallback
            │
            ▼
      Continue Processing
```

Current OCR capabilities:

- Automatic OCR triggering
- Lazy-loaded OCR engine
- Configurable OCR threshold
- Configurable OCR DPI
- Configurable OCR language support

---

# Architecture

```
OmniBrain/
│
├── app/
│   └── main.py
│
├── configs/
│   ├── settings.py
│   └── logging.yaml
│
├── src/
│   ├── ingestion/
│   │   ├── pdf_reader.py
│   │   ├── metadata.py
│   │   ├── text_extractor.py
│   │   ├── ocr.py
│   │   ├── image_extractor.py
│   │   ├── table_extractor.py
│   │   ├── report_generator.py
│   │   └── pipeline.py
│   │
│   ├── preprocessing/
│   ├── embeddings/
│   ├── retrieval/
│   ├── agents/
│   ├── llm/
│   ├── models/
│   ├── utils/
│   └── exceptions/
│
├── data/
│   ├── input/
│   │   └── pdfs/
│   │
│   ├── processed/
│   │   ├── metadata/
│   │   ├── text/
│   │   ├── images/
│   │   ├── tables/
│   │   ├── reports/
│   │   └── ocr/
│   │
│   └── temp/
│
├── docs/
├── logs/
├── scripts/
├── tests/
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Processing Pipeline

```
PDF
 │
 ▼
PDF Reader
 │
 ├────────► Metadata Extraction
 │
 ├────────► Text Extraction
 │               │
 │               ├── Native Extraction
 │               └── OCR Fallback
 │
 ├────────► Image Extraction
 │
 ├────────► Table Extraction
 │
 └────────► Report Generation
 │
 ▼
Structured Outputs
```

---

# Installation

Clone the repository

```bash
git clone <repository-url>
cd OmniBrain
```

Create the environment

```bash
conda create -n omnibrain python=3.11
conda activate omnibrain
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Usage

Place a PDF inside

```
data/input/pdfs/
```

Run the pipeline

```bash
python -m app.main
```

---

# Output Structure

```
data/
└── processed/
    ├── metadata/
    ├── text/
    ├── images/
    ├── tables/
    ├── reports/
    └── ocr/
```

Each processed document generates:

- Metadata JSON
- Extracted text
- OCR text (when required)
- Extracted images
- Extracted tables (CSV)
- Processing report

---

# Technology Stack

| Category | Technologies |
|-----------|--------------|
| Language | Python 3.11 |
| PDF Processing | PyMuPDF, pdfplumber |
| OCR | EasyOCR |
| Image Processing | Pillow |
| Data Processing | NumPy, Pandas |
| Layout Analysis | LayoutParser |
| Logging | Loguru |

---

# Development Progress

## Phase 1 — PDF Ingestion

- [x] Project Architecture
- [x] PDF Reader
- [x] Metadata Extraction
- [x] Native Text Extraction
- [x] OCR Module
- [x] OCR Fallback
- [x] Image Extraction
- [x] Table Extraction
- [x] JSON Report Generation
- [x] Modular Pipeline

---

## Phase 2 — In Progress

- [ ] Logging Framework
- [ ] Exception Handling
- [ ] Layout Analysis
- [ ] OCR Optimization

---

## Phase 3 — Planned

- [ ] Semantic Chunking
- [ ] Embedding Generation
- [ ] Vector Database Integration
- [ ] Hybrid Retrieval
- [ ] LangGraph Workflow
- [ ] Multi-Agent Architecture
- [ ] Multimodal RAG

---

# Future Vision

The PDF Ingestion Engine serves as the foundation of the OmniBrain platform.

Future releases will include:

- Intelligent document layout understanding
- Semantic chunking
- Vector database integration
- Hybrid retrieval
- Vision-language models
- Multi-agent orchestration
- Enterprise-scale document intelligence

---

# Author

**Srikanth Chevvakula**

B.Tech Computer Science & Engineering

Rajiv Gandhi University of Knowledge Technologies (RGUKT)

---

# License

This project is under active development.