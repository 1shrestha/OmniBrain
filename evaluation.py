"""
OmniBrain Evaluation Module
Author: Sowbarnika
Role: Hallucination & Response Quality Evaluator

This module measures RAG performance metrics including Groundedness (Faithfulness),
Answer Relevance, and Hallucination Risk scoring over LLM-generated responses.
"""

import re
from typing import Dict, Any, List
from config import IS_MOCK

class OmniBrainEvaluator:
    def __init__(self, is_mock: bool = IS_MOCK):
        self.is_mock = is_mock

    def evaluate_groundedness(self, answer: str, citations: List[Dict[str, Any]]) -> float:
        """Measures groundedness: how well the answer is backed by citations.
        Returns a float between 0.0 and 1.0.
        """
        if not citations:
            return 0.0
            
        answer_lower = answer.lower()
        matched_citations = 0
        
        for citation in citations:
            content = citation.get("content", "").lower()
            if not content:
                continue
            
            # Split citation into phrases for matching check
            phrases = [p.strip() for p in re.split(r'[.,;\n]', content) if len(p.strip()) > 8]
            if not phrases:
                if content in answer_lower:
                    matched_citations += 1
                continue
                
            matches = sum(1 for phrase in phrases if phrase in answer_lower)
            if matches / len(phrases) >= 0.2:  # at least 20% match
                matched_citations += 1
                
        return matched_citations / len(citations)

    def evaluate_relevance(self, query: str, answer: str) -> float:
        """Measures whether the answer addresses key topics of the query."""
        query_words = [w.strip("?,.!") for w in query.lower().split() if len(w) > 3]
        if not query_words:
            return 1.0
            
        matches = sum(1 for word in query_words if word in answer.lower())
        return matches / len(query_words)

    def evaluate(self, query: str, answer: str, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates evaluation metrics and flags potential hallucinations."""
        groundedness = self.evaluate_groundedness(answer, citations)
        relevance = self.evaluate_relevance(query, answer)
        
        # Hallucination is flagged if groundedness is low
        hallucination_score = float(1.0 - groundedness)
        
        # Pass status requires relevance and groundedness
        status = "passed" if groundedness >= 0.5 and relevance >= 0.3 else "flagged"
        
        return {
            "groundedness": groundedness,
            "relevance": relevance,
            "hallucination_score": hallucination_score,
            "status": status
        }
