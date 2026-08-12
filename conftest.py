import pytest
import os
import sys

# Append 'src' directory to system path for importing modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from retrieval import MultiModalVectorStore

@pytest.fixture
def mock_vector_store():
    """Provides a pre-populated MultiModalVectorStore for testing."""
    store = MultiModalVectorStore(is_mock=True)
    
    # Add text documents
    store.add_text(
        "Apple Inc. reported record high earnings for Q3 2026, driven by cloud computing.",
        {"source": "aapl_q3_report.txt"}
    )
    store.add_text(
        "Microsoft announced their new AI cloud division growth reached 40% YoY.",
        {"source": "msft_annual_report.txt"}
    )
    
    # Add table/chart images
    store.add_image(
        "balance_sheet.png",
        "Apple Inc. Q3 Balance Sheet showing Total Assets of $500,000 and Total Liabilities of $200,000",
        {"source": "aapl_balance_sheet_image.png"}
    )
    store.add_image(
        "revenue_growth.jpg",
        "Microsoft annual revenue growth chart showing 15% overall company growth in 2026",
        {"source": "msft_growth_chart.jpg"}
    )
    
    return store
