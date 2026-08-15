"""
OmniBrain Monitoring Module
Author: Sowbarnika
Role: Langfuse Telemetry & Monitoring Setup

This module configures and manages Langfuse callbacks for tracing LLM execution,
agent actions, state transitions, latency, and input/output token usage.
"""

from config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL, IS_MOCK

try:
    from langfuse.callback import CallbackHandler
except ImportError:
    CallbackHandler = None

def get_langfuse_callback():
    """Initializes and returns a Langfuse CallbackHandler if credentials exist and mock is disabled."""
    # Validate keys are not template placeholders
    has_valid_pub = LANGFUSE_PUBLIC_KEY and "your_" not in LANGFUSE_PUBLIC_KEY and "pk-lf-..." not in LANGFUSE_PUBLIC_KEY
    has_valid_sec = LANGFUSE_SECRET_KEY and "your_" not in LANGFUSE_SECRET_KEY and "sk-lf-..." not in LANGFUSE_SECRET_KEY
    
    if not IS_MOCK and has_valid_pub and has_valid_sec and CallbackHandler is not None:
        try:
            return CallbackHandler(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_BASE_URL
            )
        except Exception as e:
            print(f"Failed to initialize Langfuse callbacks: {e}")
            return None
    return None
