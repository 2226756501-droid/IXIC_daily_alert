import json, os

CONFIG_FILE = "threshold_config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"sensitivity_multiplier": 1.0}
    with open(CONFIG_FILE) as f:
        return json.load(f)


if __name__ == "__main__":
    body = os.environ.get("BODY", "")

    if "降低" in body:
        action = "降低敏感度"
        delta = 0.5
    elif "提高" in body:
        action = "提高敏感度"
        delta = -0.5
    else:
        print("未识别到关键词，跳过")
        exit(0)

    config = load_config()
    config["sensitivity_multiplier"] = round(
        max(0.5, min(3.0, config["sensitivity_multiplier"] + delta)), 1
    )

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    new_val = config["sensitivity_multiplier"]
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"action={action}\n")
            f.write(f"changed=true\n")
            f.write(f"new_multiplier={new_val}\n")

    print(f"{action} → 倍率调整为 {new_val}")
