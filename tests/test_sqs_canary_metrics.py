import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

spec = importlib.util.spec_from_file_location("queue_metrics", Path(__file__).parents[1] / "src/sqs_canary_metrics.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_queue_snapshot_is_readonly_and_fresh():
    now = datetime(2026, 11, 5, tzinfo=UTC)
    calls = []
    def call(**kwargs):
        calls.append(kwargs)
        return {"Datapoints": [{"Timestamp": now - timedelta(seconds=60), "Maximum": 0}]}
    text = module.collect(call, "source", "dlq", now)
    assert "cosmotech_sqs_collection_success 1" in text
    assert "cosmotech_sqs_oldest_age_seconds 0" in text
    assert len(calls) == 8 and all(c["Namespace"] == "AWS/SQS" for c in calls)


def test_missing_and_stale_queue_data_not_fabricated_as_zero():
    now = datetime(2026, 11, 5, tzinfo=UTC)
    for result in [{}, {"Datapoints": [{"Timestamp": now - timedelta(minutes=10), "Maximum": 0}]}]:
        text = module.collect(lambda result=result, **_: result, "source", "dlq", now)
        assert text == "cosmotech_sqs_collection_success 0\n"


def test_inflight_throughput_and_sparse_counters():
    now = datetime(2026, 11, 5, tzinfo=UTC)
    def call(**query):
        if query["Statistics"] == ["Sum"]:
            return {"Datapoints": [{"Timestamp": now - timedelta(seconds=60), "Sum": 120}]}
        return {"Datapoints": [{"Timestamp": now - timedelta(seconds=60), "Maximum": 7}]}
    text = module.collect(call, "source", "dlq", now)
    assert "cosmotech_sqs_inflight 7" in text
    assert "cosmotech_sqs_sent_per_second 2.0" in text
    def sparse(**query):
        return {} if query["Statistics"] == ["Sum"] else call(**query)
    text = module.collect(sparse, "source", "dlq", now)
    assert "cosmotech_sqs_collection_success 1" in text
    assert 'cosmotech_sqs_counter_available{metric="sent"} 0' in text
    assert "cosmotech_sqs_sent_per_second" not in text


def test_invalid_samples_and_permission_failure_are_not_zero():
    now = datetime(2026, 11, 5, tzinfo=UTC)
    for value in [-1, float("nan"), float("inf"), True]:
        text = module.collect(lambda **_: {"Datapoints": [{"Timestamp": now, "Maximum": value}]}, "q", "dlq", now)
        assert text == "cosmotech_sqs_collection_success 0\n"
    def denied(**query):
        raise RuntimeError("Denied")
    assert module.collect(denied, "q", "dlq", now) == "cosmotech_sqs_collection_success 0\n"


def test_idle_dlq_uses_actual_metadata_instead_of_inventing_zero():
    now = datetime(2026, 11, 7, tzinfo=UTC)
    def call(**query):
        if query["Dimensions"][0]["Value"] == "dlq":
            return {}
        statistic = query["Statistics"][0]
        return {"Datapoints": [{"Timestamp": now, statistic: 0}]}
    for count in ("0", "3"):
        text = module.collect(call, "q", "dlq", now,
                              queue_attributes=lambda name: {"Attributes": {"ApproximateNumberOfMessages": count}})
        assert f"cosmotech_sqs_dlq_visible {count}" in text
        assert "cosmotech_sqs_dlq_attribute_fallback 1" in text
    assert module.collect(call, "q", "dlq", now) == "cosmotech_sqs_collection_success 0\n"
    def denied(name):
        raise RuntimeError("Denied")
    assert module.collect(call, "q", "dlq", now, queue_attributes=denied) == "cosmotech_sqs_collection_success 0\n"
    for count in ("-1", "not-a-count", True):
        assert module.collect(call, "q", "dlq", now,
                              queue_attributes=lambda name: {"Attributes": {"ApproximateNumberOfMessages": count}}) == "cosmotech_sqs_collection_success 0\n"
