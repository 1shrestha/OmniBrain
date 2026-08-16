from typing import Dict, Any

class SQLAgent:
    def __init__(self, is_mock: bool = True):
        self.is_mock = is_mock

    def run(self, query: str) -> Dict[str, Any]:
        # Return a deterministic mock numeric summary for demo/testing
        if self.is_mock:
            return {"answer": "Mock SQL: Average stock price is $123.45"}
        # Real implementation would translate query to SQL and execute against a DB
        return {"answer": "SQL Agent (real) not implemented in demo"}
