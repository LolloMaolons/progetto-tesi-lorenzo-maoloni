from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

load_dotenv()
LLM_MODEL = os.getenv("LLM_MODEL", "phi3")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

@app.get("/health")
async def health():
    return {"status": "ok"}

    
@app.post("/llm-invoke")
async def llm_invoke(request: Request):
    """
    Endpoint per invocare LLM SOLO per tool MCP.
    Body: {"prompt": "..."}
    """
    body = await request.json()
    prompt = body.get("prompt")
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "Prompt richiesto"})

    allowed_keywords = ["catalog.", "orders.", "tool MCP", "sconto", "prezzo", "stock", "prodotto", "reset"]
    if not any(kw.lower() in prompt.lower() for kw in allowed_keywords):
        return JSONResponse(status_code=403, content={"error": "Richiesta non consentita: puoi solo usare i tool MCP (catalog, orders, sconto, prezzo, stock, prodotto, reset)"})

    system_prompt = (
    "You are an MCP assistant. When prompted to perform an action, ALWAYS respond ONLY with a valid MCP JSON-RPC object, choosing ONLY from these tools:\n"
    "- catalog.searchLowStock: List products with stock <= threshold\n"
    "- catalog.applyDiscountAll: Apply a percentage discount to all products with stock < threshold and not already discounted\n"
    "- catalog.resetPriceAll: Reset the base price of all products with stock >= threshold\n"
    "- catalog.applyDiscount: Apply a percent discount to a product if not already discounted and stock < threshold\n"
    "- catalog.resetPrice: Reset product price to base if stock >= threshold\n"
    "- orders.notifyPending: Notify about pending orders. You can use it to notify a specific product ( product_id ).\n"
    "Esempi di risposta:\n"
    '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "callTool",\n  "params": {\n    "name": "orders.notifyPending",\n    "arguments": { "product_id": 123 }\n  }\n}'
    '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "callTool",\n  "params": {\n    "name": "catalog.applyDiscount",\n    "arguments": { "product_id": 1, "percent": 10, "threshold": 25 }\n  }\n}'
    '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "callTool",\n  "params": {\n    "name": "catalog.resetPrice",\n    "arguments": { "product_id": 1, "threshold": 25 }\n  }\n}'
    '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "callTool",\n  "params": {\n    "name": "catalog.applyDiscountAll",\n    "arguments": { "percent": 10, "threshold": 25 }\n  }\n}'
    '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "callTool",\n  "params": {\n    "name": "catalog.resetPriceAll",\n    "arguments": { "threshold": 25 }\n  }\n}'
    '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "callTool",\n  "params": {\n    "name": "catalog.searchLowStock",\n    "arguments": { "threshold": 25 }\n  }\n}'
    "Non aggiungere spiegazioni, testo extra, markdown o altro. Solo il JSON-RPC. Se la richiesta non riguarda questi tool, rispondi solo con: {\"error\": \"Posso solo aiutarti con i tool MCP.\"}"
)
    data = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        resp = requests.post(OLLAMA_URL, json=data, stream=True)
        resp.raise_for_status()
        result = ""
        buffer = b""
        for chunk in resp.iter_content(chunk_size=None):
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "message" in obj and obj["message"]["role"] == "assistant":
                        result += obj["message"].get("content", "")
                except Exception:
                    continue
        if buffer:
            try:
                obj = json.loads(buffer)
                if "message" in obj and obj["message"]["role"] == "assistant":
                    result += obj["message"].get("content", "")
            except Exception:
                pass

        import re
        import re
        m = re.search(r"```json(.*?)```", result, re.DOTALL)
        json_rpc = None
        if m:
            try:
                json_rpc = json.loads(m.group(1))
            except Exception:
                pass
        if not json_rpc:
            m = re.search(r"({[^}]+})", result, re.DOTALL)
            if m:
                try:
                    json_rpc = json.loads(m.group(1))
                except Exception:
                    pass
        if json_rpc and isinstance(json_rpc, dict) and json_rpc.get("method") == "callTool":
            try:
                mcp_resp = requests.post("http://localhost:5000/rpc", json=json_rpc)
                mcp_resp.raise_for_status()
                mcp_result = mcp_resp.json()
                summary = "Azione MCP eseguita: "
                params = json_rpc.get("params", {})
                tool = params.get("name")
                arguments = params.get("arguments")
                summary += f"tool={tool}, args={arguments}. "
                if "result" in mcp_result:
                    summary += f"Risultato: {mcp_result['result']}"
                elif "error" in mcp_result:
                    summary += f"Errore: {mcp_result['error']}"
                return JSONResponse(content={"result": mcp_result, "summary": summary, "llm": result})
            except Exception as e:
                return JSONResponse(content={"error": f"Errore esecuzione tool MCP: {str(e)}", "llm": result})
        return JSONResponse(content={"result": result, "summary": "Nessuna azione MCP eseguita."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



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
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(json.dumps(body) + "\n")
    import sys
    print("[MCP DEBUG] STDOUT RAW:", repr(stdout), file=sys.stderr, flush=True)
    if stderr:
        print("[MCP DEBUG] STDERR RAW:", repr(stderr), file=sys.stderr, flush=True)
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

