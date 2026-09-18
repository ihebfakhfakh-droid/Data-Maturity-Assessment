import json
from pathlib import Path

from app.core.prompts import load_system_prompt
from app.models.recommendation_models import BestPathRequest, NDIFramework
from app.services.candidate_action_builder import build_candidate_actions
from app.services.framework_loader import FrameworkLoader
from app.services.ollama_service import OLLAMA_NUM_PREDICT, save_ollama_debug_payload
from app.services.prompt_builder import build_user_prompt
from app.services.score_calculator import compute_global_score

BASE_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    loader = FrameworkLoader()
    framework = loader.load()

    request = BestPathRequest(
        scoreGlobalActual=2.48,
        targetScore=3.48,
        currentScores={
            "DC.MQ.1": 2,
            "DC.MQ.2": 2,
            "DC.MQ.3": 4,
            "OD.MQ.1": 2,
            "FOI.MQ.1": 2,
            "DQ.MQ.1": 2,
        },
    )
    score_global_initial = request.scoreGlobalActual or compute_global_score(
        framework, request.currentScores
    )
    candidate_actions, _ = build_candidate_actions(framework, request.currentScores)
    system_prompt = load_system_prompt()
    user_prompt = build_user_prompt(
        framework=framework,
        request=request,
        score_global_initial=score_global_initial,
        candidate_actions=candidate_actions,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    payload = {
        "model": "debug-preview",
        "messages": messages,
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0.0, "num_predict": OLLAMA_NUM_PREDICT},
    }
    output_path = save_ollama_debug_payload(
        model="debug-preview",
        messages=messages,
        payload=payload,
    )
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
