"""Read CloudWatch SQS gauges through an injectable API; never touch messages."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime, timedelta


def collect(call: Callable[..., dict], queue_name: str, dlq_name: str, now: datetime) -> str:
    """Missing/stale points emit success=0 and omit gauges instead of inventing zero."""
    names = [
        ("cosmotech_sqs_visible", queue_name, "ApproximateNumberOfMessagesVisible"),
        ("cosmotech_sqs_oldest_age_seconds", queue_name, "ApproximateAgeOfOldestMessage"),
        ("cosmotech_sqs_dlq_visible", dlq_name, "ApproximateNumberOfMessagesVisible"),
    ]
    values, timestamps = {}, []
    try:
        for output, queue, metric in names:
            response = call(Namespace="AWS/SQS", MetricName=metric,
                            Dimensions=[{"Name": "QueueName", "Value": queue}],
                            StartTime=now - timedelta(minutes=10), EndTime=now,
                            Period=60, Statistics=["Maximum"])
            points = response.get("Datapoints", [])
            if not points:
                raise ValueError("No queue data")
            point = max(points, key=lambda p: p["Timestamp"])
            stamp = point["Timestamp"]
            if isinstance(stamp, str):
                stamp = datetime.fromisoformat(stamp)
            value = point["Maximum"]
            if (not 0 <= (now - stamp).total_seconds() <= 180
                    or type(value) not in {int, float} or not math.isfinite(value) or value < 0):
                raise ValueError("Invalid queue data")
            timestamps.append(stamp.timestamp())
            values[output] = value
    except (KeyError, ValueError, TypeError, OSError):
        return "cosmotech_sqs_collection_success 0\n"
    lines = ["cosmotech_sqs_collection_success 1",
             f"cosmotech_sqs_data_timestamp_seconds {min(timestamps)}"]
    lines += [f"{name} {value}" for name, value in values.items()]
    return "\n".join(lines) + "\n"
