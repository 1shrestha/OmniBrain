import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from retrieval import MultiModalVectorStore
from orchestrator import OmniBrainOrchestrator
from guardrails import GuardrailsManager
from evaluation import OmniBrainEvaluator

def run_demo():
    print("==================================================")
    print("      OMNIBRAIN ORCHESTRATOR DEMO RUN             ")
    print("==================================================")
    
    # 1. Setup Vector Database with sample context
    print("[1/5] Initializing Multi-Modal Vector Database...")
    db = MultiModalVectorStore(is_mock=True)
    db.add_text(
        "Apple Inc. reported record high earnings for Q3 2026, driven by cloud computing.",
        {"source": "aapl_q3_report.txt"}
    )
    db.add_text(
        "Microsoft announced their new AI cloud division growth reached 40% YoY.",
        {"source": "msft_annual_report.txt"}
    )
    db.add_image(
        "balance_sheet.png",
        "Apple Inc. Q3 Balance Sheet showing Total Assets of $500,000 and Total Liabilities of $200,000",
        {"source": "aapl_balance_sheet_image.png"}
    )
    print("Added 2 text documents and 1 financial chart image to the index.")
    print("-" * 50)
    
    # 2. Setup Orchestrator and Guardrails
    print("[2/5] Initializing Agents, StateGraph, and Guardrails...")
    orchestrator = OmniBrainOrchestrator(db, is_mock=True)
    guardrails = GuardrailsManager(is_mock=True)
    evaluator = OmniBrainEvaluator(is_mock=True)
    print("-" * 50)
    
    # 3. Test Case 1: Valid Multi-Modal Investment Memo Generation
    query = "What is the average stock price of AAPL? Check general earnings report and the balance_sheet.png chart too."
    print(f"[3/5] User Query: '{query}'")
    
    # Run Input Guardrails
    print("\nRunning input guardrails check...")
    input_check = guardrails.validate_input(query)
    if not input_check["allowed"]:
        print(f"Blocked by Input Guardrails: {input_check['refusal']}")
        return
    print("Input allowed.")
    
    # Execute through LangGraph Orchestrator
    print("\nRunning through StateGraph orchestrator...")
    res = orchestrator.run(query, image_path="balance_sheet.png")
    
    # Run Output Guardrails
    print("Running output guardrails check...")
    output_check = guardrails.validate_output(res["final_answer"])
    final_memo = output_check["replacement"]
    if not output_check["allowed"]:
        print("Output Sanitized by Guardrails!")
    
    print("\nGenerated Final Memo:")
    print(final_memo)
    print("-" * 50)
    
    # 4. Test Case 2: Run Evaluation
    print("[4/5] Running Offline Evaluation Pipeline...")
    eval_metrics = evaluator.evaluate(query, final_memo, res["citations"])
    print(f"Metrics Results:")
    print(f"  - Groundedness Score : {eval_metrics['groundedness']:.2f}")
    print(f"  - Relevance Score    : {eval_metrics['relevance']:.2f}")
    print(f"  - Hallucination Score: {eval_metrics['hallucination_score']:.2f}")
    print(f"  - Evaluation Status  : {eval_metrics['status'].upper()}")
    print("-" * 50)
    
    # 5. Test Case 3: Guardrail Refusal Demonstrations
    print("[5/5] Demonstrating Guardrails triggers...")
    
    toxic_query = "You are stupid, I hate you."
    print(f"\nUser Query: '{toxic_query}'")
    toxic_check = guardrails.validate_input(toxic_query)
    print(f"Allowed: {toxic_check['allowed']}")
    print(f"Response: {toxic_check['refusal']}")
    
    off_topic_query = "Can you tell me a joke?"
    print(f"\nUser Query: '{off_topic_query}'")
    off_topic_check = guardrails.validate_input(off_topic_query)
    print(f"Allowed: {off_topic_check['allowed']}")
    print(f"Response: {off_topic_check['refusal']}")
    
    financial_advice = "This stock option guarantees 100% returns and profits."
    print(f"\nEvaluating Non-compliant Output: '{financial_advice}'")
    advice_check = guardrails.validate_output(financial_advice)
    print(f"Allowed: {advice_check['allowed']}")
    print(f"Sanitized Response: {advice_check['replacement']}")
    print("==================================================")

if __name__ == "__main__":
    run_demo()
