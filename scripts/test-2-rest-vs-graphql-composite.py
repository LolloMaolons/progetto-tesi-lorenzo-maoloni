import requests
import statistics
import json
import os
import time
from datetime import datetime

REST_URL = "http://localhost:8080/products/"
REST_REC_URL = "http://localhost:8080/products/{}/recommendations"
GRAPHQL_URL = "http://localhost:4000/"
ITERATIONS = 40

HEADERS = {"Content-Type": "application/json"}
OUTPUT_FILE = "test-2-rest-vs-graphql-composite.json"


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
    return "errors" not in data

def execute_rest():
    latencies = []
    successes = 0
    failures = 0
    for i in range(ITERATIONS):
        # Seleziona 5 product_id distinti per questa iterazione
        product_ids = [((i * 5 + j) % 20) + 1 for j in range(5)]
        iter_latency = 0
        iter_success = True
        for product_id in product_ids:
            try:
                start = time.time()
                r1 = requests.get(REST_URL + str(product_id), timeout=5)
                t1 = (time.time() - start) * 1000
                if r1.status_code == 429:
                    print("Rate limited, attesa 60s...")
                    time.sleep(60)
                    iter_success = False
                    break
                if r1.status_code != 200:
                    failures += 1
                    iter_success = False
                    break
                start2 = time.time()
                r2 = requests.get(REST_REC_URL.format(product_id), timeout=5)
                t2 = (time.time() - start2) * 1000
                if r2.status_code == 429:
                    print("Rate limited, attesa 60s...")
                    time.sleep(60)
                    iter_success = False
                    break
                if r2.status_code != 200:
                    failures += 1
                    iter_success = False
                    break
                iter_latency += t1 + t2
            except Exception:
                failures += 1
                iter_success = False
                break
        if iter_success:
            latencies.append(iter_latency)
            successes += 1
    return latencies, successes, failures

def execute_graphql():
    latencies = []
    successes = 0
    failures = 0
    for i in range(ITERATIONS):
        # Seleziona 5 product_id distinti per questa iterazione
        product_ids = [((i * 5 + j) % 20) + 1 for j in range(5)]
        # Costruisci la query GraphQL per più prodotti
        products_query = "\n".join([
            f"p{pid}: product(id: {pid}) {{ id name price stock recommendations(limit: 3) {{ id name price }} }}"
            for pid in product_ids
        ])
        query = f"""
        {{
        {products_query}
        }}
        """
        start = time.time()
        try:
            r = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": query}, timeout=5)
            latency = (time.time() - start) * 1000
            if r.status_code == 200:
                data = r.json()
                if validate_graphql(data):
                    latencies.append(latency)
                    successes += 1
                else:
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

def save_results(data, filename):
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'risultati-misurazioni')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    return output_path

def main():
    print("=" * 70)
    print("TEST 2: REST vs GraphQL - Query Composte", flush=True)
    print("=" * 70)
    if not check_services():
        print("Servizi non disponibili. Esci.")
        return
    reset_catalog()
    time.sleep(2)
    print("[REST] Avvio test...", flush=True)
    rest_lat, rest_succ, rest_fail = execute_rest()
    rest_stats = calculate_stats(rest_lat)
    print("[GraphQL] Avvio test...", flush=True)
    gql_lat, gql_succ, gql_fail = execute_graphql()
    gql_stats = calculate_stats(gql_lat)
    speedup = round((rest_stats["p50"] - gql_stats["p50"]) / rest_stats["p50"] * 100, 1) if rest_stats["p50"] else 0
    results = {
        "test": "REST vs GraphQL - Query Composte",
        "data": datetime.now().isoformat(),
        "iterations": ITERATIONS,
        "configuration": {
            "rest_url": REST_URL,
            "graphql_url": GRAPHQL_URL,
            "rate_limit": "100/minute"
        },
        "results": {
            "rest": rest_stats,
            "graphql": gql_stats
        },
        "comparison": {
            "speedup": speedup,
            "winner": "GraphQL" if speedup > 0 else "REST",
            "conclusion": "GraphQL riduce round-trip su query composte" if speedup > 0 else "REST più veloce"
        },
        "successes": {"rest": rest_succ, "graphql": gql_succ},
        "failures": {"rest": rest_fail, "graphql": gql_fail}
    }
    output_file = save_results(results, OUTPUT_FILE)
    print(f"\nRisultati salvati: {output_file}")

if __name__ == "__main__":
    main()
