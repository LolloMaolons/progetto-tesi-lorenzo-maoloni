import requests
import statistics
import json
import os
import time
from datetime import datetime

LLM_URL = "http://localhost:5000/llm-invoke"
ITERATIONS = 10
OUTPUT_FILE = "test-8-mcp-llm-orchestration.json"
PROMPTS = [
    "Applica sconto 15% a prodotti con stock < 20",
    "Sconto del 10 percento su articoli con poche scorte",
    "Riduci prezzo del 20% per prodotti low stock",
    "Applica sconto 5% a tutti i prodotti",
    "Sconto 25% su prodotti in esaurimento",
    "Riduci prezzo del 30% per articoli con stock basso",
    "Applica sconto 12% a prodotti con stock < 10",
    "Sconto 8% su prodotti con scorte limitate",
    "Riduci prezzo del 18% per prodotti in esaurimento",
    "Applica sconto 20% a tutti i prodotti con stock < 15"
]

def check_services():
    try:
        r = requests.get("http://localhost:5000/health", timeout=3)
        if r.status_code != 200:
            print("[ERRORE] mcp-host non disponibile")
            return False
        return True
    except Exception as e:
        print(f"[ERRORE] Servizi non disponibili: {e}")
        return False

def is_valid_jsonrpc(resp):
    try:
        if "jsonrpc" in resp or "result" in resp:
            return True
    except Exception:
        pass
    return False

def execute_test():
    latencies = []
    successes = 0
    failures = 0
    timeouts = 0
    for i in range(ITERATIONS):
        prompt = PROMPTS[i % len(PROMPTS)]
        payload = {"prompt": prompt}
        start = time.time()
        try:
            r = requests.post(LLM_URL, json=payload, timeout=90)
            latency = (time.time() - start) * 1000
            if r.status_code == 200:
                try:
                    data = r.json()
                    if is_valid_jsonrpc(data):
                        latencies.append(latency)
                        successes += 1
                    else:
                        failures += 1
                except Exception:
                    failures += 1
            elif r.status_code == 429:
                print("Rate limited, attesa 60s...")
                time.sleep(60)
                continue
            else:
                failures += 1
        except requests.Timeout:
            timeouts += 1
            failures += 1
        except Exception:
            failures += 1
    return latencies, successes, failures, timeouts

def calculate_stats(latencies):
    if not latencies:
        return {"count": 0, "p50": 0, "mean": 0, "min": 0, "max": 0}
    sorted_lat = sorted(latencies)
    return {
        "count": len(latencies),
        "p50": statistics.median(latencies),
        "mean": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies)
    }

def main():
    print("=" * 70)
    print("TEST 8: MCP+LLM Orchestrazione", flush=True)
    print("=" * 70)
    if not check_services():
        print("Servizi non disponibili. Esci.")
        return
    latencies, successes, failures, timeouts = execute_test()
    stats = calculate_stats(latencies)
    accuracy = round(successes / ITERATIONS * 100, 1) if ITERATIONS else 0
    results = {
        "test": "MCP+LLM Orchestrazione",
        "data": datetime.now().isoformat(),
        "iterations": ITERATIONS,
        "results": stats,
        "accuracy": accuracy,
        "timeouts": timeouts,
        "successes": successes,
        "failures": failures
    }
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'risultati-misurazioni')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nRisultati salvati: {output_path}")

if __name__ == "__main__":
    main()
