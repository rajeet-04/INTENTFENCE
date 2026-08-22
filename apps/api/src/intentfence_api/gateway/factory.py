from typing import TYPE_CHECKING

from intentfence_api.semantic import OllamaProvider, StructuredSemanticJudge

from .adapters import Phase5SemanticAdapter
from .service import IntentFenceGateway

if TYPE_CHECKING:
    from intentfence_api.config import Settings


def build_application_gateway(
    settings: "Settings",
    *,
    semantic_judge: object | None = None,
) -> IntentFenceGateway:
    adapter = None
    judge = semantic_judge
    if judge is None and settings.semantic_enabled:
        provider = OllamaProvider.from_settings(settings)
        judge = StructuredSemanticJudge(provider)
    if judge is not None:
        adapter = Phase5SemanticAdapter(judge)
    return IntentFenceGateway(semantic_adapter=adapter)
