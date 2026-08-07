import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.debug_routes import router as debug_router
from app.api.recommendation_routes import router as recommendation_router
from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    startup_logger = logging.getLogger("uvicorn.error")
    message = f"Ollama configured model: {settings.effective_ollama_model}"
    startup_logger.info(
        "%s | USE_OLLAMA=%s | base_url=%s | env_file=%s",
        message,
        settings.USE_OLLAMA,
        settings.OLLAMA_BASE_URL,
        settings.model_config["env_file"],
    )
    print(message, flush=True)
    yield


app = FastAPI(
    title="AI Recommendation Service",
    description=(
        "Microservice de recommandations IA pour le framework NDI. "
        "Calcule le Best Path déterministe, enrichit éventuellement les explications via Ollama, "
        "et génère le rapport PDF."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(recommendation_router)
app.include_router(debug_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": exc.__class__.__name__,
        },
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
