from app.ai.langgraph_workflow import LangGraphWorkflow


def test_unified_workflow_routes_search_sql_and_vision_agents(monkeypatch):
    class FakeGeminiService:
        def __init__(self):
            self.calls = []

        def generate_response(self, question, context, temperature=None):
            self.calls.append((question, context, temperature))
            return "Unified OmniBrain answer"

    monkeypatch.setattr("app.ai.langgraph_workflow.GeminiService", FakeGeminiService)

    workflow = LangGraphWorkflow()
    result = workflow.run(
        question="Analyze the balance sheet chart and compare it to revenue trends",
        context="Revenue grew 12% in 2024 and the balance sheet shows strong cash reserves.",
        temperature=0.0,
    )

    assert result["answer"] == "Unified OmniBrain answer"
    assert "search_agent" in result["agents"]
    assert "sql_agent" in result["agents"]
    assert "vision_agent" in result["agents"]
