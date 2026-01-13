from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os


REST_BASE = os.getenv("REST_BASE_URL", "http://api-rest:8080")
LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", 25))
DISCOUNT_PERCENTAGE = int(os.getenv("DISCOUNT_PERCENTAGE", 10))
BASE_PRICES = {
    1: 1499.0, 
    2: 29.0, 
    3: 79.0, 
    4: 329.0, 
    5: 119.0, 
    6: 149.0, 
    7: 199.0, 
    8: 129.0,
    9: 799.0, 
    10: 999.0, 
    11: 899.0, 
    12: 649.0, 
    13: 59.0, 
    14: 179.0, 
    15: 549.0,
    16: 229.0, 
    17: 249.0, 
    18: 159.0, 
    19: 399.0, 
    20: 299.0,
}

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/rpc")
async def rpc_handler(request: Request):
    req = await request.json()
    method = req.get("method")
    params = req.get("params", {})
    id_ = req.get("id")
    try:
        if method == "getLowStockProducts":
            threshold = params.get("threshold", LOW_STOCK_THRESHOLD)
            result = get_low_stock(threshold)
        elif method == "discountProduct":
            pid = params.get("productId") or params.get("id")
            if pid is None:
                raise Exception("productId mancante")
            discount = params.get("discount", DISCOUNT_PERCENTAGE)
            threshold = params.get("threshold", LOW_STOCK_THRESHOLD)
            result = discount_product(pid, discount, threshold)
        elif method == "resetProductPrice" or method == "resetProduct":
            pid = params.get("productId") or params.get("id")
            if pid is None:
                raise Exception("productId mancante")
            threshold = params.get("threshold", LOW_STOCK_THRESHOLD)
            result = reset_product_price(pid, threshold)
        elif method == "discountAllLowStock":
            discount = params.get("discount", DISCOUNT_PERCENTAGE)
            threshold = params.get("threshold", LOW_STOCK_THRESHOLD)
            result = discount_all_low_stock(discount, threshold)
        elif method == "resetAllHighStock":
            threshold = params.get("threshold", LOW_STOCK_THRESHOLD)
            result = reset_all_high_stock(threshold)
        else:
            return JSONResponse({"jsonrpc": "2.0", "id": id_, "error": {"code":-32601, "message":"Method not found"}})
        return JSONResponse({"jsonrpc": "2.0", "id": id_, "result": result})
    except Exception as e:
        return JSONResponse({"jsonrpc": "2.0", "id": id_, "error": {"code":-32000, "message":str(e)}})


def get_low_stock(threshold=LOW_STOCK_THRESHOLD):
    resp = requests.get(f"{REST_BASE}/products")
    resp.raise_for_status()
    products = resp.json()
    return [p for p in products if p["stock"] < threshold]

def discount_product(pid, discount, threshold=LOW_STOCK_THRESHOLD):
    prod = requests.get(f"{REST_BASE}/products/{pid}").json()
    if prod["stock"] < threshold:
        base_price = BASE_PRICES.get(pid, prod["price"])
        scontato = round(base_price * (1 - discount/100), 2)
        if abs(prod["price"] - scontato) > 0.01:
            r = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": scontato})
            r.raise_for_status()
            return r.json()
        else:
            return {"message": f"Prezzo già scontato per prodotto {pid}", **prod}
    else:
        return {"message": f"Prodotto {pid} non in low stock (stock={prod['stock']}, soglia={threshold})", **prod}

def reset_product_price(pid, threshold=LOW_STOCK_THRESHOLD):
    prod = requests.get(f"{REST_BASE}/products/{pid}").json()
    if prod["stock"] >= threshold:
        base_price = BASE_PRICES.get(pid, prod["price"])
        if abs(prod["price"] - base_price) > 0.01:
            r = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": base_price})
            r.raise_for_status()
            return r.json()
        else:
            return {"message": f"Prezzo già a valore base per prodotto {pid}", **prod}
    else:
        return {"message": f"Prodotto {pid} non in high stock (stock={prod['stock']}, soglia={threshold})", **prod}

def discount_all_low_stock(discount, threshold=LOW_STOCK_THRESHOLD):
    low_products = get_low_stock(threshold)
    results = []
    for p in low_products:
        pid = p["id"]
        results.append(discount_product(pid, discount, threshold))
    return results


def reset_all_high_stock(threshold=LOW_STOCK_THRESHOLD):
    resp = requests.get(f"{REST_BASE}/products")
    resp.raise_for_status()
    products = resp.json()
    results = []
    for p in products:
        if p["stock"] >= threshold:
            pid = p["id"]
            prod = requests.get(f"{REST_BASE}/products/{pid}").json()
            base_price = BASE_PRICES.get(pid, prod["price"])
            cur_price = prod["price"]
            if abs(cur_price - base_price) > 0.01:
                r = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": base_price})
                r.raise_for_status()
                results.append(r.json())
            else:
                results.append(prod)
    return results

