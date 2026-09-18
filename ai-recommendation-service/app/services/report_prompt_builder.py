import json
from typing import Any


def build_report_context(best_path_result: dict[str, Any]) -> str:
    data_context = {
        "task": "Generate a professional consulting report from the validated Best Path.",
        "scoreGlobalInitial": best_path_result["scoreGlobalInitial"],
        "scoreGlobalTarget": best_path_result["scoreGlobalTarget"],
        "scoreGlobalFinalEstimated": best_path_result["scoreGlobalFinalEstimated"],
        "gainTotal": best_path_result["gainTotal"],
        "effortTotal": best_path_result["effortTotal"],
        "targetReached": best_path_result["targetReached"],
        "bestPath": best_path_result["bestPath"],
        "calculationValidation": best_path_result.get("calculationValidation", {}),
    }
    return json.dumps(data_context, ensure_ascii=False, indent=2)
