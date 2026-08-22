"""Stateful authorization and action-chain analysis for IntentFence."""

from .chain import (
    EXTERNAL_NETWORK_TOOLS,
    MESSAGE_TOOLS,
    SECRET_ACCESS_TOOLS,
    chain_tools,
    external_transfer_in_chain,
    parse_chain_entries,
    secret_access_in_chain,
)
from .drift import IntentDriftSignal, NullDriftSignal, PassthroughDriftSignal
from .engine import SessionStateTracker, evaluate_stateful_policy
from .lifecycle import (
    ALLOW_RISK_WEIGHT,
    APPROVAL_RISK_WEIGHT,
    BLOCK_ATTEMPT_PENALTY,
    MAX_ACTIVE_DATA_REFS,
    MAX_HISTORY_LENGTH,
    record_action,
)
from .rules import (
    STATE_ACCUMULATED_RISK_THRESHOLD_RULE_ID,
    STATE_SECRET_THEN_EXTERNAL_NETWORK_RULE_ID,
    STATE_SECRET_THEN_MESSAGE_SEND_RULE_ID,
    AccumulatedRiskThresholdRule,
    SecretExfiltrationMessageRule,
    SecretExfiltrationNetworkRule,
)

__all__ = [
    "ALLOW_RISK_WEIGHT",
    "APPROVAL_RISK_WEIGHT",
    "BLOCK_ATTEMPT_PENALTY",
    "EXTERNAL_NETWORK_TOOLS",
    "MAX_ACTIVE_DATA_REFS",
    "MAX_HISTORY_LENGTH",
    "MESSAGE_TOOLS",
    "SECRET_ACCESS_TOOLS",
    "STATE_ACCUMULATED_RISK_THRESHOLD_RULE_ID",
    "STATE_SECRET_THEN_EXTERNAL_NETWORK_RULE_ID",
    "STATE_SECRET_THEN_MESSAGE_SEND_RULE_ID",
    "AccumulatedRiskThresholdRule",
    "IntentDriftSignal",
    "NullDriftSignal",
    "PassthroughDriftSignal",
    "SecretExfiltrationMessageRule",
    "SecretExfiltrationNetworkRule",
    "SessionStateTracker",
    "chain_tools",
    "evaluate_stateful_policy",
    "external_transfer_in_chain",
    "parse_chain_entries",
    "record_action",
    "secret_access_in_chain",
]
