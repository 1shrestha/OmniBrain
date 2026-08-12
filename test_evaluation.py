import pytest
from evaluation import OmniBrainEvaluator

def test_evaluation_groundedness_pass():
    evaluator = OmniBrainEvaluator(is_mock=True)
    query = "What were Apple Q3 earnings?"
    answer = "Apple Inc. reported record high earnings for Q3 2026, driven by cloud computing."
    citations = [{"content": "Apple Inc. reported record high earnings for Q3 2026, driven by cloud computing."}]
    
    result = evaluator.evaluate(query, answer, citations)
    assert result["groundedness"] == 1.0
    assert result["hallucination_score"] == 0.0
    assert result["status"] == "passed"

def test_evaluation_hallucination_flagged():
    evaluator = OmniBrainEvaluator(is_mock=True)
    query = "What were Tesla earnings?"
    answer = "Tesla recorded 500 billion dollars in profit according to internal leaks."
    citations = [{"content": "Apple Inc. reported record high earnings for Q3 2026."}]
    
    result = evaluator.evaluate(query, answer, citations)
    assert result["groundedness"] < 0.5
    assert result["hallucination_score"] > 0.5
    assert result["status"] == "flagged"
