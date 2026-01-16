
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

def call_mcp_server(server_script, method, params=None):
    request = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        request["params"] = params
    proc = subprocess.Popen(
        ["python", server_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )
    stdout, _ = proc.communicate(json.dumps(request) + "\n")
    return json.loads(stdout.strip())


CATALOG_SERVER = os.getenv("CATALOG_SERVER", "/app/server-catalog.py")
ORDERS_SERVER = os.getenv("ORDERS_SERVER", "/app/server-orders.py")

@app.post("/rpc")
async def rpc_proxy(request: Request):
    body = await request.json()
    method = body.get("method", "")
    if method.startswith("orders.") or (method == "callTool" and body.get("params", {}).get("name", "").startswith("orders.")):
        server_script = ORDERS_SERVER
    else:
        server_script = CATALOG_SERVER
    proc = subprocess.Popen([
        "python", server_script
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    stdout, _ = proc.communicate(json.dumps(body) + "\n")
    import sys
    print("[MCP DEBUG] STDOUT RAW:", repr(stdout), file=sys.stderr, flush=True)
    try:
        response = json.loads(stdout.strip())
    except Exception:
        response = {"jsonrpc": "2.0", "error": {"code": -32000, "message": "Invalid MCP server response"}}
    return JSONResponse(content=response)

@app.post("/mcp/tools")
async def call_tool(request: Request):
    body = await request.json()
    name = body.get("name")
    arguments = body.get("arguments", {})
    response = call_mcp_server(CATALOG_SERVER, "callTool", {
        "name": name,
        "arguments": arguments
    })
    return JSONResponse(content=response)

@app.post("/mcp/search-low-stock")
async def search_low_stock(request: Request):
    body = await request.json()
    threshold = body.get("threshold", 25)
    response = call_mcp_server(CATALOG_SERVER, "callTool", {
        "name": "catalog.searchLowStock",
        "arguments": {"threshold": threshold}
    })
    return JSONResponse(content=response)

@app.post("/mcp/apply-discount")
async def apply_discount(request: Request):
    body = await request.json()
    product_id = body.get("product_id")
    percent = body.get("percent")
    threshold = body.get("threshold", 25)
    response = call_mcp_server(CATALOG_SERVER, "callTool", {
        "name": "catalog.applyDiscount",
        "arguments": {
            "product_id": product_id,
            "percent": percent,
            "threshold": threshold
        }
    })
    return JSONResponse(content=response)

@app.post("/mcp/reset-price")
async def reset_price(request: Request):
    """
    Wrapper HTTP per catalog.resetPrice.
    Accetta body JSON {"product_id": int, "threshold": int facoltativo}.
    Esegue il tool MCP catalog.resetPrice tramite JSON-RPC e restituisce la risposta.
    """
    try:
        body = await request.json()
        product_id = body.get("product_id")
        threshold = body.get("threshold", 25)
        if product_id is None:
            return JSONResponse(status_code=400, content={"error": "product_id richiesto"})
        response = call_mcp_server(CATALOG_SERVER, "callTool", {
            "name": "catalog.resetPrice",
            "arguments": {
                "product_id": product_id,
                "threshold": threshold
            }
        })
        return JSONResponse(content=response)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/mcp/tools")
async def list_tools():
    response = call_mcp_server(CATALOG_SERVER, "listTools")
    return JSONResponse(content=response)

