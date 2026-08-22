from abc import ABC, abstractmethod

from intentfence_classification import (
    AuthorityLevel,
    classify_authority,
    find_argument_authority_claim,
    is_path_under_root,
    normalize_destination,
    normalize_path,
)
from intentfence_contracts import (
    DecisionType,
    DestinationClass,
    ResourceClass,
    RuleStrength,
    Sensitivity,
)

from .models import EvaluationContext, RuleOutcome

FORBIDDEN_TOOL_RULE_ID = "FORBIDDEN_TOOL"
EXTERNAL_AUTHORITY_OVERRIDE_RULE_ID = "EXTERNAL_AUTHORITY_OVERRIDE"
FORBIDDEN_RESOURCE_RULE_ID = "FORBIDDEN_RESOURCE"
SECRET_ACCESS_UNRELATED_TO_INTENT_RULE_ID = "SECRET_ACCESS_UNRELATED_TO_INTENT"
CRITICAL_DATA_TO_UNTRUSTED_DESTINATION_RULE_ID = "CRITICAL_DATA_TO_UNTRUSTED_DESTINATION"
CONSEQUENTIAL_ACTION_UNAPPROVED_RULE_ID = "CONSEQUENTIAL_ACTION_UNAPPROVED"
WRITE_OUTSIDE_WORKSPACE_RULE_ID = "WRITE_OUTSIDE_WORKSPACE"
PURPOSE_BOUND_DATA_MISUSE_RULE_ID = "PURPOSE_BOUND_DATA_MISUSE"

_FORBIDDEN_CLASS_TOKENS: dict[str, frozenset[ResourceClass]] = {
    "credentials": frozenset({ResourceClass.CREDENTIAL}),
    "credential": frozenset({ResourceClass.CREDENTIAL}),
    "ssh_keys": frozenset({ResourceClass.CREDENTIAL}),
    "secrets": frozenset({ResourceClass.SECRET}),
    "secret": frozenset({ResourceClass.SECRET}),
    "environment_secrets": frozenset({ResourceClass.SECRET}),
}

_WRITER_TOOL_PREFIXES = ("write", "create", "delete", "remove", "move")

_TRANSFER_TOOLS = frozenset({"http_request", "send_message"})

_AUTHORITY_PURPOSES = frozenset({"authentication", "authorization", "auth"})


def _outcome(
    rule_id: str,
    strength: RuleStrength,
    decision: DecisionType,
    reason: str,
    risk: float,
) -> RuleOutcome:
    return RuleOutcome(
        rule_id=rule_id,
        rule_strength=strength,
        decision=decision,
        reason=reason,
        risk_contribution=risk,
    )


def _normalized_set(entries: list[str]) -> set[str]:
    """Canonicalize grant entries while preserving their directory-scope marker."""
    normalized: set[str] = set()
    for entry in entries:
        scoped = entry.rstrip().endswith("/")
        path = normalize_path(entry)
        normalized.add(f"{path}/" if scoped else path)
    return normalized


def _resource_matches_allowed(resource_ref: str, allowed: set[str]) -> bool:
    """Authorize a resource only by canonical identity or an explicit scoped root.

    A trailing "/" marks an allowed entry as a directory scope; containment under
    that scope is granted. Bare-name equality never grants filesystem access.
    """
    normalized_ref = normalize_path(resource_ref)
    if normalized_ref in allowed:
        return True
    return any(
        entry.endswith("/") and normalized_ref.startswith(entry) for entry in allowed
    )


class PolicyRule(ABC):
    rule_id: str
    rule_strength: RuleStrength
    description: str

    @abstractmethod
    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        """Return a deterministic RuleOutcome when this rule matches, otherwise None."""


class ExternalContentAuthorityRule(PolicyRule):
    rule_id = EXTERNAL_AUTHORITY_OVERRIDE_RULE_ID
    rule_strength = RuleStrength.HARD_BLOCK
    description = "External content cannot modify authorization."

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        source_context = context.input.request.source_context
        if classify_authority(source_context) == AuthorityLevel.FULL:
            return None
        claim = find_argument_authority_claim(context.input.request.arguments)
        if claim is None:
            return None
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.BLOCK,
            (
                f"Non-user content attempted to modify authorization "
                f"(matched authority claim '{claim}'). External content cannot grant authority."
            ),
            1.0,
        )


class ForbiddenToolRule(PolicyRule):
    rule_id = FORBIDDEN_TOOL_RULE_ID
    rule_strength = RuleStrength.HARD_BLOCK
    description = "Tools outside the Intent Contract allow-list are forbidden."

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        contract = context.input.contract
        tool = context.input.request.tool
        if tool in contract.allowed_tools:
            return None
        if tool in contract.approval_required_actions:
            return None
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.BLOCK,
            f"Tool '{tool}' is not authorized by the active Intent Contract.",
            1.0,
        )


class ForbiddenResourceRule(PolicyRule):
    rule_id = FORBIDDEN_RESOURCE_RULE_ID
    rule_strength = RuleStrength.HARD_BLOCK
    description = "Resources named or classed as forbidden by the Intent Contract are blocked."

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        contract = context.input.contract
        forbidden = [entry.lower() for entry in contract.forbidden_resources]
        if not forbidden:
            return None
        resource_ref = context.resource_ref
        if resource_ref is not None:
            normalized_ref = normalize_path(resource_ref)
            base_name = normalized_ref.rsplit("/", 1)[-1]
            for entry in forbidden:
                if normalized_ref == entry or base_name == entry:
                    return self._block(f"'{resource_ref}' is explicitly forbidden")
        resource_class = context.resource_class
        if resource_class is not None:
            for entry in forbidden:
                if resource_class in _FORBIDDEN_CLASS_TOKENS.get(entry, frozenset()):
                    return self._block(
                        f"Classified resource class {resource_class.value} matches "
                        f"forbidden boundary '{entry}'"
                    )
        return None

    def _block(self, detail: str) -> RuleOutcome:
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.BLOCK,
            f"Forbidden resource access blocked: {detail}.",
            1.0,
        )


class SecretAccessUnrelatedToIntentRule(PolicyRule):
    rule_id = SECRET_ACCESS_UNRELATED_TO_INTENT_RULE_ID
    rule_strength = RuleStrength.HARD_BLOCK
    description = (
        "Credential or secret resources are blocked unless the Intent Contract explicitly "
        "authorizes them."
    )

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        if context.resource_class not in {ResourceClass.SECRET, ResourceClass.CREDENTIAL}:
            return None
        resource_ref = context.resource_ref
        if resource_ref is not None and _resource_matches_allowed(
            resource_ref, _normalized_set(context.input.contract.allowed_resources)
        ):
            return None
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.BLOCK,
            (
                f"Access to classified {context.resource_class.value} resource "
                f"'{resource_ref}' is unrelated to the delegated intent and was not "
                f"explicitly authorized."
            ),
            1.0,
        )


class CriticalDataDestinationRule(PolicyRule):
    rule_id = CRITICAL_DATA_TO_UNTRUSTED_DESTINATION_RULE_ID
    rule_strength = RuleStrength.HARD_BLOCK
    description = "Critical data cannot move to an unknown external or blocked destination."

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        labels = context.input.data_labels
        critical_refs = [
            data_ref
            for data_ref in context.input.request.data_refs
            if data_ref in labels and labels[data_ref].sensitivity == Sensitivity.CRITICAL
        ]
        if not critical_refs:
            return None
        if context.destination_class in {
            DestinationClass.UNKNOWN_EXTERNAL,
            DestinationClass.BLOCKED,
        }:
            return _outcome(
                self.rule_id,
                self.rule_strength,
                DecisionType.BLOCK,
                (
                    f"Critical data ({', '.join(critical_refs)}) cannot be sent to "
                    f"{context.destination_class.value} destination "
                    f"'{context.destination}'."
                ),
                1.0,
            )
        return None


class ConsequentialActionApprovalRule(PolicyRule):
    rule_id = CONSEQUENTIAL_ACTION_UNAPPROVED_RULE_ID
    rule_strength = RuleStrength.REQUIRE_APPROVAL
    description = "Consequential actions require explicit human approval before execution."

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        contract = context.input.contract
        tool = context.input.request.tool
        if tool not in contract.approval_required_actions:
            return None
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.REQUIRE_APPROVAL,
            (
                f"Consequential action '{tool}' requires human approval before it can run."
            ),
            0.6,
        )


class WriteOutsideWorkspaceRule(PolicyRule):
    rule_id = WRITE_OUTSIDE_WORKSPACE_RULE_ID
    rule_strength = RuleStrength.REQUIRE_APPROVAL
    description = "Writes must target the approved workspace or an explicitly approved resource."

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        tool = context.input.request.tool
        if not tool.lower().startswith(_WRITER_TOOL_PREFIXES):
            return None
        resource_ref = context.resource_ref
        if resource_ref is None:
            return self._approval(
                f"Write action '{tool}' has no determinable target path."
            )
        allowed = _normalized_set(context.input.contract.allowed_resources)
        if _resource_matches_allowed(resource_ref, allowed):
            return None
        normalized_ref = normalize_path(resource_ref)
        if any(
            is_path_under_root(normalized_ref, root) for root in context.config.workspace_roots
        ):
            return None
        return self._approval(
            f"Write target '{resource_ref}' is outside the approved workspace boundaries."
        )

    def _approval(self, reason: str) -> RuleOutcome:
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.REQUIRE_APPROVAL,
            reason,
            0.6,
        )


class PurposeBoundDataRule(PolicyRule):
    rule_id = PURPOSE_BOUND_DATA_MISUSE_RULE_ID
    rule_strength = RuleStrength.REQUIRE_APPROVAL
    description = (
        "Data bound to a purpose may only move to destinations that purpose allows; "
        "critical violations escalate to a hard block."
    )

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        tool = context.input.request.tool
        if tool not in _TRANSFER_TOOLS:
            return None
        labels = context.input.data_labels
        for data_ref in context.input.request.data_refs:
            label = labels.get(data_ref)
            if label is None or label.purpose.lower() not in _AUTHORITY_PURPOSES:
                continue
            approved_classes = {DestinationClass.TRUSTED, DestinationClass.USER_APPROVED}
            if context.destination_class in approved_classes:
                continue
            allowed_destinations = {
                normalize_destination(entry) for entry in label.allowed_destinations
            }
            destination_host = (
                normalize_destination(context.destination) if context.destination else None
            )
            if destination_host and destination_host in allowed_destinations:
                continue
            if label.sensitivity == Sensitivity.CRITICAL:
                return self._hard_block(data_ref, label.data_type, context.destination)
            if label.sensitivity in {Sensitivity.CONFIDENTIAL, Sensitivity.INTERNAL}:
                return self._approval(data_ref, label.data_type)
        return None

    def _hard_block(self, data_ref: str, data_type: str, destination: str | None) -> RuleOutcome:
        return _outcome(
            self.rule_id,
            RuleStrength.HARD_BLOCK,
            DecisionType.BLOCK,
            (
                f"{data_type} data '{data_ref}' is bound to authentication purposes and "
                f"cannot be transferred to '{destination}'."
            ),
            1.0,
        )

    def _approval(self, data_ref: str, data_type: str) -> RuleOutcome:
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.REQUIRE_APPROVAL,
            (
                f"{data_type} data '{data_ref}' is leaving its declared purpose boundary; "
                f"human approval is required."
            ),
            0.6,
        )


DEFAULT_RULES: tuple[PolicyRule, ...] = (
    ExternalContentAuthorityRule(),
    ForbiddenToolRule(),
    ForbiddenResourceRule(),
    SecretAccessUnrelatedToIntentRule(),
    CriticalDataDestinationRule(),
    ConsequentialActionApprovalRule(),
    WriteOutsideWorkspaceRule(),
    PurposeBoundDataRule(),
)
