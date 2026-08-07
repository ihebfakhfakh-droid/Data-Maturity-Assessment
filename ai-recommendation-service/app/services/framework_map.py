from typing import Any

from app.models.recommendation_models import NDIFramework
from app.services.score_calculator import (
    compute_domain_score,
    get_domain_answered_scores,
)


def build_framework_map(framework_raw: dict[str, Any]) -> dict[str, Any]:
    framework_map: dict[str, Any] = {}
    for domain in framework_raw.get("domains", []):
        domain_id = domain.get("domain_id")
        if not domain_id:
            continue
        questions_map: dict[str, Any] = {}
        for question in domain.get("questions", []):
            question_id = question.get("id")
            if not question_id:
                continue
            questions_map[str(question_id)] = {
                "questionText": question.get("text", ""),
                "effortTransitions": question.get("effort_transitions", {}),
            }
        framework_map[str(domain_id)] = {
            "domainName": domain.get("domain_name", ""),
            "weight": float(domain["weight"]),
            "questions": questions_map,
        }
    return framework_map


def build_framework_map_from_model(framework: NDIFramework) -> dict[str, Any]:
    framework_map: dict[str, Any] = {}
    for domain in framework.domains:
        questions_map: dict[str, Any] = {}
        for question in domain.questions:
            questions_map[question.id] = {
                "questionText": question.text,
                "effortTransitions": {
                    key: {"effort": transition.effort, "explanation": transition.explanation}
                    for key, transition in question.effort_transitions.items()
                },
            }
        framework_map[domain.domain_id] = {
            "domainName": domain.domain_name,
            "weight": domain.weight,
            "questions": questions_map,
        }
    return framework_map


def compute_current_domain_score(
    framework: NDIFramework,
    domain_id: str,
    current_scores: dict[str, int],
) -> int | None:
    domain = framework.get_domain(domain_id)
    if domain is None:
        return None
    answered = get_domain_answered_scores(domain, current_scores)
    if not answered:
        return None
    return compute_domain_score(answered)
