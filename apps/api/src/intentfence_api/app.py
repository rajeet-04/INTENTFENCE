from collections.abc import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from intentfence_contracts import Decision

from .agent.models import AgentChatRequest, ErrorEvent
from .agent.orchestrator import AgentError, Phase10ChatOrchestrator
from .agent.sessions import (
    AgentSessionStore,
    IntentRevisionRequired,
    UnknownAgentSession,
)
from .agent.sse import encode_sse
from .agent.tool_executor import OllamaToolExecutor
from .benchmarks import latest_benchmark_payload
from .config import get_settings
from .gateway.adapters import Phase5SemanticAdapter
from .gateway.demo import HotelAttackComparison, run_hotel_attack_demo
from .gateway.mcp import run_mcp_tool_call
from .gateway.models import GatewayExecution
from .gateway.ollama_agent import OllamaAgentClient
from .gateway.ollama_web import OllamaWebProvider
from .gateway.runtime import SandboxProtectedToolRuntime
from .gateway.service import IntentFenceGateway
from .gateway.tools import normalize_tool_request
from .schemas import AuthorizeRequest, GatewayInterceptRequest, McpInterceptRequest
from .semantic import build_default_semantic_judge
from .services.policy_authorizer import authorize_request

settings = get_settings()
gateway = IntentFenceGateway(
    semantic_adapter=Phase5SemanticAdapter(build_default_semantic_judge(settings))
)
tool_runtime = SandboxProtectedToolRuntime()
agent_session_store = AgentSessionStore()
agent_client = OllamaAgentClient(
    base_url=settings.agent_ollama_base_url,
    model=settings.agent_ollama_model,
    context_length=settings.agent_ollama_context_length,
)
agent_web_provider = OllamaWebProvider(
    api_key=settings.ollama_api_key if settings.live_web_enabled else None,
    base_url=settings.ollama_web_base_url,
)
agent_tool_executor = OllamaToolExecutor(
    runtime=tool_runtime,
    web_provider=agent_web_provider,
)
chat_orchestrator = Phase10ChatOrchestrator(
    client=agent_client,
    executor=agent_tool_executor,
    session_store=agent_session_store,
)

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


@app.get("/benchmarks/latest")
def latest_benchmark() -> dict:
    return latest_benchmark_payload(settings.database_url)


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

    return gateway.intercept_authoritative(
        normalized,
        request.intent_contract,
        handler=handler,
        scenario_id=request.scenario_id,
    )


@app.post("/mcp/tool-call", response_model=GatewayExecution)
def mcp_tool_call(request: McpInterceptRequest) -> GatewayExecution:
    return run_mcp_tool_call(
        request.call,
        request.intent_contract,
        gateway=gateway,
        runtime=tool_runtime,
    )


@app.post("/demo/hotel-attack", response_model=HotelAttackComparison)
def hotel_attack_demo() -> HotelAttackComparison:
    return run_hotel_attack_demo()


@app.post("/agent/chat/stream")
def agent_chat_stream(request: AgentChatRequest) -> StreamingResponse:
    try:
        session = agent_session_store.resolve(
            session_id=request.session_id,
            objective=request.objective,
            web_research_enabled=request.web_research_enabled,
            revise_intent=request.revise_intent,
        )
    except (UnknownAgentSession, IntentRevisionRequired) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    def event_iterator() -> Iterator[str]:
        last_sequence = 0
        try:
            for event in chat_orchestrator.stream(request=request, session=session):
                last_sequence = event.sequence
                yield encode_sse(event)
        except AgentError as exc:
            yield encode_sse(
                ErrorEvent(
                    sequence=last_sequence + 1,
                    code=exc.code,
                    recoverable=exc.recoverable,
                    message=exc.message,
                )
            )
        except Exception:
            yield encode_sse(
                ErrorEvent(
                    sequence=last_sequence + 1,
                    code="INTERNAL_AGENT_ERROR",
                    recoverable=True,
                    message="The agent stopped safely. Retry the request.",
                )
            )

    return StreamingResponse(
        event_iterator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
