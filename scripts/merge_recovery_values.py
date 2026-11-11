"""Merge private Helm values, removing null keys before Helm default coalescing."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any


def merge_values(baseline: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Preserve baseline values except explicit overrides; null removes a key."""
    result = deepcopy(baseline)
    for key, value in overlay.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict):
            previous = result.get(key)
            result[key] = merge_values(previous if isinstance(previous, dict) else {}, value)
        else:
            result[key] = deepcopy(value)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    overlay = json.loads(args.overlay.read_text())
    if not isinstance(baseline, dict) or not isinstance(overlay, dict):
        parser.error("Values inputs must be JSON objects")
    merged = merge_values(baseline, overlay)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(merged, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
