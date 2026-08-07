"""
Génération PDF du rapport d'audit — présentation uniquement.
Les résultats métier (OUI/NON, %, critères, statuts) ne sont pas altérés.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from fpdf import FPDF


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
class PdfStyles:
    PAGE_W = 210
    PAGE_H = 297
    MARGIN = 14
    CONTENT_W = PAGE_W - 2 * MARGIN

    COLOR_PRIMARY = (27, 58, 95)
    COLOR_TEXT = (45, 55, 65)
    COLOR_MUTED = (100, 110, 120)
    COLOR_LINE = (210, 218, 226)
    COLOR_CARD_BG = (248, 250, 252)
    COLOR_HEADER_BG = (27, 58, 95)
    COLOR_TABLE_HEADER = (232, 238, 245)
    COLOR_WHITE = (255, 255, 255)
    COLOR_GREEN = (27, 122, 78)
    COLOR_GREEN_BG = (232, 245, 238)
    COLOR_RED = (184, 58, 58)
    COLOR_RED_BG = (252, 235, 235)
    COLOR_ORANGE = (196, 122, 26)
    COLOR_ORANGE_BG = (255, 244, 230)

    FONT_DIR_CANDIDATES = [
        r"C:\Windows\Fonts",
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/liberation",
    ]

    COL_LEFT = 62.0
    COL_RIGHT = CONTENT_W - COL_LEFT
    ROW_H = 5.2
    BADGE_RESERVED = 42.0


DOMAIN_DISPLAY = {
    "Data Governance Domain": "Gouvernance des données",
    "Business Intelligence and Analytics Domain": "Business Intelligence et Analytique",
    "Data Architecture and Modelling Domain": "Architecture et modélisation des données",
    "Data Classification Domain": "Classification des données",
    "Data Operations Domain": "Opérations sur les données",
    "Data Quality Domain": "Qualité des données",
    "Data Sharing & Interoperability Domain": "Partage et interopérabilité des données",
    "Data Value Realization Domain": "Valorisation des données",
    "Document and Content Management Domain": "Gestion documentaire et des contenus",
    "Freedom of Information Domain": "Liberté d'information",
    "Metadata and Data Catalog Domain": "Métadonnées et catalogue de données",
    "Open Data Domain": "Données ouvertes",
    "Personal Data Protection Domain": "Protection des données personnelles",
    "Reference and Master Data Management Domain": "Données de référence et données de base",
}

LABEL_DISPLAY = {
    "evidences": "Éléments de preuve",
    "evidence": "Élément de preuve",
    "acceptance evidence": "Élément de preuve attendu",
    "policy name": "Nom de la politique",
    "release date": "Date de publication",
    "version number": "Numéro de version",
    "document control": "Contrôle du document",
    "version history": "Historique des versions",
    "terminology": "Terminologie",
    "goal": "Objectif",
    "scope of work": "Périmètre d'application",
    "guiding principles": "Principes directeurs",
    "policy statement": "Dispositions de la politique",
    "job roles & responsibilities": "Rôles et responsabilités",
    "job roles and responsibilities": "Rôles et responsabilités",
    "roles & responsibilities": "Rôles et responsabilités",
    "roles and responsibilities": "Rôles et responsabilités",
    "accountability": "Responsabilité (Accountability)",
    "related policies": "Politiques associées",
    "references": "Références",
}


def _display_domain(domain: str) -> str:
    raw = (domain or "").strip()
    if not raw:
        return ""
    fr = DOMAIN_DISPLAY.get(raw)
    if fr:
        return f"{fr} ({raw})"
    key2 = raw if raw.endswith("Domain") else f"{raw} Domain"
    fr2 = DOMAIN_DISPLAY.get(key2)
    if fr2:
        return f"{fr2} ({raw})"
    return raw


def _display_level(level: str) -> str:
    return (level or "").strip()


def _translate_label(label: str) -> str:
    key = re.sub(r"\s+", " ", (label or "").strip().lower()).replace("’", "'")
    if key in LABEL_DISPLAY:
        return LABEL_DISPLAY[key]
    for eng, fr in LABEL_DISPLAY.items():
        if key == eng or key.startswith(eng + " "):
            return fr
    return label.strip()


def _apply_display_phrases(text: str) -> str:
    if not text:
        return text
    out = text
    for eng, fr in sorted(LABEL_DISPLAY.items(), key=lambda x: len(x[0]), reverse=True):
        out = re.compile(re.escape(eng), re.IGNORECASE).sub(fr, out)
    out = re.sub(r"\bEvidences\b", "Éléments de preuve", out, flags=re.IGNORECASE)
    out = re.sub(r"\bAcceptance Evidence\b", "Élément de preuve attendu", out, flags=re.IGNORECASE)
    return out


def fix_grammar_display(text: str) -> str:
    if not text:
        return text
    t = text
    for pat, repl in (
        (r"\bAucun manque notable a été\b", "Aucun manque notable n'a été"),
        (r"\baucun manque notable a été\b", "aucun manque notable n'a été"),
        (r"\bAucune anomalie a été\b", "Aucune anomalie n'a été"),
        (r"\baucune anomalie a été\b", "aucune anomalie n'a été"),
        (r"\bAucun élément a été\b", "Aucun élément n'a été"),
        (r"\baucun élément a été\b", "aucun élément n'a été"),
        (r"\bAucun critère a été\b", "Aucun critère n'a été"),
        (r"\bIl a pas\b", "Il n'a pas"),
        (r"\bil a pas\b", "il n'a pas"),
        # Professional French plurals (remove technical "(s)")
        (
            r"(\d+)\s+élément\(s\)\s+de\s+preuve\s+satisfait\(s\)",
            lambda m: _fr_count(
                int(m.group(1)),
                "élément de preuve satisfait",
                "éléments de preuve satisfaits",
            ),
        ),
        (
            r"(\d+)\s+élément\(s\)",
            lambda m: _fr_count(int(m.group(1)), "élément", "éléments"),
        ),
        (
            r"(\d+)\s+critère\(s\)\s+satisfait\(s\)",
            lambda m: _fr_count(int(m.group(1)), "critère satisfait", "critères satisfaits"),
        ),
        (
            r"(\d+)\s+critère\(s\)\s+manquant\(s\)",
            lambda m: _fr_count(int(m.group(1)), "critère manquant", "critères manquants"),
        ),
        (
            r"(\d+)\s+autre\(s\)",
            lambda m: (
                f"{m.group(1)} autre"
                if int(m.group(1)) == 1
                else f"{m.group(1)} autres"
            ),
        ),
        (r"\b0 élément\b", "Aucun élément"),
        (r"\b0 critère\b", "Aucun critère"),
    ):
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    t = t.strip()
    if t and t[-1] not in ".!?…" and len(t) > 40 and not t.endswith(":"):
        t = t + "."
    return t


def _normalize_cmp(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s%]", "", t, flags=re.UNICODE)
    return t


@dataclass
class CriterionRow:
    criterion: str
    information_found: str = ""


@dataclass
class EvidenceBlock:
    titre: str
    statut: str
    criteres_satisfaits: List[CriterionRow] = field(default_factory=list)
    criteres_non_satisfaits: List[CriterionRow] = field(default_factory=list)


@dataclass
class ReportData:
    domain: str
    question: str
    level: str
    resultat: str = ""
    pourcentage: str = ""
    justification: str = ""
    evidences: List[EvidenceBlock] = field(default_factory=list)
    conclusion: str = ""
    raw_fallback: str = ""
    # Optional header fields from the main application (never invent missing values).
    client_full_name: str = ""
    client_email: str = ""
    project_name: str = ""
    framework: str = ""
    domain_code: str = ""
    question_code: str = ""
    selected_score: str = ""
    evidence_file_name: str = ""
    generation_date: str = ""
    assessment_version: str = ""


def _strip_md(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    for emo in ("✅", "❌", "⚠️", "💡", "📊", "🛡️", "📋", "📌", "🚀", "📎"):
        text = text.replace(emo, "")
    text = text.replace("\xa0", " ").replace("\t", " ")
    return re.sub(r"[ \t]{2,}", " ", text).strip()


_PLACEHOLDER_VALUES = {
    "",
    "-",
    "—",
    "–",
    "*",
    "•",
    "none",
    "null",
    "n/a",
    "na",
    "nil",
    "aucun",
    "aucune",
    "n/d",
    "nd",
    "non applicable",
    "not applicable",
    "{}",
    "[]",
    "aucun critere non satisfait",
    "aucun critère non satisfait",
    "aucun critere manquant",
    "aucun critère manquant",
    "aucun critere manquant ou non demontre",
    "aucun critère manquant ou non démontré",
    "pas de critere manquant",
    "pas de critère manquant",
    "no missing criteria",
    "n/a - aucun",
}


def _strip_decorative_markers(value: str) -> str:
    """Remove isolated leading/trailing markdown bullets without deleting real content."""
    text = str(value or "").strip()
    # Leading decorative markers only: "* text", "- text", "• text"
    text = re.sub(r"^([-*•]+)\s+", "", text)
    # Trailing orphan markers
    text = re.sub(r"\s+[-*•]+$", "", text)
    # Line that is only markers / pipes / dashes
    if re.fullmatch(r"[-*•|—–\s]+", text or ""):
        return ""
    return text.strip()


def _is_empty_missing_phrase(value: str) -> bool:
    """LLM often writes a prose 'none missing' line instead of leaving the list empty."""
    text = _strip_decorative_markers(_strip_md(value or "")).lower()
    text = re.sub(r"[.\s]+$", "", text)
    if text in _PLACEHOLDER_VALUES:
        return True
    patterns = (
        r"^aucun\s+crit[eè]re[s]?\s+(non\s+satisfait|manquant)",
        r"^pas\s+de\s+crit[eè]re[s]?\s+(manquant|non\s+satisfait)",
        r"^no\s+(missing|unsatisfied)\s+criteria",
        r"^none(\s+missing)?$",
    )
    return any(re.match(pat, text) for pat in patterns)


def _is_placeholder(value: Optional[str]) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
        return True
    text = _strip_decorative_markers(_strip_md(str(value)))
    text = text.strip().lower()
    text = re.sub(r"[.\s]+$", "", text)
    if text in _PLACEHOLDER_VALUES:
        return True
    if _is_empty_missing_phrase(str(value)):
        return True
    # Markdown-only leftovers such as "*", "**", "* | —"
    if re.fullmatch(r"[-*•|—–/\s]+", text or ""):
        return True
    return False


def _is_incomplete_sentence(text: str) -> bool:
    """Detect truncated fragments (e.g. ending mid-word / hanging connector)."""
    t = (text or "").strip()
    if not t:
        return True
    if len(t) < 8:
        return False
    lower = t.lower()
    # Ends with hanging French/English connectors typical of truncation
    if re.search(
        r"\b(de|du|des|le|la|les|un|une|et|ou|à|au|aux|the|of|and|or|for|with|to|including|permettant|chaque)\s*$",
        lower,
    ):
        return True
    # Ends with open paren / colon without content
    if re.search(r"[:(\[]\s*$", t):
        return True
    # Long analysis text without terminal punctuation → usually an LLM cut-off
    if len(t) > 70 and t[-1] not in ".!?…»\"'”":
        return True
    return False


def _is_section_header_without_info(criterion: str, info: str) -> bool:
    """Drop nested parent bullets like 'Strategic requirements including:' with no info."""
    crit = (criterion or "").strip()
    if info and not _is_placeholder(info) and not _is_incomplete_sentence(info):
        return False
    if crit.endswith(":") or crit.endswith(",") or crit.lower().endswith("including"):
        return True
    if re.search(r"\bincluding\s*$", crit, re.IGNORECASE):
        return True
    return False


def _fr_count(n: int, singular: str, plural: str) -> str:
    """French countable phrase without technical '(s)' markers."""
    if n <= 0:
        return f"Aucun {singular}"
    if n == 1:
        return f"1 {singular}"
    return f"{n} {plural}"


def _bullet_lines(block: str) -> List[str]:
    items = []
    for line in (block or "").split("\n"):
        raw = line.strip()
        if not raw or raw == "-":
            continue
        # Strip one or more decorative bullet prefixes ("- *", "* -", etc.)
        raw = re.sub(r"^([-*•]\s*)+", "", raw).strip()
        cleaned = _strip_decorative_markers(_strip_md(raw))
        if cleaned and not _is_placeholder(cleaned):
            items.append(cleaned)
    return _coalesce_nested_criterion_bullets(items)


def _coalesce_nested_criterion_bullets(items: List[str]) -> List[str]:
    """
    LLM often nests findings under a parent criterion:
      - Internal requirements...
        - \"Quote from document\"
    Merge pure quote / continuation lines into the previous criterion as informationFound.
    """
    out: List[str] = []
    for text in items:
        cleaned = (text or "").strip()
        if not cleaned:
            continue
        quote_only = re.fullmatch(r"[\"«“](.+?)[\"»”]\.?", cleaned, re.DOTALL)
        if quote_only and out:
            info = quote_only.group(1).strip()
            prev = out[-1]
            if re.search(r"\s*[:：]\s*\S", prev):
                out[-1] = f"{prev} {info}"
            else:
                out[-1] = f"{prev.rstrip('.')} : {info}"
            continue
        # Sub-label under a parent (Vision / Mission / Objectif) kept as its own row
        out.append(cleaned)
    return out


def _pick_info_from_dict(item: dict) -> str:
    for key in (
        "informationFound",
        "information_found",
        "foundInformation",
        "extractedInformation",
        "evidenceFound",
        "finding",
        "details",
        "justification",
        "matchedText",
        "extractedValue",
        "info",
        "value",
    ):
        if key in item and item.get(key) is not None:
            val = _strip_md(str(item.get(key))).strip()
            if val and not _is_placeholder(val):
                return val
    return ""


def criterion_to_row(text: str) -> CriterionRow:
    """
    Normalize one criterion bullet into (criterion, information_found).
    Supported formats produced by the LLM / legacy responses:
    - Critère : Information trouvée
    - Critère | Information trouvée : ...
    - Critère – Information
    - plain criterion name (information stays empty → rendered as — only if truly absent)
    """
    raw = _strip_decorative_markers(_strip_md(text or ""))
    if _is_placeholder(raw):
        return CriterionRow(criterion="", information_found="")

    # Explicit "Information trouvée"
    m_info = re.search(
        r"^(?P<crit>.+?)\s*(?:\||–|-|:)\s*Information\s+trouv[ée]e\s*:\s*(?P<info>.+)$",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if m_info:
        crit = _strip_decorative_markers(m_info.group("crit").strip(" :-|–"))
        info = _strip_decorative_markers(m_info.group("info"))
        return CriterionRow(
            criterion=_translate_label(_apply_display_phrases(crit)),
            information_found="" if _is_placeholder(info) else info,
        )

    # Critère : info  (avoid splitting URLs / times too aggressively — require short left side)
    m = re.match(r"^([^:\n]{2,160}?)\s*:\s*(.+)$", raw, re.DOTALL)
    if m:
        left, right = _strip_decorative_markers(m.group(1)), _strip_decorative_markers(m.group(2))
        if not _is_placeholder(left):
            return CriterionRow(
                criterion=_translate_label(_apply_display_phrases(left)),
                information_found="" if _is_placeholder(right) else right,
            )

    m2 = re.match(r"^([^|–\-\n]{2,160}?)\s+[|–\-]\s+(.+)$", raw, re.DOTALL)
    if m2:
        left, right = _strip_decorative_markers(m2.group(1)), _strip_decorative_markers(m2.group(2))
        if not _is_placeholder(left):
            return CriterionRow(
                criterion=_translate_label(_apply_display_phrases(left)),
                information_found="" if _is_placeholder(right) else right,
            )

    return CriterionRow(
        criterion=_translate_label(_apply_display_phrases(raw)),
        information_found="",
    )


def normalize_criteria_rows(items) -> List[CriterionRow]:
    """
    Accept list[str] | list[CriterionRow] | list[dict] | None / placeholders → clean rows.
    Never invent information_found. Drops fake missing rows like "*", "—", "None".
    """
    if items is None:
        return []
    if isinstance(items, (list, tuple, set)) and len(items) == 0:
        return []
    if isinstance(items, dict) and len(items) == 0:
        return []
    if isinstance(items, str):
        items = [items]

    rows: List[CriterionRow] = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, (list, tuple, set)):
            if len(item) == 0:
                continue
            # Flatten nested placeholder lists such as ["*"] / ["None"]
            rows.extend(normalize_criteria_rows(list(item)))
            continue
        if isinstance(item, dict) and len(item) == 0:
            continue
        if isinstance(item, CriterionRow):
            row = CriterionRow(
                criterion=_strip_decorative_markers(item.criterion or ""),
                information_found=_strip_decorative_markers(item.information_found or ""),
            )
        elif isinstance(item, dict):
            if not any(str(v).strip() for v in item.values() if v is not None):
                continue
            crit = (
                item.get("criterion")
                or item.get("critere")
                or item.get("label")
                or item.get("name")
                or item.get("title")
                or ""
            )
            info = _pick_info_from_dict(item)
            row = CriterionRow(
                criterion=_translate_label(
                    _apply_display_phrases(_strip_decorative_markers(_strip_md(str(crit))))
                ),
                information_found=info,
            )
        else:
            row = criterion_to_row(str(item))

        crit = _strip_decorative_markers(row.criterion or "")
        info = _strip_decorative_markers(row.information_found or "")
        if _is_placeholder(crit) or _is_empty_missing_phrase(crit):
            continue
        if _is_incomplete_sentence(crit) and len(crit) < 40:
            continue
        if info and _is_incomplete_sentence(info):
            # Truncated LLM leftovers: omit the row rather than showing a cut sentence or "—"
            continue
        if info and _is_placeholder(info):
            info = ""
        if _is_section_header_without_info(crit, info):
            continue
        rows.append(CriterionRow(criterion=crit.strip().rstrip(":"), information_found=info.strip()))
    return rows


def sanitize_conclusion_text(text: str, *, has_real_missing: bool) -> str:
    """
    Keep a valid LLM conclusion when possible, but remove fake missing-criteria
    references such as '*' / 'None' / '—' after normalization.
    Drop clearly truncated hanging sentences instead of inventing content.
    """
    raw = fix_grammar_display(_apply_display_phrases(_strip_md(text or ""))).strip()
    if not raw or _is_placeholder(raw):
        return ""

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw) if s.strip()]
    kept: List[str] = []
    for sentence in sentences:
        s = _strip_decorative_markers(sentence)
        if not s or _is_placeholder(s):
            continue
        if _is_incomplete_sentence(s):
            continue
        lower = s.lower()
        # Drop sentences that only advertise fake missing markers
        if re.search(r"crit[eè]res?\s+manquants?[^.]*:\s*[-*—–none\s,]+\.?$", lower):
            if not has_real_missing:
                continue
        if not has_real_missing and re.search(
            r"crit[eè]res?\s+manquants?[^.]*:\s*\*\s*\.?$", lower
        ):
            continue
        if not has_real_missing and re.search(
            r"(crit[eè]res?\s+manquants?[^.]*|non d[eé]montr[eé]s)\s*:\s*(\*|none|—|–|-)\b",
            lower,
        ):
            continue
        kept.append(s if s[-1] in ".!?…" else s + ".")
    return fix_grammar_display(" ".join(kept).strip())


def _parse_evidence_status(bloc: str) -> str:
    """Extract evidence status; tolerate missing markdown bold."""
    patterns = (
        r"\*\*Statut\s*:\*\*\s*([^\n]+)",
        r"(?:\*\*)?Statut(?:\*\*)?\s*:\s*(?:\*\*)?([^\n*]+)",
        r"(?i)\bStatus\s*:\s*([^\n]+)",
    )
    for pat in patterns:
        m = re.search(pat, bloc, re.IGNORECASE)
        if m:
            value = _strip_md(m.group(1))
            if value and not _is_placeholder(value):
                return value
    return ""


def _resolve_evidence_status(
    statut: str,
    sat_rows: List[CriterionRow],
    nonsat_rows: List[CriterionRow],
) -> str:
    """
    Keep LLM status when present. If missing/undefined, infer only from
    structured criteria already produced by the analysis (never invent facts).
    """
    cleaned = _strip_md(statut or "").strip()
    undefined = {"", "non défini", "non defini", "indéterminé", "indetermine", "undefined", "n/a"}
    if cleaned and cleaned.lower() not in undefined:
        return cleaned

    has_sat = bool(sat_rows)
    has_miss = bool(nonsat_rows)
    if has_sat and not has_miss:
        return "Satisfait"
    if has_miss and not has_sat:
        return "Non Satisfait"
    if has_sat and has_miss:
        return "Partiellement Satisfait"
    return "Non défini"


def _extract_criteria_block(bloc: str, satisfied: bool) -> List[str]:
    if satisfied:
        patterns = (
            r"\*\*Critères Satisfaits\s*:\*\*(.*?)(?=\*\*Critères Non Satisfaits|$)",
            r"Critères Satisfaits\s*:(.*?)(?=Critères Non Satisfaits|$)",
            r"Satisfied Criteria\s*:(.*?)(?=Missing Criteria|Unsatisfied|$)",
        )
    else:
        patterns = (
            r"\*\*Critères Non Satisfaits\s*\(Manquants\)\s*:\*\*(.*?)(?=$)",
            r"Critères Non Satisfaits\s*\(Manquants\)\s*:(.*?)(?=$)",
            r"Critères Non Satisfaits\s*:(.*?)(?=$)",
            r"Missing Criteria\s*:(.*?)(?=$)",
        )
    for pat in patterns:
        m = re.search(pat, bloc, re.DOTALL | re.IGNORECASE)
        if m:
            return _bullet_lines(m.group(1))
    return []


def _extract_conclusion_text(report_text: str) -> str:
    """Field produced by LLM under section 3 / Conclusion — tolerate format variants."""
    if not report_text:
        return ""
    patterns = (
        r"###\s*3\s*[\.\)]\s*Conclusion[^\n]*(.*)",
        r"##\s*3\s*[\.\)]\s*Conclusion[^\n]*(.*)",
        r"###\s*Conclusion[^\n]*(.*)",
        r"(?im)^Conclusion\s*(?:finale)?\s*:\s*(.*)$",
        r"(?is)\*\*Conclusion\s*:\*\*\s*(.*)$",
    )
    for pat in patterns:
        m = re.search(pat, report_text, re.DOTALL | re.IGNORECASE)
        if not m:
            continue
        text = _strip_md(m.group(1))
        # Drop accidental trailing sections
        text = re.split(r"\n###\s*\d+", text, maxsplit=1)[0].strip()
        if text and not _is_placeholder(text):
            return text
    return ""


def build_deterministic_conclusion(data: "ReportData") -> str:
    """
    Fallback when LLM conclusion is empty. Uses only structured results already
    present (decision, %, evidence statuses, missing criteria). Does not invent
    document content.
    """
    resultat = (data.resultat or "Indéterminé").strip()
    pourcentage = (data.pourcentage or "N/A").strip()
    level = (data.level or "").strip()

    sat_count = 0
    partial_count = 0
    unsat_count = 0
    undefined_count = 0
    missing_labels: List[str] = []
    sat_criteria_count = 0

    for ev in data.evidences:
        st = (ev.statut or "").lower()
        if "partiel" in st:
            partial_count += 1
        elif "non satisfait" in st:
            unsat_count += 1
        elif "non défini" in st or "non defini" in st:
            undefined_count += 1
        elif "satisfait" in st:
            sat_count += 1
        sat_criteria_count += len(ev.criteres_satisfaits)
        for row in ev.criteres_non_satisfaits:
            if row.criterion and not _is_placeholder(row.criterion):
                missing_labels.append(row.criterion)

    parts = [
        f"Au regard de l'analyse réalisée, la décision globale est {resultat} "
        f"avec un taux de conformité de {pourcentage}."
    ]
    if level:
        parts.append(f"Le niveau de maturité évalué est : {level}.")

    evidence_bits = []
    if sat_count:
        evidence_bits.append(
            _fr_count(
                sat_count,
                "élément de preuve satisfait",
                "éléments de preuve satisfaits",
            )
        )
    if partial_count:
        evidence_bits.append(
            _fr_count(
                partial_count,
                "élément de preuve partiellement satisfait",
                "éléments de preuve partiellement satisfaits",
            )
        )
    if unsat_count:
        evidence_bits.append(
            _fr_count(
                unsat_count,
                "élément de preuve non satisfait",
                "éléments de preuve non satisfaits",
            )
        )
    if undefined_count:
        evidence_bits.append(
            _fr_count(
                undefined_count,
                "élément de preuve au statut non défini",
                "éléments de preuve au statut non défini",
            )
            + " (évaluation incomplète pour cet élément)"
        )
    if evidence_bits:
        parts.append("Bilan des éléments de preuve : " + ", ".join(evidence_bits) + ".")
    elif data.evidences:
        parts.append("Aucun élément de preuve satisfait n'a été identifié.")

    if sat_criteria_count:
        parts.append(
            "Critères satisfaits recensés : "
            + _fr_count(
                sat_criteria_count,
                "critère satisfait",
                "critères satisfaits",
            )
            + "."
        )

    if missing_labels:
        uniq = []
        for label in missing_labels:
            if label not in uniq:
                uniq.append(label)
        preview = ", ".join(uniq[:6])
        if len(uniq) > 6:
            rest = len(uniq) - 6
            more = f" (et {rest} autre{'s' if rest > 1 else ''})"
        else:
            more = ""
        parts.append(f"Critères manquants ou non démontrés identifiés : {preview}{more}.")
    else:
        parts.append("Aucun critère manquant ou non démontré n'a été listé dans le détail des preuves.")

    if undefined_count:
        parts.append(
            "Réserve : au moins un élément de preuve n'a pas reçu de statut explicite ; "
            "la conclusion s'appuie sur les résultats structurés disponibles."
        )
    elif resultat.upper().startswith("OUI"):
        parts.append(
            "Dans l'ensemble, les exigences examinées sont considérées comme démontrées pour le niveau ciblé."
        )
    elif resultat.upper().startswith("NON"):
        parts.append(
            "Des actions correctives restent nécessaires avant de considérer le niveau ciblé comme atteint."
        )

    return " ".join(parts)


def _has_real_missing_criteria(data: "ReportData") -> bool:
    for ev in data.evidences:
        for row in normalize_criteria_rows(ev.criteres_non_satisfaits):
            if row.criterion and not _is_placeholder(row.criterion):
                return True
    return False


def ensure_conclusion(data: "ReportData") -> str:
    has_missing = _has_real_missing_criteria(data)
    text = sanitize_conclusion_text(data.conclusion or "", has_real_missing=has_missing)
    if text and not _is_placeholder(text):
        # If OUI 100% and no real missing, strip residual fake-missing mentions
        if not has_missing and re.search(r"\b(\*|none|—)\b", text, re.IGNORECASE):
            text = sanitize_conclusion_text(
                re.sub(
                    r"(?i)crit[eè]res?\s+manquants?[^.]*:\s*[-*—–none\s,]+\.?",
                    "Aucun critère manquant ou non démontré.",
                    text,
                ),
                has_real_missing=False,
            )
        if text and not _is_placeholder(text):
            return text
    return build_deterministic_conclusion(data)


def parse_report_data(report_text: str, domain: str, question: str, level: str) -> ReportData:
    data = ReportData(
        domain=domain or "",
        question=question or "",
        level=level or "",
        raw_fallback=report_text or "",
    )
    if not report_text:
        data.conclusion = build_deterministic_conclusion(data)
        return data

    s1 = re.search(
        r"###\s*1\s*[\.\)]\s*Évaluation Globale(.*?)(?=###\s*2\s*[\.\)]|$)",
        report_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not s1:
        s1 = re.search(
            r"###\s*1\.\s*Évaluation Globale(.*?)(?=###\s*2\.|$)",
            report_text,
            re.DOTALL | re.IGNORECASE,
        )
    if s1:
        s1_text = s1.group(1)
        res = re.search(r"(?:\*\*)?Résultat(?:\*\*)?\s*:\s*(?:\*\*)?(OUI|NON|[^\n*]+)", s1_text, re.IGNORECASE)
        pct = re.search(r"(?:\*\*)?Pourcentage(?:\*\*)?\s*:\s*(?:\*\*)?([^\n*]+)", s1_text, re.IGNORECASE)
        just = re.search(r"(?:\*\*)?Justification(?:\*\*)?\s*:\s*(?:\*\*)?(.*)", s1_text, re.IGNORECASE | re.DOTALL)
        if res:
            data.resultat = _strip_md(res.group(1))
        if pct:
            data.pourcentage = _strip_md(pct.group(1))
        if just:
            just_text = re.split(r"\n###\s*", just.group(1), maxsplit=1)[0]
            data.justification = _strip_md(just_text)

    s2 = re.search(
        r"###\s*2\s*[\.\)]\s*Détail par Preuve(.*?)(?=###\s*3\s*[\.\)]|$)",
        report_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not s2:
        s2 = re.search(
            r"###\s*2\.\s*Détail par Preuve(.*?)(?=###\s*3\.|$)",
            report_text,
            re.DOTALL | re.IGNORECASE,
        )
    if s2:
        for bloc in re.split(r"####\s*Preuve\s*:", s2.group(1).strip()):
            if not bloc.strip():
                continue
            lines = bloc.strip().split("\n")
            titre = _strip_md(lines[0].strip())
            sat_raw = _extract_criteria_block(bloc, satisfied=True)
            nonsat_raw = _extract_criteria_block(bloc, satisfied=False)
            sat_rows = normalize_criteria_rows(sat_raw)
            nonsat_rows = normalize_criteria_rows(nonsat_raw)
            statut = _resolve_evidence_status(_parse_evidence_status(bloc), sat_rows, nonsat_rows)
            data.evidences.append(
                EvidenceBlock(
                    titre=titre,
                    statut=statut,
                    criteres_satisfaits=sat_rows,
                    criteres_non_satisfaits=nonsat_rows,
                )
            )

    # Final pass: re-normalize every evidence block so fake markers never reach PDF/conclusion
    for ev in data.evidences:
        ev.criteres_satisfaits = normalize_criteria_rows(ev.criteres_satisfaits)
        ev.criteres_non_satisfaits = normalize_criteria_rows(ev.criteres_non_satisfaits)
        ev.statut = _resolve_evidence_status(ev.statut, ev.criteres_satisfaits, ev.criteres_non_satisfaits)

    data.conclusion = _extract_conclusion_text(report_text)
    data.conclusion = ensure_conclusion(data)
    return data


def split_conclusion_parts(conclusion: str) -> Tuple[str, str, str]:
    text = fix_grammar_display(_apply_display_phrases(conclusion or "")).strip()
    if not text:
        return ("", "", "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) == 1:
        return (sentences[0], "", sentences[0])
    if len(sentences) == 2:
        return (sentences[0], sentences[1], sentences[1])
    return (sentences[0], " ".join(sentences[1:-1]).strip(), sentences[-1])


def _status_tone(statut: str) -> str:
    s = (statut or "").strip().lower()
    if "partiel" in s or "partial" in s:
        return "orange"
    if "non satisfait" in s or "refused" in s or "refus" in s:
        return "red"
    if s in ("non", "rejected", "reject"):
        return "red"
    if "satisfait" in s or "accepted" in s or "accepté" in s or "accepte" in s:
        return "green"
    if s == "oui":
        return "green"
    return "muted"


def _result_tone(resultat: str) -> str:
    r = (resultat or "").strip().upper()
    if r.startswith("OUI"):
        return "green"
    if r.startswith("NON"):
        return "red"
    return "orange"


def _tone_colors(tone: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    if tone == "green":
        return PdfStyles.COLOR_GREEN, PdfStyles.COLOR_GREEN_BG
    if tone == "red":
        return PdfStyles.COLOR_RED, PdfStyles.COLOR_RED_BG
    if tone == "orange":
        return PdfStyles.COLOR_ORANGE, PdfStyles.COLOR_ORANGE_BG
    return PdfStyles.COLOR_MUTED, PdfStyles.COLOR_CARD_BG


class AuditPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=False, margin=PdfStyles.MARGIN)
        self.set_margins(PdfStyles.MARGIN, PdfStyles.MARGIN, PdfStyles.MARGIN)
        self._register_fonts()
        self.alias_nb_pages()
        self.continuation_note: Optional[str] = None

    def _register_fonts(self) -> None:
        regular = bold = italic = None
        for folder in PdfStyles.FONT_DIR_CANDIDATES:
            for reg, bld, ita in (
                (
                    os.path.join(folder, "DejaVuSans.ttf"),
                    os.path.join(folder, "DejaVuSans-Bold.ttf"),
                    os.path.join(folder, "DejaVuSans-Oblique.ttf"),
                ),
                (
                    os.path.join(folder, "arial.ttf"),
                    os.path.join(folder, "arialbd.ttf"),
                    os.path.join(folder, "ariali.ttf"),
                ),
            ):
                if os.path.exists(reg) and os.path.exists(bld):
                    regular, bold = reg, bld
                    italic = ita if os.path.exists(ita) else reg
                    break
            if regular:
                break
        if not regular:
            self.font_family_name = "Helvetica"
            return
        self.add_font("ReportFont", "", regular)
        self.add_font("ReportFont", "B", bold)
        self.add_font("ReportFont", "I", italic)
        self.font_family_name = "ReportFont"

    def header(self) -> None:
        if self.page_no() <= 1 and not self.continuation_note:
            return
        self.set_font(self.font_family_name, "B", 9)
        self.set_text_color(*PdfStyles.COLOR_PRIMARY)
        self.set_x(PdfStyles.MARGIN)
        self.cell(0, 5, "Rapport d'Audit NDI — Évaluation des éléments de preuve", ln=True)
        if self.continuation_note:
            self.set_font(self.font_family_name, "I", 9)
            self.set_text_color(*PdfStyles.COLOR_MUTED)
            self.set_x(PdfStyles.MARGIN)
            self.cell(0, 5, self.continuation_note, ln=True)
            self.continuation_note = None
        self.set_draw_color(*PdfStyles.COLOR_LINE)
        self.set_line_width(0.3)
        y = self.get_y()
        self.line(PdfStyles.MARGIN, y, PdfStyles.PAGE_W - PdfStyles.MARGIN, y)
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(self.font_family_name, "I", 8)
        self.set_text_color(*PdfStyles.COLOR_MUTED)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")

    def remaining_height(self) -> float:
        return PdfStyles.PAGE_H - PdfStyles.MARGIN - 12 - self.get_y()

    def ensure_space(self, needed: float, continuation: Optional[str] = None) -> None:
        if self.remaining_height() < needed:
            if continuation:
                self.continuation_note = continuation
            self.add_page()


class PdfLayout:
    def __init__(self, pdf: AuditPDF):
        self.pdf = pdf
        self.s = PdfStyles

    def _set_font(self, style: str = "", size: float = 10) -> None:
        self.pdf.set_font(self.pdf.font_family_name, style, size)

    def _tw(self, text: str) -> float:
        return self.pdf.get_string_width(text or "")

    def section_title(self, title: str) -> None:
        pdf = self.pdf
        pdf.ensure_space(16)
        self._set_font("B", 12)
        pdf.set_text_color(*self.s.COLOR_PRIMARY)
        pdf.set_x(self.s.MARGIN)
        pdf.multi_cell(self.s.CONTENT_W, 7, title)
        pdf.set_draw_color(*self.s.COLOR_PRIMARY)
        pdf.set_line_width(0.45)
        y = pdf.get_y()
        pdf.line(self.s.MARGIN, y, self.s.PAGE_W - self.s.MARGIN, y)
        pdf.ln(3)

    def kv_line(self, label: str, value: str) -> None:
        pdf = self.pdf
        value = value or "—"
        pdf.ensure_space(10)
        pdf.set_x(self.s.MARGIN)
        self._set_font("B", 10)
        pdf.set_text_color(*self.s.COLOR_PRIMARY)
        pdf.cell(58, 5.5, f"{label} :", ln=False)
        self._set_font("", 10)
        pdf.set_text_color(*self.s.COLOR_TEXT)
        pdf.set_xy(self.s.MARGIN + 58, pdf.get_y())
        pdf.multi_cell(self.s.CONTENT_W - 58, 5.5, value)

    def draw_banner(self) -> None:
        pdf = self.pdf
        pdf.set_fill_color(*self.s.COLOR_HEADER_BG)
        pdf.rect(0, 0, self.s.PAGE_W, 36, style="F")
        pdf.set_xy(self.s.MARGIN, 10)
        self._set_font("B", 16)
        pdf.set_text_color(*self.s.COLOR_WHITE)
        pdf.cell(0, 8, "Rapport d'Audit NDI", ln=True)
        pdf.set_x(self.s.MARGIN)
        self._set_font("", 10)
        pdf.cell(0, 6, "Évaluation des éléments de preuve", ln=True)
        pdf.set_y(42)

    def draw_section_1(self, data: ReportData) -> None:
        self.section_title("1. Informations de l'audit")
        if data.client_full_name:
            self.kv_line("Client", data.client_full_name)
        if data.client_email:
            self.kv_line("E-mail client", data.client_email)
        if data.project_name:
            self.kv_line("Projet", data.project_name)
        framework = (data.framework or "").strip() or "NDI"
        self.kv_line("Framework", framework)
        domain_display = _display_domain(data.domain)
        if data.domain_code:
            domain_display = f"{domain_display} [{data.domain_code}]" if domain_display else data.domain_code
        self.kv_line("Domaine", domain_display)
        self.kv_line("Niveau de maturité évalué", _display_level(data.level))
        if data.selected_score:
            self.kv_line("Score sélectionné", data.selected_score)
        question_display = data.question or "—"
        if data.question_code:
            question_display = f"[{data.question_code}] {question_display}"
        self.kv_line("Question évaluée", question_display)
        if data.evidence_file_name:
            self.kv_line("Fichier analysé", data.evidence_file_name)
        if data.assessment_version:
            self.kv_line("Version assessment", data.assessment_version)
        if data.generation_date:
            self.kv_line("Date de génération", data.generation_date)
        self.pdf.ln(2)

    def draw_section_2(self, data: ReportData, resume_text: str) -> None:
        pdf = self.pdf
        self.section_title("2. Synthèse de l'évaluation")

        resultat = data.resultat or "Indéterminé"
        pourcentage = data.pourcentage or "N/A"
        tone = _result_tone(resultat)
        fg, bg = _tone_colors(tone)
        resume = fix_grammar_display(_apply_display_phrases(resume_text or ""))

        self._set_font("", 9)
        resume_lines = max(1, int(self._tw(resume) / (self.s.CONTENT_W - 10)) + 1) if resume else 0
        card_h = 24 + (8 + resume_lines * 5.2 if resume else 0)

        pdf.ensure_space(min(card_h + 2, 55))
        x, y = self.s.MARGIN, pdf.get_y()

        use_box = card_h <= pdf.remaining_height() - 2
        if use_box:
            pdf.set_fill_color(*bg)
            pdf.set_draw_color(*fg)
            pdf.set_line_width(0.55)
            pdf.rect(x, y, self.s.CONTENT_W, card_h, style="FD")

        pdf.set_xy(x + 4, y + 3)
        self._set_font("B", 10)
        pdf.set_text_color(*fg)
        pdf.cell(self.s.CONTENT_W - 8, 6, f"Résultat global : {resultat}", ln=True)
        pdf.set_x(x + 4)
        pdf.cell(self.s.CONTENT_W - 8, 6, f"Taux de conformité : {pourcentage}", ln=True)

        if resume:
            pdf.set_x(x + 4)
            self._set_font("B", 9)
            pdf.set_text_color(*self.s.COLOR_MUTED)
            pdf.cell(self.s.CONTENT_W - 8, 5, "Résumé de l'analyse", ln=True)
            pdf.set_x(x + 4)
            self._set_font("", 9)
            pdf.set_text_color(*self.s.COLOR_TEXT)
            pdf.multi_cell(self.s.CONTENT_W - 8, 5.2, resume)

        if use_box:
            pdf.set_y(max(pdf.get_y(), y + card_h) + 4)
        else:
            pdf.ln(3)

    def _badge_size(self, label: str) -> Tuple[float, float]:
        self._set_font("B", 8)
        w = self._tw(label) + 5
        return min(max(w, 18), 55), 6.2

    def _draw_badge(self, label: str, tone: str, x: float, y: float, w: float) -> None:
        pdf = self.pdf
        fg, bg = _tone_colors(tone)
        h = 6.2
        pdf.set_fill_color(*bg)
        pdf.set_draw_color(*fg)
        pdf.set_line_width(0.3)
        pdf.rect(x, y, w, h, style="FD")
        self._set_font("B", 8)
        pdf.set_text_color(*fg)
        pdf.set_xy(x, y + 0.6)
        pdf.cell(w, 5, label, align="C")

    def _draw_table_header(self) -> None:
        pdf = self.pdf
        pdf.ensure_space(10)
        x, y = self.s.MARGIN, pdf.get_y()
        h = 7
        pdf.set_fill_color(*self.s.COLOR_TABLE_HEADER)
        pdf.set_draw_color(*self.s.COLOR_LINE)
        pdf.set_line_width(0.3)
        pdf.rect(x, y, self.s.COL_LEFT, h, style="FD")
        pdf.rect(x + self.s.COL_LEFT, y, self.s.COL_RIGHT, h, style="FD")
        self._set_font("B", 8.5)
        pdf.set_text_color(*self.s.COLOR_PRIMARY)
        pdf.set_xy(x + 2, y + 1.2)
        pdf.cell(self.s.COL_LEFT - 4, 5, "Élément vérifié")
        pdf.set_xy(x + self.s.COL_LEFT + 2, y + 1.2)
        pdf.cell(self.s.COL_RIGHT - 4, 5, "Information trouvée")
        pdf.set_y(y + h)

    def _lines_for(self, txt: str, width: float) -> int:
        if not txt:
            return 1
        self._set_font("", 8.5)
        try:
            # fpdf2 dry-run gives accurate wrapped line count (avoids truncation / orphan pages)
            lines = self.pdf.multi_cell(
                width,
                self.s.ROW_H,
                txt,
                dry_run=True,
                output="LINES",
            )
            return max(len(lines), 1)
        except TypeError:
            pass
        words = (txt or "").split(" ")
        lines, cur = 1, ""
        for w in words:
            trial = w if not cur else f"{cur} {w}"
            if self._tw(trial) <= width:
                cur = trial
            else:
                if cur:
                    lines += 1
                if self._tw(w) > width:
                    avg = max(self._tw("a"), 0.1)
                    chunk = max(int(width / avg), 1)
                    parts = max(1, (len(w) + chunk - 1) // chunk)
                    lines += parts - 1
                    cur = w[-chunk:]
                else:
                    cur = w
        return max(lines, 1)

    def _draw_table_row(self, left: str, right: str, continuation: str) -> None:
        pdf = self.pdf
        left_d = _translate_label(_apply_display_phrases(left))
        right_d = right
        lh = self._lines_for(left_d, self.s.COL_LEFT - 4)
        rh = self._lines_for(right_d, self.s.COL_RIGHT - 4)
        h = max(lh, rh) * self.s.ROW_H + 2.4
        h = max(h, 7.5)

        if pdf.remaining_height() < h + 1:
            pdf.ensure_space(h + 2, continuation=continuation)
            self._draw_table_header()

        x, y = self.s.MARGIN, pdf.get_y()
        pdf.set_draw_color(*self.s.COLOR_LINE)
        pdf.set_fill_color(*self.s.COLOR_WHITE)
        pdf.rect(x, y, self.s.COL_LEFT, h, style="FD")
        pdf.rect(x + self.s.COL_LEFT, y, self.s.COL_RIGHT, h, style="FD")
        self._set_font("", 8.5)
        pdf.set_text_color(*self.s.COLOR_TEXT)
        pdf.set_xy(x + 2, y + 1)
        pdf.multi_cell(self.s.COL_LEFT - 4, self.s.ROW_H, left_d)
        pdf.set_xy(x + self.s.COL_LEFT + 2, y + 1)
        pdf.multi_cell(self.s.COL_RIGHT - 4, self.s.ROW_H, right_d)
        # Never leave the cursor above the drawn row bottom (prevents overlap / apparent truncation)
        pdf.set_y(max(y + h, pdf.get_y()))

    def draw_criteria_table(
        self,
        title: str,
        items,
        continuation: str,
        empty_message: str = "Aucun critère listé.",
    ) -> None:
        pdf = self.pdf
        pdf.ensure_space(18, continuation=continuation)
        self._set_font("B", 9)
        pdf.set_text_color(*self.s.COLOR_PRIMARY)
        pdf.set_x(self.s.MARGIN)
        pdf.cell(0, 6, title, ln=True)

        rows = normalize_criteria_rows(items)
        if not rows:
            self._set_font("I", 9)
            pdf.set_text_color(*self.s.COLOR_MUTED)
            pdf.set_x(self.s.MARGIN)
            pdf.multi_cell(self.s.CONTENT_W, 5.2, empty_message)
            pdf.set_text_color(*self.s.COLOR_TEXT)
            return

        self._draw_table_header()
        for row in rows:
            left = row.criterion
            right = row.information_found if row.information_found else "—"
            self._draw_table_row(left, right, continuation)

    def draw_evidence(self, index: int, ev: EvidenceBlock) -> None:
        pdf = self.pdf
        cont = f"Élément de preuve {index} — suite"
        pdf.ensure_space(28)

        x = self.s.MARGIN
        badge_label = ev.statut or "Non défini"
        tone = _status_tone(badge_label)
        badge_w, badge_h = self._badge_size(badge_label)

        title = f"Élément de preuve {index} : {ev.titre}" if ev.titre else f"Élément de preuve {index}"
        title = _apply_display_phrases(title)
        title_w = self.s.CONTENT_W - badge_w - 8

        self._set_font("B", 10)
        t_lines = self._lines_for(title, title_w)
        header_h = max(t_lines * 5.5 + 4, badge_h + 6)

        pdf.ensure_space(header_h + 4)
        y0 = pdf.get_y()
        pdf.set_fill_color(*self.s.COLOR_CARD_BG)
        pdf.set_draw_color(*self.s.COLOR_LINE)
        pdf.set_line_width(0.35)
        pdf.rect(x, y0, self.s.CONTENT_W, header_h, style="FD")

        badge_x = x + self.s.CONTENT_W - 4 - badge_w
        badge_y = y0 + (header_h - badge_h) / 2
        self._draw_badge(badge_label, tone, badge_x, badge_y, badge_w)

        pdf.set_xy(x + 3, y0 + 2)
        self._set_font("B", 10)
        pdf.set_text_color(*self.s.COLOR_PRIMARY)
        pdf.multi_cell(title_w, 5.5, title)

        pdf.set_y(y0 + header_h + 2)
        self._set_font("", 9)
        pdf.set_text_color(*self.s.COLOR_TEXT)
        pdf.set_x(self.s.MARGIN)
        pdf.cell(0, 5, f"Statut : {badge_label}", ln=True)
        pdf.ln(1)

        self.draw_criteria_table(
            "Critères vérifiés et satisfaits",
            ev.criteres_satisfaits,
            cont,
            empty_message="Aucun critère satisfait listé.",
        )
        pdf.ln(1)
        self.draw_criteria_table(
            "Critères manquants ou non démontrés",
            ev.criteres_non_satisfaits,
            cont,
            empty_message="Aucun critère manquant ou non démontré.",
        )

        pdf.ln(2)
        pdf.set_draw_color(*self.s.COLOR_LINE)
        pdf.set_line_width(0.3)
        y = pdf.get_y()
        pdf.line(x, y, x + self.s.CONTENT_W, y)
        pdf.ln(3)

    def _estimate_text_height(self, text: str, width: float, line_h: float = 5.2) -> float:
        body = fix_grammar_display(_apply_display_phrases(text or ""))
        if not body:
            return 0
        lines = self._lines_for(body, width)
        return lines * line_h

    def _conclusion_block(self, label: str, body: str) -> None:
        if not body:
            return
        pdf = self.pdf
        text = fix_grammar_display(_apply_display_phrases(body))
        if _is_incomplete_sentence(text) and len(text) < 80:
            # Drop short truncated leftovers (e.g. hanging "Accountability")
            return

        label_h = 5.5
        box_pad = 6
        content_h = self._estimate_text_height(text, self.s.CONTENT_W - 6, 5.2)
        box_h = content_h + box_pad
        needed = label_h + 2 + min(box_h, 28)

        # Keep label + start of body together — avoids orphan "Conclusion finale" on empty page
        pdf.ensure_space(needed)

        self._set_font("B", 9)
        pdf.set_text_color(*self.s.COLOR_PRIMARY)
        pdf.set_x(self.s.MARGIN)
        pdf.cell(0, label_h, label, ln=True)

        self._set_font("", 9.5)
        x, y = self.s.MARGIN, pdf.get_y()

        if box_h <= pdf.remaining_height() - 2:
            pdf.set_fill_color(*self.s.COLOR_CARD_BG)
            pdf.set_draw_color(*self.s.COLOR_PRIMARY)
            pdf.set_line_width(0.45)
            pdf.rect(x, y, self.s.CONTENT_W, box_h, style="FD")
            pdf.set_xy(x + 3, y + 2)
            pdf.set_text_color(*self.s.COLOR_TEXT)
            pdf.multi_cell(self.s.CONTENT_W - 6, 5.2, text)
            end_y = max(y + box_h, pdf.get_y() + 2)
            pdf.set_y(end_y + 2)
        else:
            start = pdf.get_y()
            pdf.set_xy(x + 3, start)
            pdf.set_text_color(*self.s.COLOR_TEXT)
            pdf.multi_cell(self.s.CONTENT_W - 6, 5.2, text)
            end = pdf.get_y() + 1
            pdf.set_draw_color(*self.s.COLOR_PRIMARY)
            pdf.set_line_width(1.0)
            # Only draw vertical rule on the current page segment
            pdf.line(x, start - 1, x, min(end, start + pdf.remaining_height()))
            pdf.set_y(end + 2)

    def draw_section_4(self, constat: str, motifs: str, finale: str) -> None:
        pdf = self.pdf

        parts = []
        for label, body in (
            ("Constat général", constat),
            ("Motifs de la décision", motifs),
            ("Conclusion finale", finale),
        ):
            if not body or _is_placeholder(body):
                continue
            cleaned = sanitize_conclusion_text(body, has_real_missing=True) or body
            if _is_incomplete_sentence(cleaned) and len(cleaned) < 80:
                continue
            if parts and _normalize_cmp(cleaned) == _normalize_cmp(parts[-1][1]):
                continue
            parts.append((label, cleaned))
        if not parts and finale and not _is_placeholder(finale):
            parts = [("Conclusion finale", finale)]
        if not parts:
            return

        # Prefer a single cohesive conclusion block when the split would orphan a short finale
        total_body = " ".join(p[1] for p in parts).strip()
        total_h = 14 + self._estimate_text_height(total_body, self.s.CONTENT_W - 6, 5.2) + 8
        # If everything fits on the current page, reserve space once (no mid-section page break)
        if total_h <= pdf.remaining_height() - 2:
            pdf.ensure_space(min(total_h, pdf.remaining_height()))
            self.section_title("4. Conclusion de l'audit")
            for label, body in parts:
                self._conclusion_block(label, body)
            return

        # Otherwise keep title with first block, then continue naturally without forcing a break
        first_body = fix_grammar_display(_apply_display_phrases(parts[0][1]))
        first_h = 14 + 5.5 + min(self._estimate_text_height(first_body, self.s.CONTENT_W - 6, 5.2) + 6, 40)
        pdf.ensure_space(min(first_h, 50))
        self.section_title("4. Conclusion de l'audit")
        for label, body in parts:
            self._conclusion_block(label, body)

    def draw_fallback(self, raw: str) -> None:
        self.section_title("1. Rapport")
        self._set_font("", 10)
        self.pdf.set_text_color(*self.s.COLOR_TEXT)
        cleaned = fix_grammar_display(_apply_display_phrases(_strip_md(raw)))
        for para in cleaned.split("\n"):
            para = para.strip()
            if not para:
                self.pdf.ln(3)
                continue
            self.pdf.ensure_space(10)
            self.pdf.set_x(self.s.MARGIN)
            self.pdf.multi_cell(self.s.CONTENT_W, 5.2, para)


def build_pdf(data: ReportData) -> bytes:
    pdf = AuditPDF()
    layout = PdfLayout(pdf)
    pdf.add_page()
    layout.draw_banner()

    has_structure = bool(data.resultat or data.evidences or data.conclusion)
    if not has_structure:
        layout.draw_fallback(data.raw_fallback)
    else:
        layout.draw_section_1(data)

        resume = data.justification or ""
        conclusion = ensure_conclusion(data)
        data.conclusion = conclusion
        layout.draw_section_2(data, resume)

        layout.section_title("3. Analyse détaillée des éléments de preuve")
        if data.evidences:
            for i, ev in enumerate(data.evidences, start=1):
                layout.draw_evidence(i, ev)
        else:
            layout._set_font("", 10)
            pdf.set_text_color(*PdfStyles.COLOR_TEXT)
            pdf.set_x(PdfStyles.MARGIN)
            pdf.multi_cell(
                PdfStyles.CONTENT_W,
                5.5,
                "Aucun élément de preuve détaillé n'a été fourni dans le rapport.",
            )

        constat, motifs, finale = split_conclusion_parts(conclusion)
        if resume and conclusion and _normalize_cmp(resume) == _normalize_cmp(conclusion):
            # Évite la duplication : une seule conclusion structurée
            layout.draw_section_4("", "", conclusion)
        else:
            # Prefer full conclusion text if split produced only empty fragments
            if not any([constat, motifs, finale]):
                layout.draw_section_4("", "", conclusion)
            else:
                layout.draw_section_4(constat, motifs, finale if finale else conclusion)

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, (bytes, bytearray)) else bytes(out)


def generate_pdf_report(
    report_text: str,
    domain: str,
    question: str,
    level: str,
    header_meta: Optional[dict] = None,
) -> bytes:
    data = parse_report_data(report_text, domain, question, level)
    if header_meta:
        data.client_full_name = str(header_meta.get("client_full_name") or "").strip()
        data.client_email = str(header_meta.get("client_email") or "").strip()
        data.project_name = str(header_meta.get("project_name") or "").strip()
        data.framework = str(header_meta.get("framework") or "").strip()
        data.domain_code = str(header_meta.get("domain_code") or "").strip()
        data.question_code = str(header_meta.get("question_code") or "").strip()
        data.selected_score = str(header_meta.get("selected_score") or "").strip()
        data.evidence_file_name = str(header_meta.get("evidence_file_name") or "").strip()
        data.generation_date = str(header_meta.get("generation_date") or "").strip()
        data.assessment_version = str(header_meta.get("assessment_version") or "").strip()
        # Prefer explicit domain/question/level from header when provided.
        if header_meta.get("domain_name"):
            data.domain = str(header_meta.get("domain_name")).strip() or data.domain
        if header_meta.get("question_text"):
            data.question = str(header_meta.get("question_text")).strip() or data.question
        if header_meta.get("maturity_level"):
            data.level = str(header_meta.get("maturity_level")).strip() or data.level
    return build_pdf(data)
