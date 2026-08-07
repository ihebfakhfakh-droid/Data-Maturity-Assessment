"""Tests for the PDF report FastAPI endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _minimal_payload() -> dict:
    return {
        "targetScore": 3.0,
        "currentScores": {
            "DG.MQ.1": 2,
            "DG.MQ.2": 2,
            "DG.MQ.3": 2,
            "DG.MQ.4": 2,
            "DQ.MQ.1": 1,
            "DQ.MQ.2": 1,
            "DQ.MQ.3": 1,
            "DQ.MQ.4": 1,
            "MCM.MQ.1": 3,
            "MCM.MQ.2": 3,
            "MCM.MQ.3": 3,
        },
        "projectName": "Projet Demo",
        "clientName": "Client Demo",
        "versionNumber": 2,
        "framework": "NDI",
    }


def test_generate_report_returns_pdf():
    response = client.post("/api/recommendations/generate-report", json=_minimal_payload())
    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert "rapport-recommandations" in disposition


def test_generate_report_rejects_empty_scores():
    response = client.post(
        "/api/recommendations/generate-report",
        json={"targetScore": 3.0, "currentScores": {}},
    )
    assert response.status_code == 400


def test_generate_report_accepts_legacy_question_codes():
    payload = {
        "targetScore": 3.0,
        "currentScores": {
            "ndi_dg_01": 2,
            "ndi_dg_02": 2,
            "ndi_dg_03": 2,
            "ndi_dg_04": 2,
            "ndi_dq_01": 1,
            "ndi_dq_02": 1,
            "ndi_dq_03": 1,
            "ndi_dq_04": 1,
        },
        "projectName": "Legacy",
        "versionNumber": 1,
    }
    response = client.post("/api/recommendations/generate-report", json=payload)
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
