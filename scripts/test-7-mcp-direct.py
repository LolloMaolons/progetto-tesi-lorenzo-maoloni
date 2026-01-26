import requests
import statistics
import json
import os
import time
from datetime import datetime

MCP_URL = "http://localhost:5000/mcp/apply-discount"
ITERATIONS = 50
OUTPUT_FILE = "test-7-mcp-direct.json"


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

def execute_test():
    latencies = []
    successes = 0
    failures = 0
    for i in range(ITERATIONS):
        product_id = (i % 20) + 1
        payload = {"product_id": product_id, "percent": 15}
        start = time.time()
        try:
            r = requests.post(MCP_URL, json=payload, timeout=5)
            latency = (time.time() - start) * 1000
            if r.status_code == 200:
                try:
                    r.json()
                    latencies.append(latency)
                    successes += 1
                except Exception:
                    failures += 1
            elif r.status_code == 429:
                print("Rate limited, attesa 60s...")
                time.sleep(60)
                continue
            else:
                failures += 1
        except Exception:
            failures += 1
    return latencies, successes, failures

def calculate_stats(latencies):
    if not latencies:
        return {"count": 0, "p50": 0, "p95": 0, "p99": 0, "mean": 0, "min": 0, "max": 0}
    sorted_lat = sorted(latencies)
    return {
        "count": len(latencies),
        "p50": statistics.median(latencies),
        "p95": sorted_lat[int(0.95 * len(latencies))-1],
        "p99": sorted_lat[int(0.99 * len(latencies))-1],
        "mean": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies)
    }

def main():
    print("=" * 70)
    print("TEST 7: MCP Diretto", flush=True)
    print("=" * 70)
    if not check_services():
        print("Servizi non disponibili. Esci.")
        return
    latencies, successes, failures = execute_test()
    stats = calculate_stats(latencies)
    throughput = round(successes / (sum(latencies)/1000) if latencies else 0, 2)
    results = {
        "test": "MCP Diretto",
        "data": datetime.now().isoformat(),
        "iterations": ITERATIONS,
        "results": stats,
        "throughput": throughput,
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
