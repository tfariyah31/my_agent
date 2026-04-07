import json
import os
from datetime import datetime

LOG_FILE = "logs/decisions.json"

def init_logger():
    os.makedirs("logs", exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)

def log_decision(user_input: str, iteration: int, action: str, detail: str, result: str = ""):
    init_logger()
    with open(LOG_FILE, "r") as f:
        logs = json.load(f)

    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_input": user_input,
        "iteration": iteration,
        "action": action,       # "think", "search", "answer"
        "detail": detail,       # what the LLM said or searched
        "result": result        # tool result if any
    })

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)