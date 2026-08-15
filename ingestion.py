import os
from typing import Dict, Any
from pypdf import PdfReader
from PIL import Image, ImageDraw
from retrieval import MultiModalVectorStore
from config import IS_MOCK

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "extracted_images")

def generate_mock_chart(output_path: str):
    """Draws a premium dark-mode balance sheet bar chart using PIL."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 800x500 premium dark blue background
    img = Image.new("RGB", (800, 500), "#0f172a")
    draw = ImageDraw.Draw(img)
    
    # Draw title
    draw.rectangle([0, 0, 800, 80], fill="#1e293b")
    draw.text((40, 30), "APPLE INC. - MOCK BALANCE SHEET CHART (Q3 2026)", fill="#f8fafc")
    
    # Draw grid lines and labels
    for y in [150, 250, 350, 450]:
        draw.line([(80, y), (720, y)], fill="#334155", width=1)
        val = int((450 - y) * 1250)
        draw.text((30, y - 5), f"${val:,}", fill="#64748b")
        
    # Draw bars (Assets, Liabilities, Equity)
    # Total Assets = $500,000 (y = 450 - 400 = 50px)
    draw.rectangle([150, 50, 250, 450], fill="#3b82f6") # Blue
    draw.text((150, 465), "Total Assets\n$500,000", fill="#94a3b8")
    
    # Liabilities = $200,000 (y = 450 - 160 = 290px)
    draw.rectangle([350, 290, 450, 450], fill="#ef4444") # Red
    draw.text((350, 465), "Liabilities\n$200,000", fill="#94a3b8")
    
    # Equity = $300,000 (y = 450 - 240 = 210px)
    draw.rectangle([550, 210, 650, 450], fill="#10b981") # Green
    draw.text((550, 465), "Equity\n$300,000", fill="#94a3b8")
    
    img.save(output_path)
    print(f"Generated mock balance sheet chart at: {output_path}")

def ingest_pdf(pdf_path: str, vector_store: MultiModalVectorStore, is_mock: bool = IS_MOCK) -> Dict[str, Any]:
    """Ingests a financial PDF, extracts text and images, and registers them in the vector store."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    filename = os.path.basename(pdf_path)
    
    if is_mock or not os.path.exists(pdf_path):
        # 1. Ingest Mock Text Chunks
        mock_chunks = [
            ("Apple Inc. reported record high earnings for Q3 2026, driven by cloud computing sales.", {"source": filename, "page": "1"}),
            ("Microsoft announced their new AI cloud division growth reached 40% YoY.", {"source": filename, "page": "2"}),
            ("The balance sheet chart shows rising cash and moderate liabilities across quarters.", {"source": filename, "page": "3"}),
        ]
        for text, meta in mock_chunks:
            vector_store.add_text(text, meta)
            
        # 2. Ingest Mock Image
        chart_name = "balance_sheet.png"
        chart_path = os.path.join(STATIC_DIR, chart_name)
        generate_mock_chart(chart_path)
        
        description = "Apple Inc. Q3 Balance Sheet showing Total Assets of $500,000 and Total Liabilities of $200,000"
        vector_store.add_image(
            image_path=os.path.join("static", "extracted_images", chart_name),
            description=description,
            metadata={"source": filename, "page": "3"}
        )
        
        return {
            "status": "success",
            "chunks_added": len(mock_chunks),
            "images_added": 1,
            "is_mock": True
        }
        
    try:
        reader = PdfReader(pdf_path)
        chunks_count = 0
        images_count = 0
        
        for idx, page in enumerate(reader.pages):
            page_num = str(idx + 1)
            # Extract Text
            text = page.extract_text()
            if text and text.strip():
                # Split into paragraphs/chunks
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                for p_idx, p in enumerate(paragraphs):
                    vector_store.add_text(
                        text=p,
                        metadata={"source": filename, "page": page_num, "chunk_idx": str(p_idx)}
                    )
                    chunks_count += 1
            
            # Extract Images
            for img_idx, img_file in enumerate(page.images):
                img_name = f"{os.path.splitext(filename)[0]}_p{page_num}_img{img_idx}.png"
                img_path = os.path.join(STATIC_DIR, img_name)
                
                with open(img_path, "wb") as f:
                    f.write(img_file.data)
                
                # In live mode, we generate a description using a dummy or default template
                description = f"Extracted visual component {img_name} from page {page_num} of {filename}"
                vector_store.add_image(
                    image_path=os.path.join("static", "extracted_images", img_name),
                    description=description,
                    metadata={"source": filename, "page": page_num}
                )
                images_count += 1
                
        return {
            "status": "success",
            "chunks_added": chunks_count,
            "images_added": images_count,
            "is_mock": False
        }
    except Exception as e:
        print(f"Error parsing PDF: {e}. Falling back to mock ingestion.")
        return ingest_pdf(pdf_path, vector_store, is_mock=True)
