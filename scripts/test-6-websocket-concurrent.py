import asyncio
import websockets
import statistics
import json
import os
import time
from datetime import datetime

WS_URL = "ws://localhost:7070"
CLIENTS = 50
OUTPUT_FILE = "test-6-websocket-concurrent.json"

async def connect_client(idx, results):
    t1 = time.time()
    try:
        async with websockets.connect(WS_URL) as ws:
            t2 = time.time()
            welcome = await ws.recv()
            t3 = time.time()
            results.append({"idx": idx, "connect": (t2-t1)*1000, "welcome": (t3-t2)*1000, "success": True})
    except Exception as e:
        results.append({"idx": idx, "connect": None, "welcome": None, "success": False, "error": str(e)})

async def main_async():
    results = []
    tasks = [connect_client(i, results) for i in range(CLIENTS)]
    await asyncio.gather(*tasks)
    return results

def calculate_stats(results):
    connects = [r["connect"] for r in results if r["success"] and r["connect"] is not None]
    welcomes = [r["welcome"] for r in results if r["success"] and r["welcome"] is not None]
    return {
        "success": sum(1 for r in results if r["success"]),
        "fail": sum(1 for r in results if not r["success"]),
        "connect_p50": statistics.median(connects) if connects else 0,
        "connect_p95": statistics.quantiles(connects, n=100)[94] if len(connects) >= 20 else 0,
        "welcome_p50": statistics.median(welcomes) if welcomes else 0
    }

def main():
    print("=" * 70)
    print("TEST 6: WebSocket Concorrenza Client", flush=True)
    print("=" * 70)
    results = asyncio.run(main_async())
    stats = calculate_stats(results)
    output = {
        "test": "WebSocket Concorrenza Client",
        "data": datetime.now().isoformat(),
        "clients": CLIENTS,
        "results": stats,
        "details": results
    }
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'risultati-misurazioni')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nRisultati salvati: {output_path}")

if __name__ == "__main__":
    main()
