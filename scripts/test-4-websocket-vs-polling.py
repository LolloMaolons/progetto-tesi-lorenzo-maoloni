import requests
import statistics
import json
import os
import time
from datetime import datetime
import websocket
import threading

REST_URL = "http://localhost:8080/products/1"
PATCH_URL = "http://localhost:8080/products/1"
WS_URL = "ws://localhost:7070"
ITERATIONS = 20
OUTPUT_FILE = "test-4-websocket-vs-polling.json"

HEADERS = {"Content-Type": "application/json"}


def check_services():
    try:
        r = requests.get("http://localhost:8080/health", timeout=3)
        if r.status_code != 200:
            print("[ERRORE] api-rest non disponibile")
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

def ws_test():
    latencies = []
    successes = 0
    failures = 0
    for i in range(ITERATIONS):
        try:
            ws = websocket.create_connection(
                WS_URL,
                timeout=5,
                header=["Origin: *"]
            )
        except Exception as e:
            print(f"WebSocket fallito: {e}")
            failures += 1
            continue
        t1 = time.time()
        try:
            requests.patch(PATCH_URL + "?stock=99", timeout=5)
        except Exception:
            ws.close()
            failures += 1
            continue
        try:
            ws.settimeout(2)
            msg = ws.recv()
            t2 = time.time()
            latency = (t2 - t1) * 1000
            latencies.append(latency)
            successes += 1
        except Exception:
            failures += 1
        ws.close()
    return latencies, successes, failures

def polling_test():
    latencies = []
    successes = 0
    failures = 0
    for i in range(ITERATIONS):
        stock_val = 98 if i % 2 == 0 else 99
        try:
            requests.patch(PATCH_URL + f"?stock={stock_val}", timeout=5)
            time.sleep(0.5)
            t1 = time.time()
            for attempt in range(10):
                time.sleep(1)
                r = requests.get(REST_URL, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    print(f"[Polling][{i+1}/{ITERATIONS}] Tentativo {attempt+1}: stock={data.get('stock', 0)} (atteso {stock_val})")
                    if data.get("stock", 0) == stock_val:
                        t2 = time.time()
                        latency = (t2 - t1) * 1000
                        latencies.append(latency)
                        successes += 1
                        break
            else:
                print(f"[Polling][{i+1}/{ITERATIONS}] Fallito: stock non aggiornato a {stock_val} dopo 10s")
                failures += 1
        except Exception as e:
            print(f"[Polling][{i+1}/{ITERATIONS}] Errore: {e}")
            failures += 1
    return latencies, successes, failures

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
    print("TEST 4: WebSocket vs Polling HTTP", flush=True)
    print("=" * 70)
    if not check_services():
        print("Servizi non disponibili. Esci.")
        return
    reset_catalog()
    time.sleep(2)
    r = requests.get(REST_URL, timeout=5)
    if r.status_code != 200:
        print(f"[ERRORE] Prodotto non trovato dopo reset! Status: {r.status_code}")
        return
    else:
        print(f"[INFO] Prodotto dopo reset: {r.json()}")
    print("[WebSocket] Avvio test...", flush=True)
    ws_lat, ws_succ, ws_fail = ws_test()
    ws_stats = calculate_stats(ws_lat)
    print("[WebSocket] COMPLETATO\n", flush=True)
    time.sleep(2)
    print("[Polling] Avvio test...", flush=True)
    poll_lat, poll_succ, poll_fail = polling_test()
    poll_stats = calculate_stats(poll_lat)
    print("[Polling] COMPLETATO\n", flush=True)
    ratio = round(poll_stats["p50"] / ws_stats["p50"], 1) if ws_stats["p50"] else 0
    results = {
        "test": "WebSocket vs Polling HTTP",
        "data": datetime.now().isoformat(),
        "iterations": ITERATIONS,
        "results": {
            "websocket": ws_stats,
            "polling": poll_stats
        },
        "comparison": {
            "ratio": ratio,
            "winner": "WebSocket" if ratio > 1 else "Polling",
            "conclusion": "WebSocket più veloce per notifiche real-time" if ratio > 1 else "Polling più veloce"
        },
        "successes": {"websocket": ws_succ, "polling": poll_succ},
        "failures": {"websocket": ws_fail, "polling": poll_fail}
    }

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'risultati-misurazioni')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nRisultati salvati: {output_path}")

if __name__ == "__main__":
    main()
