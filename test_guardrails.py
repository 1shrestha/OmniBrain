import pytest
from guardrails import GuardrailsManager

def test_input_guardrail_toxicity():
    """Verifies that the toxic inputs are blocked by input guardrails."""
    gm = GuardrailsManager(is_mock=True)
    res = gm.validate_input("You are stupid and I hate you!")
    assert res["allowed"] is False
    assert "hostile or toxic" in res["refusal"]

def test_input_guardrail_off_topic():
    """Verifies that off-topic inputs are blocked by input guardrails."""
    gm = GuardrailsManager(is_mock=True)
    res = gm.validate_input("Can you write a poem about flowers and tell me a joke?")
    assert res["allowed"] is False
    assert "configured to only answer" in res["refusal"]

def test_input_guardrail_allowed():
    """Verifies that valid financial queries are allowed by input guardrails."""
    gm = GuardrailsManager(is_mock=True)
    res = gm.validate_input("What is the Q3 balance sheet of Apple Inc.?")
    assert res["allowed"] is True
    assert res["refusal"] == ""

def test_output_guardrail_replacement():
    """Verifies that high-risk/non-compliant outputs are sanitized by output guardrails."""
    gm = GuardrailsManager(is_mock=True)
    
    # Non-compliant output claiming guaranteed returns
    raw_response = "We ensure guaranteed 100% returns on this stock option."
    res = gm.validate_output(raw_response)
    assert res["allowed"] is False
    assert "Disclaimer: Investment involves risks" in res["replacement"]

    # Compliant output
    valid_response = "The stock exhibits stable upward growth."
    res_valid = gm.validate_output(valid_response)
    assert res_valid["allowed"] is True
    assert res_valid["replacement"] == valid_response
