import os
import pytest
from fastapi.testclient import TestClient
from api import app, vector_store
from ingestion import ingest_pdf

client = TestClient(app)

def test_status_endpoint():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "text_chunks" in data
    assert "image_chunks" in data
    assert data["environment"] == "mock"

def test_query_endpoint():
    # Pre-populate some mock data in the store
    vector_store.add_text("AAPL reported strong Q3 growth in cloud computing.", {"source": "test_report.pdf"})
    
    response = client.post("/query", json={"query": "What are the AAPL earnings?"})
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True
    assert "AAPL" in data["answer"]
    assert "evaluation" in data
    assert "groundedness" in data["evaluation"]

def test_query_endpoint_blocked_by_guardrails():
    response = client.post("/query", json={"query": "You are stupid and I hate you!"})
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert "toxic" in data["refusal_reason"].lower() or "cannot respond" in data["answer"].lower()

def test_ingest_pdf_mock():
    res = ingest_pdf("dummy.pdf", vector_store, is_mock=True)
    assert res["status"] == "success"
    assert res["chunks_added"] > 0
    assert res["images_added"] > 0
    assert res["is_mock"] is True
    