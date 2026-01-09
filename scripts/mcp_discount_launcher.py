import os
import sys
import time
import requests
import json

MCP_HOST = os.environ['MCP_HOST']
MCP_BEARER = os.environ.get('MCP_BEARER', '')
DISCOUNT_PERCENTAGE = float(os.environ.get('DISCOUNT_PERCENTAGE', '10'))
LOW_STOCK_THRESHOLD = int(os.environ.get('LOW_STOCK_THRESHOLD', '5'))
RESULTS_FILE = os.environ.get('RESULTS_FILE', 'results_mcp.json')

headers = {"Authorization": f"Bearer {MCP_BEARER}"} if MCP_BEARER else {}

def main():
    payload = {
        "discount": DISCOUNT_PERCENTAGE,
        "lowStockThreshold": LOW_STOCK_THRESHOLD
    }
    start = time.monotonic()
    resp = requests.post(f"{MCP_HOST}/discount-lowstock", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    end = time.monotonic()
    result = {
        "start": start,
        "end": end,
        "duration": end - start,
        "products_updated": data['products_updated'],
        "num_api_calls": data.get('num_api_calls', -1),
        "errors": data.get('errors', []),
    }
    with open(RESULTS_FILE, 'w') as f:
        json.dump(result, f, indent=2)

if __name__ == '__main__':
    main()