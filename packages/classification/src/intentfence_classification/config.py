from dataclasses import dataclass, field


def _default_blocked_destinations() -> frozenset[str]:
    return frozenset(
        {
            "169.254.169.254",
            "metadata.google.internal",
            "metadata.goog",
        }
    )


@dataclass(frozen=True)
class ClassifierConfig:
    workspace_roots: tuple[str, ...] = ()
    blocked_destinations: frozenset[str] = field(default_factory=_default_blocked_destinations)
    trusted_destinations: frozenset[str] = frozenset()
    known_external_domains: frozenset[str] = frozenset()
