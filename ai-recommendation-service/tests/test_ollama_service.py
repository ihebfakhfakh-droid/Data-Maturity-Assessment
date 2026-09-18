import json

import pytest

from app.services.ollama_service import OLLAMA_NUM_PREDICT, OllamaService, OllamaServiceError


def test_chat_json_uses_system_and_user_roles(monkeypatch, tmp_path):
    captured: dict = {}

    class ClientCtx:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None):
            captured["messages"] = json["messages"]

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"message": {"content": '{"ok": true}'}}

            return Response()

    monkeypatch.setattr("app.services.ollama_service.httpx.Client", lambda timeout: ClientCtx())
    monkeypatch.setattr(
        "app.services.ollama_service.settings.DEBUG_PAYLOAD_PATH",
        tmp_path / "latest_ollama_payload.json",
    )

    service = OllamaService()
    service.chat_json("system rules", '{"task":"data"}')

    assert captured["messages"] == [
        {"role": "system", "content": "system rules"},
        {"role": "user", "content": '{"task":"data"}'},
    ]

    debug_payload = json.loads((tmp_path / "latest_ollama_payload.json").read_text(encoding="utf-8"))
    assert debug_payload["system_prompt"] == "system rules"
    assert debug_payload["user_prompt"] == '{"task":"data"}'
    assert debug_payload["payload"]["format"] == "json"
    assert debug_payload["payload"]["think"] is False
    assert debug_payload["payload"]["stream"] is False
    assert debug_payload["payload"]["options"]["temperature"] == 0.0
    assert debug_payload["payload"]["options"]["num_predict"] == OLLAMA_NUM_PREDICT


def test_call_ollama_raises_when_only_thinking_is_returned(monkeypatch, tmp_path):
    class ClientCtx:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None):
            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {
                        "message": {
                            "content": "",
                            "thinking": "Reasoning about the best path...",
                        },
                        "done_reason": "length",
                    }

            return Response()

    monkeypatch.setattr("app.services.ollama_service.httpx.Client", lambda timeout: ClientCtx())
    monkeypatch.setattr(
        "app.services.ollama_service.settings.DEBUG_PAYLOAD_PATH",
        tmp_path / "latest_ollama_payload.json",
    )

    service = OllamaService()
    with pytest.raises(OllamaServiceError, match="Disable thinking mode with think=false"):
        service.chat_json("system rules", '{"task":"data"}')
