import requests
import statistics
import json
import os
import time
from datetime import datetime

REST_URL = "http://localhost:8080/products"
GRAPHQL_URL = "http://localhost:4000/"
ITERATIONS = 40

HEADERS = {"Content-Type": "application/json"}

OUTPUT_FILE = "test-1-rest-vs-graphql-simple.json"


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

def validate_graphql(data):
    if "errors" in data:
        print(f"[GraphQL] Errore: {data['errors']}")
        return False
    if "data" not in data or not data["data"]:
        print(f"[GraphQL] Nessun dato: {data}")
        return False
    return True

def execute_rest():
    latencies = []
    successes = 0
    failures = 0
    for i in range(ITERATIONS):
        start = time.time()
        try:
            r = requests.get(REST_URL, timeout=5)
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

def execute_graphql(query):
    latencies = []
    successes = 0
    failures = 0
    for i in range(ITERATIONS):
        start = time.time()
        try:
            r = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": query}, timeout=5)
            latency = (time.time() - start) * 1000
            if r.status_code == 200:
                data = r.json()
                if not validate_graphql(data):
                    print(f"[GraphQL][B][{i+1}/{ITERATIONS}] Risposta: {data}")
                    failures += 1
                else:
                    latencies.append(latency)
                    successes += 1
            elif r.status_code == 429:
                print("Rate limited, attesa 60s...")
                time.sleep(60)
                continue
            else:
                print(f"[GraphQL][B][{i+1}/{ITERATIONS}] Status: {r.status_code}, Body: {r.text}")
                failures += 1
        except Exception as e:
            print(f"[GraphQL][B][{i+1}/{ITERATIONS}] Exception: {e}")
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

def save_results(data, filename):
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'risultati-misurazioni')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    return output_path

def main():
    print("=" * 70)
    print("TEST 1: REST vs GraphQL - Query Semplici", flush=True)
    print("=" * 70)
    if not check_services():
        print("Servizi non disponibili. Esci.")
        return
    reset_catalog()
    time.sleep(2)
    print("[REST] Avvio test...", flush=True)
    rest_lat, rest_succ, rest_fail = execute_rest()
    rest_stats = calculate_stats(rest_lat)
    print("[GraphQL] Query A (tutti campi)...", flush=True)
    query_a = """{ products { id name price stock category description } }"""
    gqlA_lat, gqlA_succ, gqlA_fail = execute_graphql(query_a)
    gqlA_stats = calculate_stats(gqlA_lat)
    print("[GraphQL] Query B (3 campi)...", flush=True)
    query_b = """{ products { id name price } }"""
    gqlB_lat, gqlB_succ, gqlB_fail = execute_graphql(query_b)
    gqlB_stats = calculate_stats(gqlB_lat)
    overhead = round(gqlA_stats["p50"] / rest_stats["p50"], 2) if rest_stats["p50"] else 0
    results = {
        "test": "REST vs GraphQL - Query Semplici",
        "data": datetime.now().isoformat(),
        "iterations": ITERATIONS,
        "configuration": {
            "rest_url": REST_URL,
            "graphql_url": GRAPHQL_URL,
            "rate_limit": "100/minute"
        },
        "results": {
            "rest": rest_stats,
            "graphql_A": gqlA_stats,
            "graphql_B": gqlB_stats
        },
        "comparison": {
            "overhead": overhead,
            "winner": "REST" if rest_stats["p50"] < gqlA_stats["p50"] else "GraphQL",
            "conclusion": "REST più veloce su query atomiche" if rest_stats["p50"] < gqlA_stats["p50"] else "GraphQL più veloce"
        },
        "successes": {"rest": rest_succ, "graphql_A": gqlA_succ, "graphql_B": gqlB_succ},
        "failures": {"rest": rest_fail, "graphql_A": gqlA_fail, "graphql_B": gqlB_fail}
    }
    output_file = save_results(results, OUTPUT_FILE)
    print(f"\nRisultati salvati: {output_file}")

if __name__ == "__main__":
    main()
