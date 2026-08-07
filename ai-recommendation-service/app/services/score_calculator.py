from app.models.recommendation_models import FrameworkDomain, FrameworkQuestion, NDIFramework


def round_score(value: float, digits: int = 2) -> float:
    return round(value, digits)


def get_domain_answered_scores(
    domain: FrameworkDomain, current_scores: dict[str, int]
) -> dict[str, int]:
    answered: dict[str, int] = {}
    for question in domain.questions:
        if question.id in current_scores:
            answered[question.id] = current_scores[question.id]
    return answered


def compute_domain_score(answered_scores: dict[str, int]) -> int:
    if not answered_scores:
        return 0
    return min(answered_scores.values())


def compute_global_score(
    framework: NDIFramework, current_scores: dict[str, int]
) -> float:
    weighted_total = 0.0
    total_weight = 0.0

    for domain in framework.domains:
        answered = get_domain_answered_scores(domain, current_scores)
        if not answered:
            continue
        domain_score = compute_domain_score(answered)
        weighted_total += domain_score * domain.weight
        total_weight += domain.weight

    if total_weight == 0:
        return 0.0
    return round_score(weighted_total / total_weight)


def compute_global_score_from_domain_scores(
    domain_scores: dict[str, tuple[int, float]],
) -> float:
    weighted_total = 0.0
    total_weight = 0.0
    for score, weight in domain_scores.values():
        weighted_total += score * weight
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return round_score(weighted_total / total_weight)


def compute_question_effort(
    framework: NDIFramework,
    question_id: str,
    current_score: int,
    target_score: int,
) -> int:
    question = framework.get_question(question_id)
    if question is None:
        raise ValueError(f"Unknown question: {question_id}")
    return question.effort_for_transition(current_score, target_score)


def get_transition_explanations(
    framework: NDIFramework,
    question_id: str,
    current_score: int,
    target_score: int,
) -> list[str]:
    question = framework.get_question(question_id)
    if question is None:
        return []
    return question.transition_explanations(current_score, target_score)


def compute_total_framework_weight(framework: NDIFramework) -> float:
    return sum(domain.weight for domain in framework.domains)


def round_gain(value: float) -> float:
    return round(value, 3)


def build_expected_transitions(
    framework: NDIFramework,
    question_id: str,
    current_score: int,
    target_score: int,
) -> list[dict[str, int | str]]:
    question = framework.get_question(question_id)
    if question is None or target_score <= current_score:
        return []

    transitions: list[dict[str, int | str]] = []
    for level in range(current_score, target_score):
        key = f"{level}_to_{level + 1}"
        transition = question.effort_transitions.get(key)
        if transition is None:
            continue
        transitions.append(
            {
                "from": level,
                "to": level + 1,
                "transitionKey": key,
                "effort": transition.effort,
                "explanation": transition.explanation,
            }
        )
    return transitions


def compute_active_domains_total_weight(
    framework: NDIFramework, current_scores: dict[str, int]
) -> float:
    total_weight = 0.0
    for domain in framework.domains:
        if get_domain_answered_scores(domain, current_scores):
            total_weight += domain.weight
    return total_weight


def compute_expected_global_gain(
    framework: NDIFramework,
    current_scores: dict[str, int],
    domain_id: str,
    current_domain_score: int,
    target_domain_score: int,
    *,
    total_weights: float | None = None,
) -> float:
    domain = framework.get_domain(domain_id)
    if domain is None:
        return 0.0
    denominator = total_weights if total_weights is not None else compute_total_framework_weight(framework)
    if denominator <= 0:
        return 0.0
    return round_gain(
        (target_domain_score - current_domain_score) * domain.weight / denominator
    )


def build_domain_scores_map(
    framework: NDIFramework, current_scores: dict[str, int]
) -> dict[str, tuple[int, float]]:
    result: dict[str, tuple[int, float]] = {}
    for domain in framework.domains:
        answered = get_domain_answered_scores(domain, current_scores)
        if not answered:
            continue
        result[domain.domain_id] = (
            compute_domain_score(answered),
            domain.weight,
        )
    return result
