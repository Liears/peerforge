#!/usr/bin/env python3
import json
import sys


def main() -> int:
    name = sys.argv[1]
    prompt = sys.argv[2]
    if name == "alpha":
        payload = {
            "status": "continue",
            "summary": "I want beta to verify the split.",
            "messages": [
                {
                    "to": ["beta"],
                    "kind": "question",
                    "body": "Please validate whether adapter work should be separated from routing work."
                }
            ]
        }
    else:
        done = "alpha -> beta" in prompt or "question:" in prompt
        payload = {
            "status": "done" if done else "continue",
            "summary": "I verified the split and support separate responsibilities.",
            "messages": [
                {
                    "to": ["alpha"],
                    "kind": "reply",
                    "body": "Validated. Adapter and routing can proceed independently."
                }
            ]
        }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
