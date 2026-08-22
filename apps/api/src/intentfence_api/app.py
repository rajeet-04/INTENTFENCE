from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from intentfence_contracts import Decision

from .config import get_settings
from .gateway.demo import HotelAttackComparison, run_hotel_attack_demo
from .gateway.models import GatewayExecution
from .gateway.runtime import SandboxProtectedToolRuntime
from .gateway.service import IntentFenceGateway
from .gateway.tools import normalize_tool_request
from .schemas import AuthorizeRequest, GatewayInterceptRequest
from .services.policy_authorizer import authorize_request

settings = get_settings()
gateway = IntentFenceGateway()
tool_runtime = SandboxProtectedToolRuntime()

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
    return authorize_request(request)


@app.post("/gateway/intercept", response_model=GatewayExecution)
def gateway_intercept(request: GatewayInterceptRequest) -> GatewayExecution:
    tool_request = request.tool_request
    try:
        normalized = normalize_tool_request(
            request_id=tool_request.request_id,
            session_id=tool_request.session_id,
            agent_id=tool_request.agent_id,
            intent_id=tool_request.intent_id,
            tool=tool_request.tool,
            arguments=tool_request.arguments,
            data_refs=tool_request.data_refs,
            source_context=tool_request.source_context,
            timestamp=tool_request.timestamp,
        )
        handler = tool_runtime.handler(tool_request.tool)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return gateway.intercept(
        normalized,
        request.intent_contract,
        request.security_context,
        handler=handler,
        data_labels=request.data_labels,
        mode=request.mode,
        scenario_id=request.scenario_id,
    )


@app.post("/demo/hotel-attack", response_model=HotelAttackComparison)
def hotel_attack_demo() -> HotelAttackComparison:
    return run_hotel_attack_demo()
