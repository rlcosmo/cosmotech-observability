"""Regression coverage for stale node selectors and private baseline preservation."""
from scripts.merge_recovery_values import merge_values


def test_remove_existing_hostname_without_losing_zone_or_private_values():
    baseline = {"nodeSelector": {"kubernetes.io/hostname": "retired"}, "private": "fixture"}
    overlay = {"nodeSelector": {"kubernetes.io/hostname": None, "zone": "us-east-1b"}}
    assert merge_values(baseline, overlay) == {"nodeSelector": {"zone": "us-east-1b"}, "private": "fixture"}
    assert baseline["nodeSelector"]["kubernetes.io/hostname"] == "retired"


def test_remove_nulls_from_new_nested_maps():
    assert merge_values({}, {"new": {"retired": None, "active": "yes"}}) == {"new": {"active": "yes"}}


def test_replace_claim_mounts_without_retaining_old_claim_template():
    baseline = {"storage": {"volumeClaimTemplate": {"old": True}}, "volumes": [{"claim": "old"}]}
    overlay = {"storage": {"volumeClaimTemplate": None, "emptyDir": {}}, "volumes": [{"claim": "restored"}]}
    assert merge_values(baseline, overlay) == {"storage": {"emptyDir": {}}, "volumes": [{"claim": "restored"}]}
