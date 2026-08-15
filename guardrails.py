"""
OmniBrain Guardrails Module
Author: Sowbarnika
Role: AI Safety & NeMo Guardrails Integration

This module validates incoming user prompts (Input Guardrails) and outgoing LLM responses
(Output Guardrails) to ensure strict adherence to financial domain scope, non-toxicity,
and compliance with investment disclaimer safety checks.
"""

import os
from typing import Dict, Any
from config import IS_MOCK

# Gracefully attempt import to allow dry-run / mock modes
try:
    from nemoguardrails import LLMRails, RailsConfig
except ImportError:
    LLMRails, RailsConfig = None, None

class GuardrailsManager:
    def __init__(self, is_mock: bool = IS_MOCK):
        self.is_mock = is_mock
        self.rails = None
        
        if not self.is_mock and LLMRails is not None and RailsConfig is not None:
            try:
                config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))
                config = RailsConfig.from_path(config_path)
                self.rails = LLMRails(config)
            except Exception as e:
                print(f"NeMo Guardrails initialization failed: {e}. Falling back to mock guardrails.")
                self.is_mock = True

    def validate_input(self, user_query: str) -> Dict[str, Any]:
        """Validates input query. Returns whether it is allowed or refused."""
        query_lower = user_query.lower()
        
        # Check toxic triggers
        toxic_keywords = ["stupid", "hate you", "kill yourself"]
        for kw in toxic_keywords:
            if kw in query_lower:
                return {
                    "allowed": False,
                    "refusal": "I cannot respond to hostile or toxic remarks. Please keep the conversation professional."
                }
                
        # Check off-topic triggers
        off_topic_keywords = ["tell me a joke", "capital of france", "write a poem"]
        for kw in off_topic_keywords:
            if kw in query_lower:
                return {
                    "allowed": False,
                    "refusal": "I am configured to only answer financial and investment-related queries."
                }
                
        # Execute NeMo Guardrails check in production mode
        if not self.is_mock and self.rails is not None:
            try:
                response = self.rails.generate(messages=[{"role": "user", "content": user_query}])
                # If the rails triggered a refusal response
                if "only answer financial" in response.lower() or "hostile or toxic" in response.lower():
                    return {
                        "allowed": False,
                        "refusal": response
                    }
            except Exception as e:
                # Logs exception, falls back to allowing
                print(f"NeMo Input Guardrail error: {e}")
                
        return {
            "allowed": True,
            "refusal": ""
        }

    def validate_output(self, response_text: str) -> Dict[str, Any]:
        """Validates final generated memo for security compliance."""
        response_lower = response_text.lower()
        if "guarante" in response_lower and ("return" in response_lower or "profit" in response_lower):
            return {
                "allowed": False,
                "replacement": "Disclaimer: Investment involves risks. We cannot provide guaranteed returns."
            }
        return {
            "allowed": True,
            "replacement": response_text
        }
