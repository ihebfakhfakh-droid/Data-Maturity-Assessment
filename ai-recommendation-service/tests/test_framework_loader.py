import json
from pathlib import Path

import pytest

from app.services.framework_loader import (
    EXPECTED_TOTAL_WEIGHT,
    FrameworkLoader,
    FrameworkLoaderError,
    validate_domain_weights,
)


@pytest.fixture
def loader(tmp_path: Path) -> FrameworkLoader:
    return FrameworkLoader(framework_path=tmp_path / "ndi_framework.json")


def _write_framework(path: Path, domains: list[dict]) -> None:
    payload = {
        "framework": "NDI",
        "total_domains": len(domains),
        "effort_scale": {"1": "Simple"},
        "domains": domains,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_validate_domain_weights_requires_weight_field():
    raw = {
        "domains": [
            {"domain_id": "DG", "domain_name": "Data Governance", "questions": []}
        ]
    }
    with pytest.raises(FrameworkLoaderError, match="missing required field 'weight'"):
        validate_domain_weights(raw)


def test_validate_domain_weights_requires_sum_close_to_100_01():
    raw = {
        "domains": [
            {
                "domain_id": "DG",
                "domain_name": "Data Governance",
                "weight": 50.0,
                "questions": [],
            },
            {
                "domain_id": "DQ",
                "domain_name": "Data Quality",
                "weight": 40.0,
                "questions": [],
            },
        ]
    }
    with pytest.raises(FrameworkLoaderError, match="Sum of domain weights"):
        validate_domain_weights(raw)


def test_loader_validates_weights_on_load_raw(loader: FrameworkLoader, tmp_path: Path):
    framework_path = tmp_path / "ndi_framework.json"
    _write_framework(
        framework_path,
        [
            {
                "domain_id": "DG",
                "domain_name": "Data Governance",
                "weight": 50.005,
                "questions": [],
            },
            {
                "domain_id": "DQ",
                "domain_name": "Data Quality",
                "weight": 50.005,
                "questions": [],
            },
        ],
    )

    raw = loader.load_raw()
    assert len(raw["domains"]) == 2
    weights = loader.get_domain_weights(raw)
    assert weights["DG"] == 50.005
    assert round(sum(weights.values()), 2) == EXPECTED_TOTAL_WEIGHT


def test_real_framework_file_has_valid_weights():
    framework_path = (
        Path(__file__).resolve().parents[1] / "app" / "data" / "ndi_framework.json"
    )
    loader = FrameworkLoader(framework_path=framework_path)
    raw = loader.load_raw()
    weights = loader.get_domain_weights(raw)
    assert len(weights) == 14
    assert round(sum(weights.values()), 2) == EXPECTED_TOTAL_WEIGHT
