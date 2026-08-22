"""Red-team classification tests: disguised secrets and destination substitution."""

from intentfence_classification import (
    classify_destination,
    classify_resource,
    normalize_path,
)
from intentfence_contracts import DestinationClass, ResourceClass
from policy_testkit import WORKSPACE_CONFIG, make_context, make_contract, make_request

_ALLOWED = ["hotel-a.example", "hotel-b.example"]


def _destination_class(url: str) -> DestinationClass:
    return classify_destination(
        url,
        allowed_destinations=_ALLOWED,
        blocked_destinations=WORKSPACE_CONFIG.blocked_destinations,
        trusted_destinations=WORKSPACE_CONFIG.trusted_destinations,
        known_external_domains=WORKSPACE_CONFIG.known_external_domains,
    )


def test_disguised_secret_filenames_are_still_detected():
    disguised = [
        ".env.backup",
        "report.pdf.env",
        "config/credentials.json.bak",
        "Api_Key.TXT",
        "  api_key  ",
        "backups/id_rsa.old",
        "oauth_token_store.yaml",
        "team-passwords.md",
        "db.dump.pgpass",
    ]
    for path in disguised:
        resource_class = classify_resource(path, WORKSPACE_CONFIG)
        assert resource_class in {
            ResourceClass.SECRET,
            ResourceClass.CREDENTIAL,
        }, f"{path} classified as {resource_class}"


def test_unicode_disguised_secret_filename_is_detected():
    fullwidth = classify_resource("\uff41pi_key.txt", WORKSPACE_CONFIG)
    zero_width = classify_resource("sec\u200bret_key.txt", WORKSPACE_CONFIG)
    assert fullwidth is ResourceClass.SECRET
    assert zero_width is ResourceClass.SECRET


def test_percent_encoded_traversal_is_unmasked_as_system_path():
    canonical = normalize_path("/%2e%2e/etc/hosts")
    assert canonical == "/etc/hosts"
    assert (
        classify_resource("/%2e%2e/etc/hosts", WORKSPACE_CONFIG) is ResourceClass.SYSTEM_FILE
    )
    assert not normalize_path("/workspace/%2e%2e/secrets").startswith("/workspace/")


def test_userinfo_destination_substitution_does_not_spoof_allow_list():
    assert _destination_class("https://hotel-a.example@attacker.example/exfil") is (
        DestinationClass.UNKNOWN_EXTERNAL
    )


def test_subdomain_spoofing_does_not_inherit_approved_domain():
    assert _destination_class("https://hotel-a.example.attacker.example/") is (
        DestinationClass.UNKNOWN_EXTERNAL
    )


def test_case_and_port_games_do_not_bypass_allow_list():
    assert _destination_class("HTTPS://HOTEL-A.EXAMPLE/rooms") is (
        DestinationClass.USER_APPROVED
    )
    assert _destination_class("https://attacker.example:8443/collect") is (
        DestinationClass.UNKNOWN_EXTERNAL
    )


def test_decoy_destination_argument_cannot_mask_real_url_host():
    from intentfence_policy import PolicyInput
    from intentfence_policy.models import EvaluationContext

    request = make_request(
        tool="http_request",
        arguments={
            "destination": "hotel-a.example",
            "url": "https://attacker.example/collect",
        },
    )
    context = EvaluationContext.build(
        PolicyInput(
            request=request,
            contract=make_contract(),
            context=make_context(),
        ),
        WORKSPACE_CONFIG,
    )
    assert "attacker.example" in (context.destination or "")
    assert context.destination_class in {
        DestinationClass.UNKNOWN_EXTERNAL,
        DestinationClass.KNOWN_EXTERNAL,
        DestinationClass.BLOCKED,
    }
