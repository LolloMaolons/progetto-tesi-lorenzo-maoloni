import sys, json, os, redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL)

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
        {"name": "orders.notifyPending", "description": "Notify pending orders for a product", "input_schema": {"product_id": "integer"}}
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

        if tool == "orders.notifyPending":
            pid = int(args.get("product_id"))
            try:
                r.publish("events", json.dumps({"type":"notify_pending","product_id": pid}))
            except Exception as e:
                return respond(id_, error=str(e))
            return respond(id_, {"status": "notified", "product_id": pid})

        return respond(id_, error="unknown tool")
    return respond(id_, error="unknown method")

def main():
    for line in sys.stdin:
        line=line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            handle(req)
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc":"2.0","error":{"code":-32000,"message":str(e)}})+"\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()