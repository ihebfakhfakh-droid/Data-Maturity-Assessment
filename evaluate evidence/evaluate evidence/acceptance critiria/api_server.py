"""
API FastAPI pour l'évaluation Acceptance Criteria.
Appelée uniquement par Spring Boot (jamais par React directement).
Indépendante de Streamlit (pas de session_state / UI Streamlit).
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response

from evaluation_service import (
    AcceptanceCriteriaError,
    ReportHeaderMeta,
    load_domains,
    run_evaluation_and_build_pdf,
)

APP_PORT = int(os.environ.get("ACCEPTANCE_CRITERIA_PORT", "8003"))

app = FastAPI(
    title="Acceptance Criteria Evaluation Service",
    description=(
        "Microservice d'évaluation des éléments de preuve selon les Acceptance Criteria NDI. "
        "Génère un rapport PDF. Conçu pour être appelé par PFEBACKEND (Spring Boot)."
    ),
    version="1.0.0",
)


@app.get("/health")
def health():
    domains = load_domains()
    return {
        "status": "ok",
        "domains_loaded": len(domains),
        "streamlit_required": False,
    }


def _opt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _parse_score(raw: Optional[str]) -> Optional[int]:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(str(raw).strip())
    except ValueError as exc:
        raise AcceptanceCriteriaError(
            "Le score sélectionné doit être un entier (0..5).",
            status_code=400,
        ) from exc


@app.post("/api/acceptance-criteria/report")
async def generate_acceptance_criteria_report(
    file: UploadFile = File(...),
    original_filename: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    framework: Optional[str] = Form(None),
    domain_name: Optional[str] = Form(None),
    domain_code: Optional[str] = Form(None),
    question_text: Optional[str] = Form(None),
    question_code: Optional[str] = Form(None),
    selected_score: Optional[str] = Form(None),
    maturity_level: Optional[str] = Form(None),
    client_full_name: Optional[str] = Form(None),
    client_email: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    assessment_version: Optional[str] = Form(None),
    generation_date: Optional[str] = Form(None),
    evidence_file_name: Optional[str] = Form(None),
):
    try:
        raw = await file.read()
        filename = (
            _opt(original_filename)
            or _opt(evidence_file_name)
            or _opt(file.filename)
            or "evidence.bin"
        )
        score = _parse_score(selected_score)
        if not _opt(domain_name) and not _opt(domain_code) and not _opt(question_code):
            raise AcceptanceCriteriaError(
                "Au moins domain_name, domain_code ou question_code est requis.",
                status_code=400,
            )
        if score is None and not _opt(maturity_level):
            raise AcceptanceCriteriaError(
                "selected_score ou maturity_level est requis.",
                status_code=400,
            )

        header = ReportHeaderMeta(
            client_full_name=_opt(client_full_name),
            client_email=_opt(client_email),
            project_name=_opt(project_name),
            framework=_opt(framework),
            domain_name=_opt(domain_name),
            domain_code=_opt(domain_code),
            question_text=_opt(question_text),
            question_code=_opt(question_code),
            selected_score=str(score) if score is not None else None,
            maturity_level=_opt(maturity_level),
            evidence_file_name=_opt(evidence_file_name) or filename,
            generation_date=_opt(generation_date),
            assessment_version=_opt(assessment_version),
        )

        result = run_evaluation_and_build_pdf(
            filename=filename,
            content=raw,
            domain_name=_opt(domain_name),
            domain_code=_opt(domain_code),
            question_text=_opt(question_text),
            question_code=_opt(question_code),
            selected_score=score,
            maturity_level=_opt(maturity_level),
            header=header,
        )

        return Response(
            content=result.pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"',
            },
        )
    except AcceptanceCriteriaError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message, "detail": exc.message, "status": exc.status_code},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "message": f"Erreur interne du microservice Acceptance Criteria: {exc}",
                "detail": str(exc),
                "status": 500,
            },
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=APP_PORT, reload=False)
