import pytest
import os
from agents.search_agent import SearchAgent
from agents.sql_agent import SQLAgent
from agents.vision_agent import VisionAgent
from config import DB_PATH

def test_search_agent(mock_vector_store):
    """Verifies that the search agent queries the vector database and formats output correctly."""
    agent = SearchAgent(mock_vector_store)
    
    # Query matching Apple text
    res = agent.run("Apple earnings")
    assert "Apple" in res["answer"]
    assert len(res["citations"]) > 0
    assert res["citations"][0]["source"] == "aapl_q3_report.txt"

    # Query matching Microsoft image description
    res_img = agent.run("Microsoft growth chart")
    assert "Microsoft" in res_img["answer"]
    assert any(cite["type"] == "image" for cite in res_img["citations"])

def test_sql_agent():
    """Verifies that the SQL agent translates queries to SQL and queries database successfully."""
    # Ensure DB is present (setup in test or db_setup already run)
    assert os.path.exists(DB_PATH), "Database file must exist for SQL agent testing"
    
    agent = SQLAgent(is_mock=True)
    
    # Test query for maximum value
    res_max = agent.run("What is the maximum price of MSFT?")
    assert res_max["success"] is True
    assert "SELECT MAX(high)" in res_max["sql"]
    assert "max_high" in res_max["answer"]

    # Test query for average value
    res_avg = agent.run("What is the average price of AAPL?")
    assert res_avg["success"] is True
    assert "SELECT AVG(close)" in res_avg["sql"]
    assert "average_close" in res_avg["answer"]

def test_vision_agent():
    """Verifies that the vision agent parses charts/tables using filename-based mocked parser."""
    agent = VisionAgent(is_mock=True)
    
    # Test balance sheet VLM mock
    res_bs = agent.run("path/to/my_balance_sheet.png")
    assert res_bs["success"] is True
    assert "Total Assets" in res_bs["answer"]
    assert "Total Liabilities" in res_bs["answer"]

    # Test revenue growth VLM mock
    res_rev = agent.run("path/to/revenue_growth_chart.jpg")
    assert res_rev["success"] is True
    assert "Revenue" in res_rev["answer"]
    assert "Driver" in res_rev["answer"]

    # Test generic VLM mock
    res_generic = agent.run("other_chart.png")
    assert res_generic["success"] is True
    assert "Data Series" in res_generic["answer"]
