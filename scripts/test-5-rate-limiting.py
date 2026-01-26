import requests
import statistics
import json
import os
import time
from datetime import datetime

REST_URL = "http://localhost:8080/products"
GRAPHQL_URL = "http://localhost:4000/"
ITERATIONS = 25
HEADERS = {"Content-Type": "application/json"}
OUTPUT_FILE = "test-5-rate-limiting.json"


def check_services():
    try:
        r = requests.get("http://localhost:8080/health", timeout=3)
        if r.status_code != 200:
            print("[ERRORE] api-rest non disponibile")
            return False
        r2 = requests.post(GRAPHQL_URL, json={"query": "{ __typename }"}, timeout=3)
        if r2.status_code != 200:
            print("[ERRORE] gateway-graphql non disponibile")
            return False
        return True
    except Exception as e:
        print(f"[ERRORE] Servizi non disponibili: {e}")
        return False

def reset_catalog():
    try:
        r = requests.post("http://localhost:8080/reset", timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def execute_rest():
    latencies = []
    codes = []
    for i in range(ITERATIONS):
        start = time.time()
        try:
            r = requests.get(REST_URL, timeout=5)
            latency = (time.time() - start) * 1000
            codes.append(r.status_code)
            if r.status_code == 429:
                print("Rate limited!")
            else:
                latencies.append(latency)
        except Exception:
            codes.append(0)
        time.sleep(0.1)
    return latencies, codes

def execute_graphql():
    latencies = []
    codes = []
    query = "{ products { id } }"
    for i in range(ITERATIONS):
        start = time.time()
        try:
            r = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": query}, timeout=5)
            latency = (time.time() - start) * 1000
            code = r.status_code
            try:
                data = r.json()
                if 'errors' in data and any('Rate limit exceeded' in e.get('message', '') for e in data['errors']):
                    code = 429
            except Exception:
                pass
            codes.append(code)
            if code == 429:
                print("Rate limited!")
            else:
                latencies.append(latency)
        except Exception:
            codes.append(0)
        time.sleep(0.1)
    return latencies, codes

def analyze_codes(codes, limit):
    from collections import Counter
    c = Counter(codes)
    accepted = c.get(200, 0)
    rejected = c.get(429, 0)
    efficacy = round(rejected / (len(codes) - limit) * 100, 1) if (len(codes) - limit) > 0 else 0
    return {"200": accepted, "429": rejected, "efficacy": efficacy}

def calculate_stats(latencies):
    if not latencies:
        return {"count": 0, "mean": 0, "min": 0, "max": 0}
    return {
        "count": len(latencies),
        "mean": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies)
    }

def main():
    print("=" * 70)
    print("TEST 5: Rate Limiting", flush=True)
    print("=" * 70)
    if not check_services():
        print("Servizi non disponibili. Esci.")
        return
    reset_catalog()
    time.sleep(2)
    print("[REST] Avvio test...", flush=True)
    rest_lat, rest_codes = execute_rest()
    rest_stats = calculate_stats(rest_lat)
    rest_code_stats = analyze_codes(rest_codes, 10)
    print("[GraphQL] Avvio test...", flush=True)
    gql_lat, gql_codes = execute_graphql()
    gql_stats = calculate_stats(gql_lat)
    gql_code_stats = analyze_codes(gql_codes, 10)
    results = {
        "test": "Rate Limiting",
        "data": datetime.now().isoformat(),
        "iterations": ITERATIONS,
        "configuration": {
            "rest_url": REST_URL,
            "graphql_url": GRAPHQL_URL,
            "rate_limit": "10/minute"
        },
        "results": {
            "rest": {"latency": rest_stats, "codes": rest_code_stats},
            "graphql": {"latency": gql_stats, "codes": gql_code_stats}
        }
    }
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'risultati-misurazioni')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nRisultati salvati: {output_path}")

if __name__ == "__main__":
    main()
