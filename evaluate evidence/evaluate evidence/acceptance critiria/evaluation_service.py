"""
Logique métier d'évaluation Acceptance Criteria — indépendante de Streamlit.
Réutilise les mêmes prompts, JSON et générateur PDF que l'app Streamlit.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pandas as pd
from docx import Document
from openai import OpenAI

from pdf_report import generate_pdf_report

JSON_DIR = os.path.dirname(os.path.abspath(__file__))

SUPPORTED_EXTENSIONS = {"pdf", "txt", "csv", "xlsx", "xls", "docx", "png", "jpg", "jpeg"}

# Codes segment Spring Boot → préfixe de domaine JSON
SEGMENT_TO_DOMAIN_HINTS = {
    "ndi_dg": ("Data Governance", "DG"),
    "ndi_mcm": ("Metadata and Data Catalog", "MCM"),
    "ndi_dq": ("Data Quality", "DQ"),
    "ndi_do": ("Data Operations", "DO"),
    "ndi_dcm": ("Document and Content Management", "DCM"),
    "ndi_dam": ("Data Architecture and Modelling", "DAM"),
    "ndi_dsi": ("Data Sharing & Interoperability", "DSI"),
    "ndi_rmd": ("Reference and Master Data Management", "RMD"),
    "ndi_bia": ("Business Intelligence and Analytics", "BIA"),
    "ndi_dvr": ("Data Value Realization", "DVR"),
    "ndi_od": ("Open Data", "OD"),
    "ndi_foi": ("Freedom of Information", "FOI"),
    "ndi_dc": ("Data Classification", "DC"),
    "ndi_pdp": ("Personal Data Protection", "PDP"),
}

SCORE_TO_LEVEL_KEYWORDS = {
    0: ("absence of capabilities", "level 0"),
    1: ("establishing", "level 1"),
    2: ("defined", "level 2"),
    3: ("activated", "level 3"),
    4: ("managed", "level 4"),
    5: ("pioneer", "level 5"),
}


class Settings:
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "ollama")
    OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "900"))
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5vl:7b")


settings = Settings()


def _openai_client() -> OpenAI:
    return OpenAI(
        base_url=settings.OLLAMA_BASE_URL,
        api_key=settings.OLLAMA_API_KEY,
        timeout=settings.OLLAMA_TIMEOUT_SECONDS,
    )


@dataclass
class ReportHeaderMeta:
    client_full_name: Optional[str] = None
    client_email: Optional[str] = None
    project_name: Optional[str] = None
    framework: Optional[str] = None
    domain_name: Optional[str] = None
    domain_code: Optional[str] = None
    question_text: Optional[str] = None
    question_code: Optional[str] = None
    selected_score: Optional[str] = None
    maturity_level: Optional[str] = None
    evidence_file_name: Optional[str] = None
    generation_date: Optional[str] = None
    assessment_version: Optional[str] = None


@dataclass
class EvaluationContext:
    domain_name: str
    question_text: str
    level_name: str
    evidences_list: List[Dict[str, Any]]
    question_id: Optional[str] = None


@dataclass
class EvaluationResult:
    report_text: str
    pdf_bytes: bytes
    domain_name: str
    question_text: str
    level_name: str
    filename: str


class AcceptanceCriteriaError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def load_domains(json_directory: str = JSON_DIR) -> Dict[str, Any]:
    domains_data: Dict[str, Any] = {}
    if not os.path.exists(json_directory):
        return domains_data

    for filename in os.listdir(json_directory):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(json_directory, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, list):
                    data = data[0]
                domain_name = data.get("Domain", filename.replace(".json", ""))
                domains_data[domain_name] = data
        except Exception:
            continue
    return domains_data


def _normalize(text: str) -> str:
    t = (text or "").lower().strip()
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _segment_code_from_question(question_code: Optional[str]) -> Optional[str]:
    if not question_code:
        return None
    code = question_code.strip().lower()
    # ndi_dg_01 -> ndi_dg
    m = re.match(r"^(ndi_[a-z]+)", code)
    return m.group(1) if m else None


def resolve_domain(
    domains_data: Dict[str, Any],
    domain_name: Optional[str] = None,
    domain_code: Optional[str] = None,
    question_code: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    if not domains_data:
        raise AcceptanceCriteriaError(
            "Aucun fichier JSON d'Acceptance Criteria n'a été trouvé.",
            status_code=500,
        )

    keys = list(domains_data.keys())

    # 1) Exact / fuzzy domain name
    if domain_name and domain_name.strip():
        needle = _normalize(domain_name)
        for key in keys:
            kn = _normalize(key)
            if needle == kn or needle in kn or kn in needle:
                return key, domains_data[key]
            # strip trailing "domain"
            kn2 = re.sub(r"\s+domain$", "", kn)
            needle2 = re.sub(r"\s+domain$", "", needle)
            if needle2 and (needle2 == kn2 or needle2 in kn2 or kn2 in needle2):
                return key, domains_data[key]

    # 2) Segment code hint from question_code
    segment = _segment_code_from_question(question_code)
    if segment and segment in SEGMENT_TO_DOMAIN_HINTS:
        hint_name, hint_code = SEGMENT_TO_DOMAIN_HINTS[segment]
        for key in keys:
            kn = _normalize(key)
            if _normalize(hint_name) in kn or hint_code.lower() in kn.split():
                return key, domains_data[key]

    # 3) Explicit domain_code (DG, MCM, …)
    if domain_code and domain_code.strip():
        code = domain_code.strip().upper()
        for key in keys:
            # Question_ID prefixes like DG.MQ.1
            questions = domains_data[key].get("Questions") or []
            if questions:
                qid = str(questions[0].get("Question_ID", ""))
                if qid.upper().startswith(code + ".") or qid.upper().startswith(code):
                    return key, domains_data[key]
            if code.lower() in _normalize(key).split():
                return key, domains_data[key]

    raise AcceptanceCriteriaError(
        "Domaine introuvable pour les Acceptance Criteria fournis.",
        status_code=422,
    )


def resolve_question(
    domain_json: Dict[str, Any],
    question_text: Optional[str] = None,
    question_code: Optional[str] = None,
) -> Dict[str, Any]:
    questions = domain_json.get("Questions") or []
    if not questions:
        raise AcceptanceCriteriaError(
            "Aucune question n'est définie pour ce domaine.",
            status_code=422,
        )

    # Match by Question_ID if question_code looks like DG.MQ.1
    if question_code and "." in question_code:
        for q in questions:
            if str(q.get("Question_ID", "")).strip().upper() == question_code.strip().upper():
                return q

    # Match by index: ndi_dg_01 -> index 0
    if question_code:
        m = re.search(r"_(\d+)$", question_code.strip())
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(questions):
                return questions[idx]

    # Fuzzy match on question text
    if question_text and question_text.strip():
        needle = _normalize(question_text)
        best = None
        best_score = 0
        for q in questions:
            qtext = _normalize(str(q.get("Question", "")))
            if not qtext:
                continue
            if needle == qtext:
                return q
            # token overlap
            n_tokens = set(needle.split())
            q_tokens = set(qtext.split())
            if not n_tokens or not q_tokens:
                continue
            overlap = len(n_tokens & q_tokens) / max(len(n_tokens), 1)
            if overlap > best_score:
                best_score = overlap
                best = q
        if best is not None and best_score >= 0.45:
            return best

    raise AcceptanceCriteriaError(
        "Question introuvable dans les Acceptance Criteria du domaine.",
        status_code=422,
    )


def resolve_level(
    question: Dict[str, Any],
    selected_score: Optional[int] = None,
    maturity_level: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    levels = question.get("Levels") or []
    if not levels:
        raise AcceptanceCriteriaError(
            "Aucun niveau de maturité n'est défini pour cette question.",
            status_code=422,
        )

    if maturity_level and maturity_level.strip():
        needle = _normalize(maturity_level)
        for lvl in levels:
            name = str(lvl.get("Level_Name", ""))
            nn = _normalize(name)
            if needle == nn or needle in nn or nn in needle:
                return name, lvl.get("Evidences") or []

    if selected_score is not None:
        keywords = SCORE_TO_LEVEL_KEYWORDS.get(int(selected_score), ())
        for lvl in levels:
            name = str(lvl.get("Level_Name", ""))
            nn = _normalize(name)
            if f"level {int(selected_score)}" in nn:
                return name, lvl.get("Evidences") or []
            if any(k in nn for k in keywords):
                return name, lvl.get("Evidences") or []

    raise AcceptanceCriteriaError(
        "Acceptance Criterion / niveau de maturité introuvable pour le score sélectionné.",
        status_code=422,
    )


def resolve_evaluation_context(
    domains_data: Dict[str, Any],
    *,
    domain_name: Optional[str] = None,
    domain_code: Optional[str] = None,
    question_text: Optional[str] = None,
    question_code: Optional[str] = None,
    selected_score: Optional[int] = None,
    maturity_level: Optional[str] = None,
) -> EvaluationContext:
    resolved_domain_name, domain_json = resolve_domain(
        domains_data,
        domain_name=domain_name,
        domain_code=domain_code,
        question_code=question_code,
    )
    question = resolve_question(
        domain_json,
        question_text=question_text,
        question_code=question_code,
    )
    level_name, evidences = resolve_level(
        question,
        selected_score=selected_score,
        maturity_level=maturity_level,
    )
    if not evidences:
        raise AcceptanceCriteriaError(
            "Aucun Acceptance Criterion n'est défini pour ce niveau.",
            status_code=422,
        )
    return EvaluationContext(
        domain_name=resolved_domain_name,
        question_text=str(question.get("Question") or question_text or ""),
        level_name=level_name,
        evidences_list=evidences,
        question_id=str(question.get("Question_ID") or "") or None,
    )


def process_file_bytes(filename: str, content: bytes) -> Dict[str, Any]:
    if content is None or len(content) == 0:
        raise AcceptanceCriteriaError("Le fichier est vide.", status_code=422)

    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise AcceptanceCriteriaError(
            f"Type de fichier non accepté: .{file_ext or 'inconnu'}.",
            status_code=422,
        )

    result: Dict[str, Any] = {"type": "text", "content": ""}
    stream = io.BytesIO(content)

    try:
        if file_ext == "pdf":
            doc = fitz.open(stream=content, filetype="pdf")
            extracted_text = [page.get_text("text") for page in doc]
            result["content"] = "\n".join(extracted_text)
        elif file_ext in ["txt", "csv"]:
            result["content"] = content.decode("utf-8", errors="replace")
        elif file_ext in ["xlsx", "xls"]:
            df = pd.read_excel(stream)
            result["content"] = df.to_markdown(index=False)
        elif file_ext == "docx":
            doc = Document(stream)
            result["content"] = "\n".join([para.text for para in doc.paragraphs])
        elif file_ext in ["png", "jpg", "jpeg"]:
            result["type"] = "image"
            result["content"] = base64.b64encode(content).decode("utf-8")
            result["mime_type"] = f"image/{'jpeg' if file_ext == 'jpg' else file_ext}"
    except AcceptanceCriteriaError:
        raise
    except Exception as exc:
        raise AcceptanceCriteriaError(
            f"Erreur lors de la lecture du fichier : {exc}",
            status_code=422,
        ) from exc

    return result


def evaluate_evidence_with_llm(
    question_text: str,
    target_level: str,
    evidences_list: List[Dict[str, Any]],
    file_data: Dict[str, Any],
    *,
    client: Optional[OpenAI] = None,
) -> str:
    if file_data.get("type") == "error":
        raise AcceptanceCriteriaError(str(file_data.get("content") or "Fichier invalide."), 422)

    system_prompt = (
        "Vous êtes un auditeur gouvernemental expert en gouvernance des données (NDMO). "
        "Votre tâche est d'auditer avec une rigueur absolue un document d'évidence par rapport à des critères stricts. "
        "Soyez direct, factuel, et ne justifiez votre réponse qu'en vous basant sur le document fourni."
    )

    evidences_text = ""
    for idx, ev in enumerate(evidences_list, start=1):
        ev_title = ev.get("Acceptance_Evidence", "Non spécifié")
        ev_criteria = "\n".join(ev.get("Acceptance_Criteria", []))
        evidences_text += (
            f"\n**Acceptance Evidence {idx} :** {ev_title}\n"
            f"**Critères :**\n{ev_criteria}\n"
        )

    base_prompt = f"""
**Contexte de l'Audit :**
* **Question d'évaluation :** {question_text}
* **Niveau de Maturité Cible :** {target_level}

**Exigences à vérifier :**
{evidences_text}

**Instructions :**
Analysez le contenu fourni ci-dessous. Répondez EXACTEMENT avec la structure suivante :

### 1. Évaluation Globale
**Résultat :** [OUI ou NON]
**Pourcentage :** [ex: 100%, 50%]
**Justification :** [Une phrase justifiant le résultat global.]

### 2. Détail par Preuve
[Pour chaque Preuve Requise :]
#### Preuve : [Copier le nom de la preuve]
**Statut :** [Satisfait / Partiellement Satisfait / Non Satisfait]
(Obligatoire pour chaque preuve. N'omettez jamais la ligne Statut.)

**Critères Satisfaits :**
- [Nom exact du critère] : [Information concrète réellement trouvée dans le document (citation courte, titre de section, valeur, date, version, etc.)]

**Critères Non Satisfaits (Manquants) :**
- [Nom exact du critère] : [Ce qui manque concrètement dans le document]
(Si aucun critère manquant, laissez cette liste ENTIÈREMENT VIDE — n'écrivez aucune puce, ni *, ni None, ni —, ni « Aucun critère non satisfait ».)

Règles importantes pour les listes de critères :
- Chaque puce DOIT suivre le format : Critère : Information trouvée (sur une seule ligne, sans sous-puces).
- L'information trouvée doit provenir uniquement du document analysé (ne jamais inventer).
- Ne recopiez pas toute la synthèse dans chaque ligne.
- Ne changez ni le résultat OUI/NON, ni le pourcentage, ni le statut global de chaque preuve.
- N'utilisez jamais un astérisque seul (*) comme critère.
- Terminez toujours toutes les phrases (ne tronquez pas en milieu de phrase).
- Couvrez TOUTES les preuves requises avant la conclusion.

### 3. Conclusion
Rédigez 4 à 8 phrases en français résumant uniquement : décision globale, taux de conformité, preuves satisfaites, critères manquants éventuels, réserves, et niveau de maturité évalué. Ne laissez jamais cette section vide.

**Contenu à analyser :**
"""

    if file_data["type"] == "text":
        content_text = file_data["content"][:20000]
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{base_prompt}\n---\n{content_text}\n---"},
        ]
    elif file_data["type"] == "image":
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": base_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{file_data['mime_type']};base64,{file_data['content']}"
                        },
                    },
                ],
            },
        ]
    else:
        raise AcceptanceCriteriaError("Type de contenu non supporté pour l'évaluation.", 422)

    llm = client or _openai_client()
    try:
        response = llm.chat.completions.create(
            model=settings.OLLAMA_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=4500,
        )
        text = response.choices[0].message.content
        if not text or not str(text).strip():
            raise AcceptanceCriteriaError("L'analyse IA a renvoyé une réponse vide.", 502)
        return str(text)
    except AcceptanceCriteriaError:
        raise
    except Exception as exc:
        raise AcceptanceCriteriaError(
            f"Erreur d'analyse IA (Ollama). Vérifiez qu'Ollama tourne avec le modèle "
            f"`{settings.OLLAMA_MODEL}`. Détails : {exc}",
            status_code=504,
        ) from exc


def build_safe_pdf_filename(
    client_name: Optional[str],
    project_name: Optional[str],
    evidence_name: Optional[str],
) -> str:
    def slug(value: Optional[str], fallback: str) -> str:
        raw = (value or fallback).strip().lower()
        raw = re.sub(r"[^\w\-.]+", "-", raw, flags=re.UNICODE)
        raw = re.sub(r"-{2,}", "-", raw).strip("-._")
        return raw[:60] or fallback

    name = (
        f"acceptance-criteria-{slug(client_name, 'client')}-"
        f"{slug(project_name, 'projet')}-"
        f"{slug(evidence_name, 'evidence')}.pdf"
    )
    return name.replace("\\", "_").replace("/", "_")


def run_evaluation_and_build_pdf(
    *,
    filename: str,
    content: bytes,
    domain_name: Optional[str] = None,
    domain_code: Optional[str] = None,
    question_text: Optional[str] = None,
    question_code: Optional[str] = None,
    selected_score: Optional[int] = None,
    maturity_level: Optional[str] = None,
    header: Optional[ReportHeaderMeta] = None,
    llm_client: Optional[OpenAI] = None,
    domains_data: Optional[Dict[str, Any]] = None,
) -> EvaluationResult:
    domains = domains_data if domains_data is not None else load_domains()
    ctx = resolve_evaluation_context(
        domains,
        domain_name=domain_name,
        domain_code=domain_code,
        question_text=question_text,
        question_code=question_code,
        selected_score=selected_score,
        maturity_level=maturity_level,
    )
    file_data = process_file_bytes(filename, content)
    report_text = evaluate_evidence_with_llm(
        question_text=ctx.question_text,
        target_level=ctx.level_name,
        evidences_list=ctx.evidences_list,
        file_data=file_data,
        client=llm_client,
    )

    meta = header or ReportHeaderMeta()
    pdf_bytes = generate_pdf_report(
        report_text,
        ctx.domain_name,
        ctx.question_text,
        ctx.level_name,
        header_meta={
            "client_full_name": meta.client_full_name,
            "client_email": meta.client_email,
            "project_name": meta.project_name,
            "framework": meta.framework or "NDI",
            "domain_name": meta.domain_name or ctx.domain_name,
            "domain_code": meta.domain_code,
            "question_text": meta.question_text or ctx.question_text,
            "question_code": meta.question_code,
            "selected_score": meta.selected_score,
            "maturity_level": meta.maturity_level or ctx.level_name,
            "evidence_file_name": meta.evidence_file_name or filename,
            "generation_date": meta.generation_date,
            "assessment_version": meta.assessment_version,
        },
    )
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        raise AcceptanceCriteriaError("Erreur de génération PDF.", status_code=502)

    out_name = build_safe_pdf_filename(
        meta.client_full_name,
        meta.project_name,
        meta.evidence_file_name or filename,
    )
    return EvaluationResult(
        report_text=report_text,
        pdf_bytes=pdf_bytes,
        domain_name=ctx.domain_name,
        question_text=ctx.question_text,
        level_name=ctx.level_name,
        filename=out_name,
    )
