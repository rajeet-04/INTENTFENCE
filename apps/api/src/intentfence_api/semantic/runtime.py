from typing import TYPE_CHECKING

from .judge import SemanticJudge, StructuredSemanticJudge
from .orchestrator import HybridSemanticJudge
from .providers import OllamaProvider

if TYPE_CHECKING:
    from intentfence_api.config import Settings


def build_default_semantic_judge(
    settings: "Settings",
    *,
    cloud_judge: SemanticJudge | None = None,
) -> HybridSemanticJudge:
    local_judge = StructuredSemanticJudge(OllamaProvider.from_settings(settings))
    return HybridSemanticJudge(local_judge, cloud_judge)
