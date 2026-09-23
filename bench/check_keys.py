#!/usr/bin/env python3
"""check_keys.py — confirm API keys work and model IDs in models.json exist."""
import os, json, requests

cfg = json.load(open("models.json"))

print("--- keys in this shell ---")
for env in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
    v = os.environ.get(env)
    print(f"{env:20} {'set (' + v[:8] + '...)' if v else 'MISSING  <- run: export ' + env + '=...'}")

print("\n--- one tiny request per model ---")
for m in cfg["models"]:
    b, mid = m["backend"], m["model"]
    try:
        if b == "openai":
            r = requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                json={"model": mid, "max_completion_tokens": 5,
                      "messages": [{"role": "user", "content": "hi"}]}, timeout=30)
        elif b == "anthropic":
            r = requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                json={"model": mid, "max_tokens": 5,
                      "messages": [{"role": "user", "content": "hi"}]}, timeout=30)
        elif b == "gemini":
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{mid}:generateContent",
                params={"key": os.environ["GEMINI_API_KEY"]},
                json={"contents": [{"parts": [{"text": "hi"}]}],
                      "generationConfig": {"maxOutputTokens": 5}}, timeout=30)
        else:
            r = requests.post("http://localhost:11434/api/chat",
                json={"model": mid, "stream": False,
                      "messages": [{"role": "user", "content": "hi"}]}, timeout=120)
        if r.status_code == 200:
            msg = "OK"
        elif r.status_code == 401:
            msg = "HTTP 401 -> key is wrong or revoked"
        elif r.status_code == 404:
            msg = "HTTP 404 -> model ID not found; fix it in models.json"
        elif r.status_code == 429:
            msg = "HTTP 429 -> rate limit or no credit"
        else:
            msg = f"HTTP {r.status_code}: {r.text[:150]}"
    except KeyError as e:
        msg = f"env var {e} not set"
    except requests.exceptions.ConnectionError:
        msg = "cannot connect" + (" -> is Ollama running? (ollama serve)" if b == "ollama" else "")
    except Exception as e:
        msg = f"ERROR {str(e)[:120]}"
    print(f"{m['name']:14} {b:10} {mid:26} {msg}")
