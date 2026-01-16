import subprocess
import json

class MCPClient:
    def __init__(self, docker_service):
        """
        Connetti a un server MCP tramite docker compose exec
        """
        self.service = docker_service
        self.request_id = 0
    
    def send(self, method, params=None):
        """Invia richiesta JSON-RPC al server Docker"""
        self.request_id += 1
        request = {"jsonrpc": "2.0", "id": self.request_id, "method": method}
        if params:
            request["params"] = params
        
        cmd = [
            "docker", "compose", "exec", "-T", self.service,
            "python", "server.py"
        ]
        
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        
        stdout, _ = proc.communicate(json.dumps(request) + "\n")
        return json.loads(stdout.strip())


def main():
    print("🚀 Test MCP Server Catalog via Docker\n")
    
    client = MCPClient("mcp-server-catalog")
    
    print("1️⃣ Inizializzazione...")
    resp = client.send("initialize")
    print(f"   ✅ {resp['result']}\n")
    
    print("2️⃣ Lista Tool...")
    resp = client.send("listTools")
    for tool in resp['result']['tools']:
        print(f"   📦 {tool['name']}")
    print()
    
    print("3️⃣ Ricerca prodotti low-stock (threshold=15)...")
    resp = client.send("callTool", {
        "name": "catalog.searchLowStock",
        "arguments": {"threshold": 15}
    })
    
    items = resp['result']['items']
    print(f"   ✅ Trovati {len(items)} prodotti:")
    for item in items[:3]:
        print(f"      - ID {item['id']}: {item['name']} (stock: {item['stock']})")
    print()
    
    if items:
        pid = items[0]['id']
        print(f"4️⃣ Applicazione sconto 10% al prodotto {pid}...")
        resp = client.send("callTool", {
            "name": "catalog.applyDiscount",
            "arguments": {
                "product_id": pid,
                "percent": 10,
                "threshold": 25
            }
        })
        print("DEBUG:", resp)
    if 'result' in resp:
        result = resp['result']
    elif 'error' in resp:
        print("❌ Errore MCP:", resp['error'])
        result = None
    else:
        print("❌ Risposta inattesa:", resp)
        result = None   
        print(f"   ✅ Vecchio: €{result['old_price']} → Nuovo: €{result['new_price']}")
    
    print("\n🎉 Test completato!")


if __name__ == "__main__":
    main()
