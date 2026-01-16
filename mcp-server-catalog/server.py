import sys, json, os, requests, redis

REST_BASE = os.getenv("REST_BASE_URL", "http://localhost:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

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

def respond(id, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": id}
    if error:
        msg["error"] = {"code": -32000, "message": error}
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def list_tools():
    return [
        {
            "name": "catalog.searchLowStock",
            "description": "List products with stock <= threshold",
            "input_schema": {
                "type": "object",
                "properties": {
                    "threshold": {"type": "integer"}
                },
                "required": ["threshold"]
            }
        },
        {
            "name": "catalog.applyDiscountAll",
            "description": "Applica uno sconto percentuale a tutti i prodotti con stock < threshold e non già scontati",
            "input_schema": {
                "type": "object",
                "properties": {
                    "percent": {"type": "number"},
                    "threshold": {"type": "integer"}
                },
                "required": ["percent", "threshold"]
            }
        },
        {
            "name": "catalog.resetPriceAll",
            "description": "Resetta il prezzo base di tutti i prodotti con stock >= threshold",
            "input_schema": {
                "type": "object",
                "properties": {
                    "threshold": {"type": "integer"}
                },
                "required": ["threshold"]
            }
        },
        {
            "name": "catalog.applyDiscount",
            "description": "Apply percent discount to a product if not already discounted and stock < threshold",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "percent": {"type": "number"},
                    "threshold": {"type": "integer"}
                },
                "required": ["product_id", "percent", "threshold"]
            }
        },
        {
            "name": "catalog.resetPrice",
            "description": "Reset product price to base if stock >= threshold",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "threshold": {"type": "integer"}
                },
                "required": ["product_id", "threshold"]
            }
        }
    ]

def handle(req):
    method = req.get("method")
    id_ = req.get("id")

    if method == "initialize":
        return respond(id_, {"capabilities": {"tools": True}})
    if method == "listTools":
        return respond(id_, {"tools": list_tools()})
    if method == "callTool":
        params = req.get("params", {})
        tool = params.get("name")
        args = params.get("arguments", {})


        if tool == "catalog.applyDiscountAll":
            percent = float(args.get("percent"))
            threshold = int(args.get("threshold"))
            try:
                redis_client = redis.Redis.from_url(REDIS_URL)
                resp = requests.get(f"{REST_BASE}/products")
                resp.raise_for_status()
                products = resp.json()
                updated = []
                already_discounted = []
                for prod in products:
                    pid = prod["id"]
                    base_price = BASE_PRICES.get(pid, prod["price"])
                    if prod["stock"] < threshold:
                        if abs(prod["price"] - base_price) < 0.01:
                            new_price = round(base_price * (1 - percent/100), 2)
                            upd = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": new_price})
                            upd.raise_for_status()
                            updated.append({"id": pid, "old_price": base_price, "new_price": new_price})
                        else:
                            already_discounted.append({"id": pid, "current_price": prod["price"]})
                if not updated:
                    msg = "Nessun prodotto aggiornato. Tutti i prodotti in low stock sono già scontati."
                    if already_discounted:
                        msg += f" Esempio: prodotto {already_discounted[0]['id']} già scontato (prezzo attuale: {already_discounted[0]['current_price']})."
                    return respond(id_, {"message": msg})
                return respond(id_, {"updated": updated, "count": len(updated)})
            except Exception as e:
                return respond(id_, error=f"Error: {str(e)}")


        if tool == "catalog.resetPriceAll":
            threshold = int(args.get("threshold"))
            try:
                redis_client = redis.Redis.from_url(REDIS_URL)
                resp = requests.get(f"{REST_BASE}/products")
                resp.raise_for_status()
                products = resp.json()
                reset = []
                already_base = []
                for prod in products:
                    pid = prod["id"]
                    base_price = BASE_PRICES.get(pid, prod["price"])
                    if prod["stock"] >= threshold:
                        if abs(prod["price"] - base_price) > 0.01:
                            old_price = prod["price"]
                            upd = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": base_price})
                            upd.raise_for_status()
                            reset.append({"id": pid, "old_price": old_price, "new_price": base_price})
                        else:
                            already_base.append({"id": pid})
                if not reset:
                    msg = "Nessun prodotto aggiornato. Tutti i prodotti in high stock sono già a prezzo base."
                    if already_base:
                        msg += f" Esempio: prodotto {already_base[0]['id']} già a valore base."
                    return respond(id_, {"message": msg})
                return respond(id_, {"reset": reset, "count": len(reset)})
            except Exception as e:
                return respond(id_, error=f"Error: {str(e)}")

        if tool == "catalog.searchLowStock":
            threshold = int(args.get("threshold", 25))
            try:
                resp = requests.get(f"{REST_BASE}/products")
                resp.raise_for_status()
                items = [p for p in resp.json() if p["stock"] <= threshold]
                return respond(id_, {"items": items})
            except Exception as e:
                return respond(id_, error=f"REST API error: {str(e)}")

        if tool == "catalog.applyDiscount":
            pid = int(args.get("product_id"))
            percent = float(args.get("percent"))
            threshold = int(args.get("threshold"))
            try:
                prod = requests.get(f"{REST_BASE}/products/{pid}").json()
                base_price = BASE_PRICES.get(pid, prod["price"])
                if prod["stock"] < threshold:
                    if abs(prod["price"] - base_price) < 0.01:
                        new_price = round(base_price * (1 - percent/100), 2)
                        upd = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": new_price})
                        upd.raise_for_status()
                        return respond(id_, {
                            "id": pid,
                            "old_price": base_price,
                            "new_price": new_price,
                            "discount_percent": percent
                        })
                    else:
                        return respond(id_, {"message": f"Prezzo già scontato per prodotto {pid}", "current_price": prod["price"]})
                else:
                    return respond(id_, {"message": f"Prodotto {pid} non in low stock (stock={prod['stock']}, soglia={threshold})"})
            except Exception as e:
                return respond(id_, error=f"Error: {str(e)}")

        if tool == "catalog.resetPrice":
            pid = int(args.get("product_id"))
            threshold = int(args.get("threshold"))
            try:
                redis_client = redis.Redis.from_url(REDIS_URL)
                prod = requests.get(f"{REST_BASE}/products/{pid}").json()
                base_price = BASE_PRICES.get(pid, prod["price"])
                if prod["stock"] >= threshold:
                    if abs(prod["price"] - base_price) > 0.01:
                        old_price = prod["price"]
                        upd = requests.patch(f"{REST_BASE}/products/{pid}", params={"price": base_price})
                        upd.raise_for_status()
                        # Evento price_update pubblicato solo da API REST
                        return respond(id_, {
                            "id": pid,
                            "old_price": old_price,
                            "new_price": base_price
                        })
                    else:
                        return respond(id_, {"message": f"Prezzo già a valore base per prodotto {pid}"})
                else:
                    return respond(id_, {"message": f"Prodotto {pid} non in high stock (stock={prod['stock']}, soglia={threshold})"})
            except Exception as e:
                return respond(id_, error=f"Error: {str(e)}")

        return respond(id_, error="unknown tool")
    return respond(id_, error="unknown method")

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            handle(req)
        except Exception as e:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)}
            }) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()