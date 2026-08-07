"""Tests du microservice Acceptance Criteria (sans Streamlit)."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api_server import app
from evaluation_service import (
    AcceptanceCriteriaError,
    build_safe_pdf_filename,
    load_domains,
    process_file_bytes,
    resolve_evaluation_context,
    run_evaluation_and_build_pdf,
)
from pdf_report import generate_pdf_report

ROOT = Path(__file__).resolve().parent
SAMPLE_REPORT = """
### 1. Évaluation Globale
**Résultat :** OUI
**Pourcentage :** 100%
**Justification :** Le document couvre tous les critères requis pour le niveau Defined.

### 2. Détail par Preuve
#### Preuve : The approved DM & PDP Strategy.
**Statut :** Satisfait

**Critères Satisfaits :**
- Current challenges in DM. : Section 2.1 lists current DM challenges and gaps.
- The DM & PDP Vision, Mission, and Strategic Objectives. : Vision/Mission stated on page 4.
- Strategic and operational performance indicators with targets. : KPIs table with 3-year targets included.

**Critères Non Satisfaits (Manquants) :**
- None

#### Preuve : The DM guiding principles.
**Statut :** Satisfait

**Critères Satisfaits :**
- The principles underlying the culture of DM. : Guiding principles section present and approved.

**Critères Non Satisfaits (Manquants) :**

#### Preuve : Data strategy approval decision letter.
**Statut :** Satisfait

**Critères Satisfaits :**
- Approval decision by the Data Management Committee. : Signed approval letter dated 2024-03-12.

**Critères Non Satisfaits (Manquants) :**
-

### 3. Conclusion
Le niveau Defined est atteint. Aucun critère manquant n'a été identifié.
"""


@pytest.fixture(scope="module")
def domains():
    data = load_domains(str(ROOT))
    assert data, "JSON domains must load"
    return data


def test_imports_and_no_streamlit_session_dependency():
    import evaluation_service
    import api_server
    import pdf_report

    src = Path(evaluation_service.__file__).read_text(encoding="utf-8")
    assert "import streamlit" not in src
    assert "st.session_state" not in src
    api_src = Path(api_server.__file__).read_text(encoding="utf-8")
    assert "import streamlit" not in api_src
    assert "from streamlit" not in api_src
    assert "st.session_state" not in api_src
    assert pdf_report.generate_pdf_report


def test_load_json_domains(domains):
    assert any("Governance" in k for k in domains.keys())


def test_resolve_acceptance_criteria_by_question_code(domains):
    ctx = resolve_evaluation_context(
        domains,
        question_code="ndi_dg_01",
        selected_score=1,
    )
    assert "Governance" in ctx.domain_name
    assert ctx.evidences_list
    assert "Level 1" in ctx.level_name or "Establishing" in ctx.level_name


def test_criterion_not_found(domains):
    with pytest.raises(AcceptanceCriteriaError) as exc:
        resolve_evaluation_context(
            domains,
            question_code="ndi_dg_01",
            selected_score=99,
        )
    assert exc.value.status_code == 422


def test_process_png_and_jpg():
    # Minimal valid-ish payloads: process_file_bytes treats images as base64
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    jpg = b"\xff\xd8\xff" + b"\x00" * 32
    png_data = process_file_bytes("proof.png", png)
    jpg_data = process_file_bytes("proof.jpg", jpg)
    assert png_data["type"] == "image"
    assert jpg_data["type"] == "image"
    assert png_data["mime_type"] == "image/png"
    assert jpg_data["mime_type"] == "image/jpeg"


def test_invalid_type():
    with pytest.raises(AcceptanceCriteriaError) as exc:
        process_file_bytes("malware.exe", b"MZ")
    assert exc.value.status_code == 422


def test_empty_file():
    with pytest.raises(AcceptanceCriteriaError) as exc:
        process_file_bytes("empty.png", b"")
    assert exc.value.status_code == 422


def test_pdf_generation_contains_pdf_magic_and_header():
    pdf = generate_pdf_report(
        SAMPLE_REPORT,
        "Data Governance Domain",
        "Has the entity established a strategy?",
        "Level 2: Defined",
        header_meta={
            "client_full_name": "Client Demo",
            "client_email": "client@example.com",
            "project_name": "Projet Alpha",
            "framework": "NDI",
            "domain_code": "DG",
            "question_code": "ndi_dg_01",
            "selected_score": "2",
            "evidence_file_name": "DG-Q1-level2-validated.pdf",
            "generation_date": "23/07/2026 17:00",
            "assessment_version": "3",
        },
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500

    import fitz

    doc = fitz.open(stream=pdf, filetype="pdf")
    text = "\n".join(page.get_text("text") for page in doc)
    # Header preserved
    assert "Client Demo" in text
    assert "client@example.com" in text
    assert "Projet Alpha" in text
    assert "DG-Q1-level2-validated.pdf" in text
    # Business result preserved
    assert "OUI" in text
    assert "100%" in text or "100 %" in text
    # Information trouvée filled (not all dashes)
    assert "Section 2.1 lists current DM challenges" in text
    assert "Vision/Mission stated on page 4" in text
    assert "Signed approval letter dated 2024-03-12" in text
    # Empty missing criteria normalized
    assert "Aucun critère manquant ou non démontré" in text
    assert "None |" not in text
    # Should not have a fake empty table row of only placeholders for missing
    assert text.count("Information trouvée") >= 1


def test_normalize_criteria_filters_none_and_parses_info():
    from pdf_report import criterion_to_row, normalize_criteria_rows

    rows = normalize_criteria_rows(
        [
            "Current challenges in DM. : Section 2.1 lists challenges.",
            "None",
            "—",
            "-",
            "*",
            "* | —",
            "- *",
            None,
            "",
            ["*"],
            {"criterion": "*", "informationFound": "—"},
            {"criterion": "Vision", "informationFound": "Page 4"},
            {"criterion": "KPI", "extractedInformation": "Table 3 targets"},
            "Policy name | Information trouvée : Data Governance Policy",
            "Accountability : Rôles RACI définis pour chaque domaine DM.",
        ]
    )
    assert len(rows) == 5
    assert rows[0].criterion.startswith("Current challenges")
    assert "Section 2.1" in rows[0].information_found
    assert rows[1].criterion == "Vision"
    assert rows[1].information_found == "Page 4"
    assert "Table 3" in rows[2].information_found
    assert "Data Governance Policy" in rows[3].information_found
    assert "Accountability" in rows[4].criterion or "Responsabilité" in rows[4].criterion
    assert "RACI" in rows[4].information_found

    empty = normalize_criteria_rows(["None", "—", None, "", "*", "* | —", ["None"], ["—"]])
    assert empty == []

    plain = criterion_to_row("Only criterion name without info")
    assert plain.criterion.startswith("Only criterion")
    assert plain.information_found == ""


def test_fake_star_missing_does_not_appear_in_pdf_or_conclusion():
    from pdf_report import generate_pdf_report, parse_report_data

    report = """
### 1. Évaluation Globale
**Résultat :** OUI
**Pourcentage :** 100%
**Justification :** Tous les critères sont démontrés.

### 2. Détail par Preuve
#### Preuve : The approved DM & PDP Strategy.
**Statut :** Satisfait
**Critères Satisfaits :**
- Current challenges in DM. : Section 2.1 lists challenges.
- Accountability : Matrix RACI présente en annexe B avec responsables nommés.
**Critères Non Satisfaits (Manquants) :**
- *
- * | —
- None

### 3. Conclusion
La décision est OUI à 100 %. Critères manquants ou non démontrés : *. 2 élément(s) de preuve satisfait(s).
"""
    data = parse_report_data(report, "Data Governance Domain", "Q?", "Level 2: Defined")
    assert data.evidences[0].criteres_non_satisfaits == []
    assert "*" not in data.conclusion
    assert "élément(s)" not in data.conclusion
    assert "éléments de preuve satisfaits" in data.conclusion or "élément de preuve satisfait" in data.conclusion

    pdf = generate_pdf_report(
        report,
        "Data Governance Domain",
        "Q?",
        "Level 2: Defined",
        header_meta={"evidence_file_name": "DG-Q1-level2-validated.pdf", "client_full_name": "Client Demo"},
    )
    import fitz

    doc = fitz.open(stream=pdf, filetype="pdf")
    text = "\n".join(page.get_text("text") for page in doc)
    assert "Aucun critère manquant ou non démontré" in text
    assert "None |" not in text
    assert "* |" not in text
    assert "élément(s)" not in text
    assert "Matrix RACI" in text or "RACI" in text
    # Conclusion should not sit alone on a nearly empty 3rd page when content is short
    assert doc.page_count <= 2


def test_conclusion_never_empty_and_status_inferred():
    from pdf_report import generate_pdf_report, parse_report_data

    # Simulates truncated / imperfect LLM output: no ### 3, evidence 3 without **Statut**
    truncated = """
### 1. Évaluation Globale
**Résultat :** OUI
**Pourcentage :** 100%
**Justification :** Le document couvre les exigences du niveau Defined.

### 2. Détail par Preuve
#### Preuve : The approved DM & PDP Strategy.
**Statut :** Satisfait
**Critères Satisfaits :**
- Current challenges in DM. : Section 2.1 lists challenges.
**Critères Non Satisfaits (Manquants) :**

#### Preuve : The DM guiding principles.
**Statut :** Satisfait
**Critères Satisfaits :**
- Guiding principles : Present in section 3.
**Critères Non Satisfaits (Manquants) :**

#### Preuve : Data strategy approval decision letter.
Critères Satisfaits :
- Approval decision : Signed letter dated 2024-03-12.
Critères Non Satisfaits (Manquants) :
"""
    data = parse_report_data(
        truncated,
        "Data Governance Domain",
        "Has the entity established a strategy?",
        "Level 2: Defined",
    )
    assert data.conclusion
    assert data.conclusion.lower() not in {"none", "—", "-"}
    assert "100%" in data.conclusion or "OUI" in data.conclusion
    assert len(data.evidences) == 3
    assert data.evidences[2].statut == "Satisfait"  # inferred from satisfied criteria

    pdf = generate_pdf_report(
        truncated,
        "Data Governance Domain",
        "Has the entity established a strategy?",
        "Level 2: Defined",
        header_meta={
            "client_full_name": "mohsen benjmaa",
            "evidence_file_name": "DG-Q1-level2-validated.pdf",
            "framework": "NDI",
            "selected_score": "2",
        },
    )
    assert pdf.startswith(b"%PDF")
    import fitz

    text = "\n".join(page.get_text("text") for page in fitz.open(stream=pdf, filetype="pdf"))
    assert "4. Conclusion de l'audit" in text or "Conclusion de l'audit" in text
    assert "décision globale" in text.lower() or "OUI" in text
    # Title must not be alone without body keywords from deterministic conclusion
    assert "taux de conformité" in text.lower() or "100%" in text


def test_safe_filename():
    name = build_safe_pdf_filename("Client/A", "Projet\\B", "ev:1?.png")
    assert name.endswith(".pdf")
    assert "/" not in name
    assert "\\" not in name


def test_api_endpoint_with_mocked_llm(domains, monkeypatch):
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = SAMPLE_REPORT
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    def _fake_run(**kwargs):
        kwargs["llm_client"] = mock_client
        kwargs["domains_data"] = domains
        return run_evaluation_and_build_pdf(**kwargs)

    monkeypatch.setattr("api_server.run_evaluation_and_build_pdf", _fake_run)

    client = TestClient(app)
    files = {
        "file": ("proof.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64), "image/png"),
    }
    data = {
        "original_filename": "proof.png",
        "content_type": "image/png",
        "framework": "NDI",
        "domain_name": "Data Governance Domain",
        "domain_code": "DG",
        "question_code": "ndi_dg_01",
        "question_text": "strategy",
        "selected_score": "1",
        "maturity_level": "Establishing",
        "client_full_name": "Client Demo",
        "client_email": "client@example.com",
        "project_name": "Projet Alpha",
        "assessment_version": "2",
        "generation_date": "23/07/2026 17:00",
        "evidence_file_name": "proof.png",
    }
    res = client.post("/api/acceptance-criteria/report", files=files, data=data)
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.content.startswith(b"%PDF")
    assert "attachment" in res.headers.get("content-disposition", "")


def test_health_endpoint():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["streamlit_required"] is False
    assert body["domains_loaded"] > 0
