from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os

REST_BASE = os.getenv("REST_BASE_URL", "http://api-rest:8080")

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

app = FastAPI()

def get_headers():
    jwt_secret = os.getenv("JWT_SECRET", "")
    if jwt_secret:
        import jwt, time
        token = jwt.encode(
            {"sub": "mcp-host", "role": "admin", "exp": int(time.time()) + 3600},
            jwt_secret,
            algorithm="HS256"
        )
        return {"Authorization": f"Bearer {token}"}
    return {}

@app.post("/rpc")
async def rpc_handler(request: Request):
    req = await request.json()
    method = req.get("method")
    params = req.get("params", {})
    id_ = req.get("id")
    try:
        if method == "getLowStockProducts":
            threshold = params.get("threshold", 25)
            result = get_low_stock(threshold)
        elif method == "discountProduct":
            pid = params["productId"]
            discount = params.get("discount", 10)
            result = discount_product(pid, discount)
        elif method == "resetProductPrice":
            pid = params["productId"]
            result = reset_product_price(pid)
        elif method == "discountAllLowStock":
            discount = params.get("discount", 10)
            threshold = params.get("threshold", 25)
            result = discount_all_low_stock(discount, threshold)
        elif method == "resetAllHighStock":
            threshold = params.get("threshold", 25)
            result = reset_all_high_stock(threshold)
        else:
            return JSONResponse({"jsonrpc": "2.0", "id": id_, "error": {"code":-32601, "message":"Method not found"}})
        return JSONResponse({"jsonrpc": "2.0", "id": id_, "result": result})
    except Exception as e:
        return JSONResponse({"jsonrpc": "2.0", "id": id_, "error": {"code":-32000, "message":str(e)}})

def get_low_stock(threshold):
    resp = requests.get(f"{REST_BASE}/products", headers=get_headers())
    resp.raise_for_status()
    products = resp.json()
    return [p for p in products if p["stock"] <= threshold]

def discount_all_low_stock(discount, threshold):
    low_products = get_low_stock(threshold)
    results = []
    for p in low_products:
        pid = p["id"]
        results.append(discount_product(pid, discount))
    return results  

def discount_product(pid, discount):
    prod = requests.get(f"{REST_BASE}/products/{pid}", headers=get_headers()).json()
    base_price = BASE_PRICES.get(pid, prod["price"])
    scontato = round(base_price * (1 - discount/100), 2)
    r = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": scontato}, headers=get_headers())
    r.raise_for_status()
    return r.json()

def reset_product_price(pid):
    prod = requests.get(f"{REST_BASE}/products/{pid}", headers=get_headers()).json()
    base_price = BASE_PRICES.get(pid, prod["price"])
    r = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": base_price}, headers=get_headers())
    r.raise_for_status()
    return r.json()

def reset_all_high_stock(threshold):
    resp = requests.get(f"{REST_BASE}/products", headers=get_headers())
    resp.raise_for_status()
    products = resp.json()
    results = []
    for p in products:
        if p["stock"] > threshold:
            pid = p["id"]
            prod = requests.get(f"{REST_BASE}/products/{pid}", headers=get_headers()).json()
            base_price = BASE_PRICES.get(pid, prod["price"])
            cur_price = prod["price"]
            if abs(cur_price - base_price) > 0.01:
                r = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": base_price}, headers=get_headers())
                r.raise_for_status()
                results.append(r.json())
            else:
                results.append(prod)
    return results

