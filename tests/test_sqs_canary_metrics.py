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
    assert len(calls) == 3 and all(c["Namespace"] == "AWS/SQS" for c in calls)


def test_missing_and_stale_queue_data_not_fabricated_as_zero():
    now = datetime(2026, 11, 5, tzinfo=UTC)
    for result in [{}, {"Datapoints": [{"Timestamp": now - timedelta(minutes=10), "Maximum": 0}]}]:
        text = module.collect(lambda result=result, **_: result, "source", "dlq", now)
        assert text == "cosmotech_sqs_collection_success 0\n"
