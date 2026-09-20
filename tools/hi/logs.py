"""Bounded component diagnostics that never emit raw household log messages."""
import json
import re
import subprocess

EXCEPTIONS = {"ImportError", "ModuleNotFoundError", "ValueError", "TypeError", "KeyError", "RuntimeError", "OperationalError", "TimeoutError"}


def summarize(raw):
    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0, "OTHER": 0}
    exceptions = set()
    matched = 0
    for line in raw.splitlines()[-200:]:
        if not re.search(r"\[custom_components\.ai_automation_suggester(?:\.[a-z_]+)*\]", line):
            continue
        matched += 1
        level = next((level for level in ("ERROR", "WARNING", "INFO") if re.search(rf"\b{level}\b", line)), "OTHER")
        counts[level] += 1
        exceptions.update(kind for kind in EXCEPTIONS if re.search(rf"\b{kind}\b", line))
    return {"scanned_line_limit": 200, "component_lines": matched, "levels": counts,
            "exception_types": sorted(exceptions), "raw_messages_omitted": True,
            "limitation": "A bounded summary cannot prove the absence of errors or integration readiness."}


def main():
    try:
        result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                                 "-o", "ForwardAgent=no", "homeassistant-ai", "ha core logs --lines 200"],
                                capture_output=True, text=True, timeout=30, check=False)
        if result.returncode:
            print(json.dumps({"error": "Bounded log retrieval failed", "exit_code": result.returncode}))
            return 1
        print(json.dumps(summarize(result.stdout)))
        return 0
    except (OSError, subprocess.TimeoutExpired):
        print(json.dumps({"error": "Bounded log retrieval unavailable"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
