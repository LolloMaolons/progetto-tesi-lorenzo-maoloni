import os
import time
import requests
import json

API_URL = os.environ['REST_API_URL']
DISCOUNT = float(os.environ.get('DISCOUNT_PERCENTAGE', '10'))
THRESHOLD = int(os.environ.get('LOW_STOCK_THRESHOLD', '5'))
RESULTS = os.environ.get('RESULTS_FILE', 'results_rest.json')

headers = {}

def main():
    start = time.monotonic()
    num_api_calls = 0
    resp = requests.get(f"{API_URL}/products", headers=headers)
    num_api_calls += 1
    assert resp.status_code == 200, resp.text
    products = resp.json()
    low_stock_p = [p for p in products if p['stock'] < THRESHOLD]
    
    for p in low_stock_p:
        new_price = p['price'] * (1 - DISCOUNT/100)
        up_resp = requests.patch(
            f"{API_URL}/products/{p['id']}",
            json={'price': new_price},
            headers=headers,
        )
        num_api_calls += 1
        assert up_resp.status_code == 200, up_resp.text

    end = time.monotonic()
    result = {
        "start": start,
        "end": end,
        "duration": end - start,
        "products_updated": len(low_stock_p),
        "num_api_calls": num_api_calls,
    }
    with open(RESULTS, 'w') as f:
        json.dump(result, f, indent=2)

if __name__ == '__main__':
    main()