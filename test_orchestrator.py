import pytest
from orchestrator import OmniBrainOrchestrator

def test_orchestrator_flow(mock_vector_store):
    """Verifies that the orchestrator routes calls and synthesizes the investment memo."""
    orchestrator = OmniBrainOrchestrator(mock_vector_store, is_mock=True)
    
    # Query triggering both stock prices (SQL) and general reports (Search)
    res = orchestrator.run("What is the average stock price of AAPL? Check general earnings report too.")
    
    assert "INVESTMENT MEMORANDUM" in res["final_answer"]
    assert "Semantics & News Context" in res["final_answer"]
    assert "Quantitative Stock Data" in res["final_answer"]
    assert len(res["citations"]) > 0
    assert any(cite["source"] == "aapl_q3_report.txt" for cite in res["citations"])

def test_orchestrator_vision_routing(mock_vector_store):
    """Verifies orchestrator correctly routes to the vision agent for balance sheet queries."""
    orchestrator = OmniBrainOrchestrator(mock_vector_store, is_mock=True)
    
    res = orchestrator.run("Show details for the balance_sheet.png image.", image_path="balance_sheet.png")
    
    assert "INVESTMENT MEMORANDUM" in res["final_answer"]
    assert "Financial Chart Analysis" in res["final_answer"]
    assert "Parsed Balance Sheet Chart" in res["final_answer"]
