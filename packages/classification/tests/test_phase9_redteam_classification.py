from intentfence_classification import classify_resource
from intentfence_contracts import ResourceClass


def test_percent_encoded_env_is_classified_secret():
    assert classify_resource("%2Eenv") is ResourceClass.SECRET


def test_zero_width_api_key_is_classified_secret():
    assert classify_resource("workspace/api\u200b_key.txt") is ResourceClass.SECRET


def test_fullwidth_api_key_is_classified_secret():
    assert classify_resource("workspace/ａｐｉ_key.txt") is ResourceClass.SECRET


def test_percent_encoded_traversal_to_env_is_classified_secret():
    assert classify_resource("workspace/%2e%2e/%2eenv") is ResourceClass.SECRET
