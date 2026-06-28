import json
import os
import re
from typing import Any

CONFIG_FILE: str = "threshold_config.json"

INCREASE_KEYWORDS: list[str] = ["提高", "调高", "调大", "增加", "加大", "升"]
DECREASE_KEYWORDS: list[str] = ["降低", "调低", "调小", "减少", "减小", "降"]
DELTA_MIN: float = 0.1
DELTA_MAX: float = 1.0
DELTA_DEFAULT: float = 0.5


def load_config() -> dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        return {"sensitivity_multiplier": 1.0}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def _extract_delta(text: str) -> float | None:
    matches = re.findall(r"(\d+\.?\d*)", text)
    if matches:
        val = float(matches[0])
        return max(DELTA_MIN, min(DELTA_MAX, val))
    return None


if __name__ == "__main__":
    body: str = os.environ.get("BODY", "")

    action: str = ""
    delta: float = 0.0

    for kw in DECREASE_KEYWORDS:
        if kw in body:
            action = "降低敏感度"
            delta = _extract_delta(body) or DELTA_DEFAULT
            delta = max(DELTA_MIN, delta)
            break

    if not action:
        for kw in INCREASE_KEYWORDS:
            if kw in body:
                action = "提高敏感度"
                delta = _extract_delta(body) or DELTA_DEFAULT
                delta = max(DELTA_MIN, delta)
                break

    if not action:
        print("未识别到关键词，跳过")
        exit(0)

    config: dict[str, Any] = load_config()
    current: float = config["sensitivity_multiplier"]
    adjustment: float = -delta if action == "降低敏感度" else delta
    config["sensitivity_multiplier"] = round(
        max(0.5, min(3.0, current + adjustment)), 1
    )

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    new_val: float = config["sensitivity_multiplier"]
    gh_out: str | None = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write("action<<EOF\n")
            f.write(f"{action}\n")
            f.write("EOF\n")
            f.write(f"changed=true\n")
            f.write(f"new_multiplier={new_val}\n")

    print(f"{action} → 倍率调整为 {new_val}")
