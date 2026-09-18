import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.recommendation_models import NDIFramework

EXPECTED_TOTAL_WEIGHT = 100.01
WEIGHT_SUM_TOLERANCE = 0.01


class FrameworkLoaderError(Exception):
    """Raised when the NDI framework file cannot be loaded."""


def validate_domain_weights(raw: dict[str, Any]) -> None:
    domains = raw.get("domains")
    if not isinstance(domains, list) or not domains:
        raise FrameworkLoaderError("NDI framework has no domains")

    total_weight = 0.0
    for index, domain in enumerate(domains):
        if not isinstance(domain, dict):
            raise FrameworkLoaderError(f"Domain at index {index} is not a valid object")

        domain_id = domain.get("domain_id") or f"index_{index}"
        if "weight" not in domain:
            raise FrameworkLoaderError(
                f"Domain '{domain_id}' is missing required field 'weight'"
            )

        weight_value = domain.get("weight")
        try:
            weight = float(weight_value)
        except (TypeError, ValueError) as exc:
            raise FrameworkLoaderError(
                f"Domain '{domain_id}' has invalid weight value: {weight_value!r}"
            ) from exc

        if weight <= 0:
            raise FrameworkLoaderError(
                f"Domain '{domain_id}' has invalid weight: must be greater than 0"
            )

        total_weight += weight

    rounded_total = round(total_weight, 2)
    if abs(rounded_total - EXPECTED_TOTAL_WEIGHT) > WEIGHT_SUM_TOLERANCE:
        raise FrameworkLoaderError(
            "Sum of domain weights must be close to "
            f"{EXPECTED_TOTAL_WEIGHT}, got {rounded_total}"
        )


class FrameworkLoader:
    def __init__(self, framework_path: Path | None = None) -> None:
        self.framework_path = framework_path or settings.FRAMEWORK_PATH

    def load_raw(self) -> dict[str, Any]:
        if not self.framework_path.exists():
            raise FrameworkLoaderError(
                f"Framework file not found: {self.framework_path}"
            )

        try:
            raw = json.loads(self.framework_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FrameworkLoaderError(
                f"Invalid framework file: {self.framework_path}"
            ) from exc

        validate_domain_weights(raw)
        return raw

    def load(self) -> NDIFramework:
        try:
            return NDIFramework.model_validate(self.load_raw())
        except ValueError as exc:
            raise FrameworkLoaderError(
                f"Invalid framework file: {self.framework_path}"
            ) from exc

    def get_domain_weights(self, raw: dict[str, Any] | None = None) -> dict[str, float]:
        framework_raw = raw if raw is not None else self.load_raw()
        return {
            str(domain["domain_id"]): float(domain["weight"])
            for domain in framework_raw.get("domains", [])
        }
