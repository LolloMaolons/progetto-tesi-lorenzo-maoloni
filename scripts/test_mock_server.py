import subprocess
import json

proc = subprocess.Popen([
    "python", "../mcp-server-orders/server.py"
], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "callTool",
    "params": {
        "name": "orders.notifyPending",
        "arguments": {"product_id": 123}
    }
}

proc.stdin.write(json.dumps(request) + "\n")
proc.stdin.flush()

response = proc.stdout.readline()
print("Risposta dal mock:", response)

proc.terminate()
