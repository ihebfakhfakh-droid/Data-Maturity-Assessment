import io
import re
from typing import Any

import pandas as pd

from app.models.recommendation_models import NDIFramework
from app.services.score_calculator import (
    build_domain_scores_map,
    compute_active_domains_total_weight,
    compute_global_score,
    round_score,
)

QUESTION_CODE_COLUMNS = (
    "questioncode",
    "question_code",
    "question id",
    "questionid",
    "code",
    "question",
)
SCORE_COLUMNS = ("score", "value", "rating", "niveau", "level", "note")


class ClientExcelLoaderError(ValueError):
    """Raised when the client Excel file cannot be parsed."""


def build_legacy_question_code_map(framework: NDIFramework) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for domain in framework.domains:
        legacy_prefix = f"ndi_{domain.domain_id.lower()}"
        for index, question in enumerate(domain.questions, start=1):
            mapping[f"{legacy_prefix}_{index:02d}"] = question.id
            mapping[f"{legacy_prefix}_{index}"] = question.id
    return mapping


def normalize_question_code(
    raw_code: str,
    framework: NDIFramework,
    legacy_map: dict[str, str] | None = None,
) -> str | None:
    code = str(raw_code).strip()
    if not code:
        return None

    if framework.get_question(code) is not None:
        return code

    normalized_legacy = code.lower().replace("-", "_")
    legacy_lookup = legacy_map or build_legacy_question_code_map(framework)
    if normalized_legacy in legacy_lookup:
        return legacy_lookup[normalized_legacy]

    # Some exports use DG.MQ.1 with spaces or alternate separators.
    compact = code.replace(" ", "")
    if framework.get_question(compact) is not None:
        return compact

    return None


def _normalize_column_name(column: Any) -> str:
    return re.sub(r"\s+", " ", str(column).strip().lower())


def _find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {_normalize_column_name(column): column for column in columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    for column in columns:
        normalized_name = _normalize_column_name(column)
        if any(candidate in normalized_name for candidate in candidates):
            return column
    return None


def _looks_like_question_code(value: Any) -> bool:
    text = str(value).strip()
    if not text:
        return False
    return bool(
        re.match(r"^[A-Za-z]{2,4}\.MQ\.\d+$", text)
        or re.match(r"^ndi_[a-z0-9_]+$", text.lower())
    )


def _parse_score_value(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return None
    if 0 <= score <= 5:
        return score
    return None


def _extract_long_format_scores(
    dataframe: pd.DataFrame,
    framework: NDIFramework,
    legacy_map: dict[str, str],
) -> dict[str, int]:
    columns = [str(column) for column in dataframe.columns]
    question_column = _find_column(columns, QUESTION_CODE_COLUMNS)
    score_column = _find_column(columns, SCORE_COLUMNS)

    if question_column is None or score_column is None:
        if dataframe.shape[1] < 2:
            raise ClientExcelLoaderError(
                "Format Excel non reconnu. Utilisez au minimum deux colonnes : questionCode et score."
            )
        question_column = columns[0]
        score_column = columns[1]

    current_scores: dict[str, int] = {}
    for _, row in dataframe.iterrows():
        question_code = normalize_question_code(row[question_column], framework, legacy_map)
        score = _parse_score_value(row[score_column])
        if question_code is None or score is None:
            continue
        current_scores[question_code] = score

    if not current_scores:
        raise ClientExcelLoaderError(
            "Aucun score valide trouvé dans le fichier Excel. "
            "Vérifiez les colonnes questionCode et score."
        )
    return current_scores


def _extract_wide_format_scores(
    dataframe: pd.DataFrame,
    framework: NDIFramework,
    legacy_map: dict[str, str],
) -> dict[str, int]:
    current_scores: dict[str, int] = {}
    for column in dataframe.columns:
        question_code = normalize_question_code(str(column), framework, legacy_map)
        if question_code is None:
            continue
        for value in dataframe[column].tolist():
            score = _parse_score_value(value)
            if score is not None:
                current_scores[question_code] = score
                break

    if not current_scores:
        raise ClientExcelLoaderError(
            "Format Excel large non reconnu. Aucune colonne de question valide n'a été détectée."
        )
    return current_scores


def parse_client_scores_from_excel(
    file_bytes: bytes,
    framework: NDIFramework,
) -> dict[str, int]:
    try:
        dataframe = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception as exc:
        raise ClientExcelLoaderError(f"Impossible de lire le fichier Excel : {exc}") from exc

    if dataframe.empty:
        raise ClientExcelLoaderError("Le fichier Excel est vide.")

    dataframe = dataframe.dropna(how="all")
    legacy_map = build_legacy_question_code_map(framework)
    columns = [str(column) for column in dataframe.columns]

    question_column = _find_column(columns, QUESTION_CODE_COLUMNS)
    score_column = _find_column(columns, SCORE_COLUMNS)
    if question_column is not None and score_column is not None:
        return _extract_long_format_scores(dataframe, framework, legacy_map)

    if any(_looks_like_question_code(column) for column in columns):
        return _extract_wide_format_scores(dataframe, framework, legacy_map)

    sample_first_column = dataframe.iloc[:, 0].astype(str).head(10).tolist()
    if any(_looks_like_question_code(value) for value in sample_first_column):
        return _extract_long_format_scores(dataframe, framework, legacy_map)

    raise ClientExcelLoaderError(
        "Format Excel non reconnu. Attendu : colonnes questionCode + score, "
        "ou colonnes larges avec les codes question NDI."
    )


def build_client_assessment_payload(
    framework: NDIFramework,
    current_scores: dict[str, int],
) -> dict[str, Any]:
    domain_scores_map = build_domain_scores_map(framework, current_scores)
    total_weights = compute_active_domains_total_weight(framework, current_scores)
    score_global_initial = compute_global_score(framework, current_scores)

    domain_scores = {domain_id: values[0] for domain_id, values in domain_scores_map.items()}
    domain_weights = {domain_id: values[1] for domain_id, values in domain_scores_map.items()}
    weighted_scores = {
        domain_id: round_score((values[0] * values[1]) / total_weights)
        if total_weights
        else 0.0
        for domain_id, values in domain_scores_map.items()
    }

    return {
        "scoreGlobalActual": score_global_initial,
        "targetScore": None,
        "totalWeights": round_score(total_weights),
        "domainWeights": domain_weights,
        "domainScores": domain_scores,
        "weightedScores": weighted_scores,
        "currentScores": current_scores,
    }
