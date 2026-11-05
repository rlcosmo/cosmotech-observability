"""The AWS publisher must never export account credentials or invent a token balance."""
import importlib.util
from pathlib import Path
import pytest
spec = importlib.util.spec_from_file_location('quota', Path(__file__).parents[1]/'scripts/publish_codex_usage.py')
quota = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quota)


def test_quota_is_restricted_to_percentages_and_reset_metadata():
    result = quota.sanitize({'account': {'token': 'must-not-leave-host'}, 'rateLimits': {
        'planType': 'private', 'primary': {'usedPercent': 20, 'resetsAt': 1234567, 'windowDurationMins': 300,
                                         'credential': 'secret'}}})
    assert result['token_balance_available'] is False
    assert result['buckets'] == {'codex': {'primary': {'usedPercent': 20, 'resetsAt': 1234567, 'windowDurationMins': 300}}}
    assert 'secret' not in str(result) and 'must-not-leave-host' not in str(result)


def test_invalid_percentage_fails_instead_of_showing_available_quota():
    with pytest.raises(ValueError):
        quota.sanitize({'rateLimits': {'primary': {'usedPercent': 101, 'resetsAt': 1, 'windowDurationMins': 300}}})
