"""Generate a Best Path recommendation report as PDF bytes (ReportLab)."""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)

from app.services.best_path_response_formatter import sort_best_path_for_display

TITLE_BLUE = colors.HexColor("#1F4E79")
HEADER_BG = colors.HexColor("#2E75B6")
HEADER_TEXT = colors.white
BODY_TEXT = colors.HexColor("#1A1A1A")
MARGIN = 18 * mm
PAGE_WIDTH, PAGE_HEIGHT = A4
USABLE_WIDTH = PAGE_WIDTH - 2 * MARGIN

FONT_REGULAR = "BestPathUnicode"
FONT_BOLD = "BestPathUnicode-Bold"


class BestPathPDFError(Exception):
    """Base error for PDF generation."""


class UnicodeFontNotFoundError(BestPathPDFError):
    """Raised when no suitable Unicode TTF font is available locally."""


def _register_unicode_fonts() -> None:
    if FONT_REGULAR in pdfmetrics.getRegisteredFontNames():
        return

    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = [
        (windir / "Fonts" / "segoeui.ttf", windir / "Fonts" / "segoeuib.ttf"),
        (windir / "Fonts" / "arial.ttf", windir / "Fonts" / "arialbd.ttf"),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
        (Path("/Library/Fonts/Arial Unicode.ttf"), Path("/Library/Fonts/Arial Unicode.ttf")),
    ]

    for regular_path, bold_path in candidates:
        if regular_path.is_file():
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_path)))
            bold_file = bold_path if bold_path.is_file() else regular_path
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_file)))
            return

    raise UnicodeFontNotFoundError(
        "Aucune police Unicode locale trouvée. Installez Segoe UI ou Arial, "
        "ou placez DejaVuSans.ttf sur le système."
    )


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_str(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _format_bool_oui_non(value: Any) -> str:
    return "Oui" if bool(value) else "Non"


def _align_detailed_actions(
    best_path_table: list[dict[str, Any]],
    detailed_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions_by_domain = {
        str(action.get("domainId")): action for action in detailed_actions
    }
    aligned: list[dict[str, Any]] = []
    for row in best_path_table:
        domain_id = str(row.get("domainId", ""))
        action = actions_by_domain.get(domain_id)
        if action is None:
            continue
        aligned_action = dict(action)
        aligned_action["priority"] = row.get("priority")
        aligned.append(aligned_action)
    return aligned


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "BP_Title",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=18,
            leading=22,
            textColor=TITLE_BLUE,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "BP_Section",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=13,
            leading=16,
            textColor=TITLE_BLUE,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "BP_Body",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=10,
            leading=14,
            textColor=BODY_TEXT,
            alignment=TA_LEFT,
        ),
        "body_bold": ParagraphStyle(
            "BP_BodyBold",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            leading=14,
            textColor=BODY_TEXT,
        ),
        "table_header": ParagraphStyle(
            "BP_TableHeader",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=HEADER_TEXT,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "BP_TableCell",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=10,
            textColor=BODY_TEXT,
            alignment=TA_LEFT,
        ),
        "table_cell_center": ParagraphStyle(
            "BP_TableCellCenter",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=10,
            textColor=BODY_TEXT,
            alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "BP_Footer",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=10,
            textColor=colors.grey,
        ),
    }


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = _safe_str(text, "")
    return Paragraph(safe.replace("\n", "<br/>"), style)


def _key_value_table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> LongTable:
    table_data = [
        [
            Paragraph(f"<b>{label}</b>", styles["body"]),
            Paragraph(value, styles["body"]),
        ]
        for label, value in rows
    ]
    table = LongTable(table_data, colWidths=[USABLE_WIDTH * 0.38, USABLE_WIDTH * 0.62])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F0FA")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B4C6E7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E2F3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _data_table(
    headers: list[str],
    rows: list[list[Any]],
    styles: dict[str, ParagraphStyle],
    col_widths: list[float] | None = None,
) -> LongTable:
    header_row = [_paragraph(header, styles["table_header"]) for header in headers]
    body_rows: list[list[Paragraph]] = []
    for row in rows:
        formatted_row: list[Paragraph] = []
        for index, cell in enumerate(row):
            cell_style = styles["table_cell_center"] if index == 0 else styles["table_cell"]
            formatted_row.append(_paragraph(cell, cell_style))
        body_rows.append(formatted_row)

    widths = col_widths or [USABLE_WIDTH / len(headers)] * len(headers)
    table = LongTable([header_row, *body_rows], colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B4C6E7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E2F3")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F9FD")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _draw_page_decorations(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setFont(FONT_REGULAR, 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 12 * mm, "Best Path Recommendation Report")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 10 * mm, f"Page {canvas.getPageNumber()}")
    canvas.setStrokeColor(colors.HexColor("#B4C6E7"))
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_HEIGHT - 14 * mm, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 14 * mm)
    canvas.restoreState()


def generate_best_path_pdf(report: dict) -> bytes:
    """Build a complete Best Path PDF report in memory and return raw bytes."""
    if not isinstance(report, dict):
        raise BestPathPDFError("Le rapport fourni n'est pas un dictionnaire valide.")

    _register_unicode_fonts()
    styles = _build_styles()

    score_summary = _safe_dict(report.get("scoreSummary"))
    optimization = _safe_dict(report.get("optimizationSummary"))
    status = _safe_dict(report.get("status"))
    validation = _safe_dict(report.get("mathematicalValidation"))
    # Keep report["warnings"] available for API/validation; do not render it.

    raw_table = _safe_list(report.get("bestPathTable"))
    best_path_table = sort_best_path_for_display(
        [dict(row) for row in raw_table if isinstance(row, dict)]
    )
    detailed_actions = _align_detailed_actions(
        best_path_table,
        [dict(item) for item in _safe_list(report.get("detailedActions")) if isinstance(item, dict)],
    )

    generation_date = _safe_str(
        report.get("generationDate") or report.get("_generationDate"),
        datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    framework_name = _safe_str(report.get("framework") or report.get("_frameworkName"), "NDI")
    status_message = _safe_str(status.get("message"), "Statut inconnu")
    target_reached = status.get("targetReached", validation.get("targetReached"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=20 * mm,
        bottomMargin=16 * mm,
        title="Best Path Recommendation Report",
    )

    story: list[Any] = []
    story.append(Paragraph("Best Path Recommendation Report", styles["title"]))
    story.append(Spacer(1, 6))

    project_name = _safe_str(report.get("projectName") or report.get("_projectName"), "")
    client_name = _safe_str(report.get("clientName") or report.get("_clientName"), "")
    version_number = report.get("versionNumber") or report.get("_versionNumber")
    submitted_at = _safe_str(report.get("submittedAt") or report.get("_submittedAt"), "")

    general_rows: list[tuple[str, str]] = [
        ("Framework", framework_name),
        ("Date de génération", generation_date),
    ]
    if project_name and project_name != "—":
        general_rows.append(("Projet", project_name))
    if client_name and client_name != "—":
        general_rows.append(("Client", client_name))
    if version_number is not None and str(version_number).strip():
        general_rows.append(("Numéro de version", _safe_str(version_number)))
    if submitted_at and submitted_at != "—":
        general_rows.append(("Date de soumission", submitted_at))
    general_rows.extend(
        [
            ("Statut de la génération", status_message),
            ("Succès", _format_bool_oui_non(report.get("success"))),
        ]
    )

    story.append(Paragraph("A. Informations générales", styles["section"]))
    story.append(_key_value_table(general_rows, styles))

    story.append(Paragraph("B. Résumé des scores", styles["section"]))
    story.append(
        _key_value_table(
            [
                ("Score global initial", _safe_str(score_summary.get("scoreGlobalInitial"))),
                ("Score global cible", _safe_str(score_summary.get("scoreGlobalTarget"))),
                ("Écart à combler", _safe_str(score_summary.get("targetGap"))),
                ("Gain total", _safe_str(score_summary.get("gainTotal"))),
                ("Score global final estimé", _safe_str(score_summary.get("scoreGlobalFinalEstimated"))),
                ("Effort total", _safe_str(score_summary.get("effortTotal"))),
                ("Target Reached", _format_bool_oui_non(target_reached)),
            ],
            styles,
        )
    )

    story.append(Paragraph("C. Résumé de l'optimisation", styles["section"]))
    story.append(
        _key_value_table(
            [
                ("Stratégie utilisée", _safe_str(optimization.get("strategy"))),
                ("Nombre de domaines sélectionnés", _safe_str(optimization.get("selectedDomainsCount"))),
                ("Nombre de questions sélectionnées", _safe_str(optimization.get("selectedQuestionsCount"))),
                ("Explication du chemin choisi", _safe_str(optimization.get("whyThisPath"))),
                ("Explication de l'effort", _safe_str(optimization.get("effortExplanation"))),
            ],
            styles,
        )
    )

    story.append(Paragraph("D. Tableau Best Path", styles["section"]))
    if best_path_table:
        table_rows = [
            [
                row.get("priority"),
                row.get("domainId"),
                row.get("domainName"),
                row.get("domainWeight"),
                row.get("currentDomainScore"),
                row.get("targetDomainScore"),
                row.get("globalScoreGain"),
                row.get("totalEffort"),
                row.get("efficiencyRatio"),
            ]
            for row in best_path_table
        ]
        col_widths = [
            USABLE_WIDTH * 0.06,
            USABLE_WIDTH * 0.07,
            USABLE_WIDTH * 0.18,
            USABLE_WIDTH * 0.08,
            USABLE_WIDTH * 0.09,
            USABLE_WIDTH * 0.09,
            USABLE_WIDTH * 0.12,
            USABLE_WIDTH * 0.09,
            USABLE_WIDTH * 0.12,
        ]
        story.append(
            _data_table(
                [
                    "Priorité",
                    "ID domaine",
                    "Nom du domaine",
                    "Poids",
                    "Score actuel",
                    "Score cible",
                    "Gain score global",
                    "Effort total",
                    "Ratio efficacité",
                ],
                table_rows,
                styles,
                col_widths=col_widths,
            )
        )
    else:
        story.append(Paragraph("Aucun domaine sélectionné dans le chemin optimal.", styles["body"]))

    story.append(Paragraph("E. Actions détaillées", styles["section"]))
    if detailed_actions:
        for domain_action in detailed_actions:
            story.append(
                Paragraph(
                    f"Priorité {_safe_str(domain_action.get('priority'))} — "
                    f"{_safe_str(domain_action.get('domainId'))} / "
                    f"{_safe_str(domain_action.get('domainName'))}",
                    styles["body_bold"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Objectif du domaine :</b> {_safe_str(domain_action.get('domainObjective'))}",
                    styles["body"],
                )
            )

            questions = _safe_list(domain_action.get("questionsToImprove"))
            if not questions:
                story.append(Paragraph("Aucune question à améliorer.", styles["body"]))
                story.append(Spacer(1, 6))
                continue

            for question in questions:
                if not isinstance(question, dict):
                    continue
                story.append(
                    Paragraph(
                        f"<b>{_safe_str(question.get('questionCode'))}</b> — "
                        f"{_safe_str(question.get('questionText'))}",
                        styles["body"],
                    )
                )
                story.append(
                    Paragraph(
                        f"Score actuel : {_safe_str(question.get('currentScore'))} | "
                        f"Score cible : {_safe_str(question.get('targetScore'))} | "
                        f"Effort de la question : {_safe_str(question.get('totalQuestionEffort'))}",
                        styles["body"],
                    )
                )

                transitions = [item for item in _safe_list(question.get("transitions")) if isinstance(item, dict)]
                if transitions:
                    transition_rows = [
                        [
                            f"{transition.get('from')} → {transition.get('to')}",
                            _safe_str(transition.get("transitionKey")),
                            transition.get("effort"),
                            _safe_str(transition.get("explanation")),
                        ]
                        for transition in transitions
                    ]
                    story.append(
                        _data_table(
                            ["Transition", "Clé", "Effort", "Explication"],
                            transition_rows,
                            styles,
                            col_widths=[
                                USABLE_WIDTH * 0.14,
                                USABLE_WIDTH * 0.16,
                                USABLE_WIDTH * 0.08,
                                USABLE_WIDTH * 0.62,
                            ],
                        )
                    )

                recommendation = _safe_str(question.get("groundedRecommendation") or question.get("recommendation"), "")
                if recommendation:
                    story.append(
                        Paragraph(
                            f"<b>Recommandation :</b> {recommendation}",
                            styles["body"],
                        )
                    )
                source = _safe_str(question.get("recommendationSource"), "")
                if source:
                    story.append(
                        Paragraph(
                            f"<b>Source :</b> {source}",
                            styles["body"],
                        )
                    )
                story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("Aucune action détaillée disponible.", styles["body"]))

    story.append(Paragraph("F. Validation mathématique", styles["section"]))
    story.append(
        _key_value_table(
            [
                ("Formule utilisée", _safe_str(validation.get("formula"))),
                ("Calcul", _safe_str(validation.get("calculation"))),
                ("Résultat targetReached", _format_bool_oui_non(validation.get("targetReached"))),
            ],
            styles,
        )
    )

    doc.build(story, onFirstPage=_draw_page_decorations, onLaterPages=_draw_page_decorations)
    return buffer.getvalue()
