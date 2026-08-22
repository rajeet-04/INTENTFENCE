from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from intentfence_contracts import Decision

from .config import get_settings
from .schemas import AuthorizeRequest
from .services.foundation_authorizer import authorize_foundation

settings = get_settings()

app = FastAPI(
    title="IntentFence API",
    version="0.1.0",
    docs_url="/docs" if settings.env != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "intentfence-api"}


@app.post("/authorize", response_model=Decision)
def authorize(request: AuthorizeRequest) -> Decision:
    return authorize_foundation(request)
