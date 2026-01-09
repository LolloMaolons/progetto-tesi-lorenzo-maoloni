# Architettura ibrida REST + GraphQL + WebSocket + MCP (demo tesi)  
Questa demo implementa e mostra l'integrazione di REST, GraphQL, WebSocket e MCP agent/LLM come descritto nel capitolo metodologico.  
**Tutte le procedure, test e utility sono presentate in parallelo PowerShell & Bash**  
(permette massima ripetibilità su qualsiasi ambiente dev/didattico).

---

## Indice

- [Requisiti](#requisiti)
- [Preparazione ambiente](#preparazione-ambiente)
- [Avvio rapido (Bash e PowerShell)](#avvio-rapido-bash-e-powershell)
- [Servizi inclusi](#servizi-inclusi)
- [Test funzionali](#test-funzionali)
- [Autenticazione JWT (opzionale)](#autenticazione-jwt-opzionale)
- [Osservabilità e metriche](#osservabilità-e-metriche)
- [Load test & Benchmark (Artillery)](#load-test--benchmark-artillery)
- [Sezione test](#sezione-test)
- [Sicurezza](#sicurezza)
- [Script e utility](#script-e-utility)
- [Variabili d’ambiente](#variabili-dambiente)
- [Architettura logica](#architettura-logica)
- [Troubleshooting](#troubleshooting)

---

## Requisiti

- **Docker** e **Docker Compose**
- **Node.js** (per wscat, artillery)
- **Python 3.11+** (opzionale: test locali, MCP host)
- **Artillery**:
  - Bash/PowerShell: `npm install -g artillery`
- **wscat**:
  - Bash/PowerShell: `npm install -g wscat`

---

## Preparazione ambiente

### 1. Clona la repo

**Bash:**
```bash
git clone https://github.com/LolloMaolons/progetto-tesi-lorenzo-maoloni.git
cd progetto-tesi-lorenzo-maoloni
```
**PowerShell:**
```powershell
git clone https://github.com/LolloMaolons/progetto-tesi-lorenzo-maoloni.git
cd progetto-tesi-lorenzo-maoloni
```

### 2. Pulizia e build

**Bash:**
```bash
docker compose down -v
docker compose build
```
**PowerShell:**
```powershell
docker compose down -v
docker compose build
```

---

## Avvio rapido (Bash e PowerShell)

**Bash:**
```bash
docker compose up -d
docker compose ps
```
**PowerShell:**
```powershell
docker compose up -d
docker compose ps
```

Controlla servizi attivi e prosegui con i test.

---

## Servizi inclusi

| Servizio             | Porta | Descrizione fondamentale      |
|----------------------|-------|------------------------------|
| api-rest             | 8080  | API REST prodotti            |
| gateway-graphql      | 4000  | API GraphQL (aggregazione)   |
| ws-events            | 7070  | WebSocket eventi             |
| redis                | 6379  | Pub/Sub                      |
| mcp-host             | 5000  | Orchestratore MCP agent      |
| mcp-server-catalog   | 5002  | Tool MCP prodotti            |
| mcp-server-orders    | 5003  | Tool MCP mock ordini         |

---

## Test funzionali

### Test REST

**Bash**
```bash
curl http://localhost:8080/products
curl http://localhost:8080/products/1
curl -X PATCH "http://localhost:8080/products/1?stock=8&price=1000"
```
**PowerShell**
```powershell
Invoke-RestMethod http://localhost:8080/products
Invoke-RestMethod http://localhost:8080/products/1
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=8&price=1000" -Method Patch
```

### Test GraphQL

Apri browser su [http://localhost:4000/graphql](http://localhost:4000/graphql)

Query demo:
```graphql
{
  products { id name price stock }
  product(id: 1) { id name price stock }
}
```

### Test WebSocket

**Bash**
```bash
wscat -c ws://localhost:7070/ws
```
**PowerShell**
```powershell
wscat -c ws://localhost:7070/ws
```

### Test MCP strumenti/agent

Batch orchestrazione (non automatica: sempre su richiesta MCP!):

**Bash:**
```bash
docker compose run --rm mcp-host
```
**PowerShell:**
```powershell
docker compose run --rm mcp-host
```

Chiamata diretta tool MCP:

**Bash:**
```bash
curl -X POST http://localhost:5000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"discountAllLowStock","params":{"discount":10,"threshold":15}}'
```
**PowerShell:**
```powershell
Invoke-WebRequest -Uri http://localhost:5000/rpc -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"jsonrpc":"2.0", "id":1, "method":"discountAllLowStock", "params":{"discount":10,"threshold":15}}'
```

---

### Verifica effetti (tutti i layer)

**Bash**
```bash
curl http://localhost:8080/products/1
```
**PowerShell**
```powershell
Invoke-RestMethod http://localhost:8080/products/1
```
Verifica via GraphQL (Playground) che prezzi e stock cambino, oppure lascia aperto `wscat` per la ricezione real-time.

---

## Autenticazione JWT (opzionale)

### Abilitazione e avvio

1. `.env`:
   ```
   JWT_SECRET=demo-secret
   ```
2. Restart:

   **Bash/PowerShell**
   ```bash
   docker compose down -v
   docker compose build
   docker compose up -d
   ```

### Generazione token

**Node.js**
```bash
# Bash
jwt=$(node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user1',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'demo-secret'));")
# PowerShell
$jwt = node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user1',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'demo-secret'));"
```
**Python**
```bash
# Bash
jwt=$(docker compose exec api-rest python -c "import jwt,time; print(jwt.encode({'sub':'user1','role':'admin','exp':int(time.time())+3600}, 'demo-secret', algorithm='HS256'))")
# PowerShell
$jwt = docker compose exec api-rest python -c "import jwt,time; print(jwt.encode({'sub':'user1','role':'admin','exp':int(time.time())+3600}, 'demo-secret', algorithm='HS256'))"
```

### Uso token

**Bash**
```bash
curl -H "Authorization: Bearer $jwt" http://localhost:8080/products
```
**PowerShell**
```powershell
Invoke-RestMethod http://localhost:8080/products -Headers @{"Authorization"="Bearer $jwt"}
```

**GraphQL**: inserisci nel playground HTTP HEADERS
```json
{ "Authorization": "Bearer <jwt>" }
```

**WebSocket**:
```bash
wscat -c "ws://localhost:7070/ws?token=$jwt"
```

---

## Osservabilità e metriche

### Logging

**Bash**
```bash
docker compose logs -f api-rest
```
**PowerShell**
```powershell
docker compose logs -f api-rest
```
Per trace custom:
```bash
curl -H "X-Trace-ID: test-123" http://localhost:8080/products/1
# PowerShell:
Invoke-RestMethod http://localhost:8080/products/1 -Headers @{"X-Trace-ID" = "test-123"}
docker compose logs api-rest --tail=5 | grep test-123
# PowerShell:
docker compose logs api-rest --tail=5 | Select-String test-123
```

### Metriche Prometheus

**Bash**
```bash
curl http://localhost:8080/metrics | grep api_rest_requests_total
```
**PowerShell**
```powershell
Invoke-RestMethod http://localhost:8080/metrics | Select-String api_rest_requests_total
```

### Healthcheck

**Bash**
```bash
curl http://localhost:8080/health
```
**PowerShell**
```powershell
Invoke-RestMethod http://localhost:8080/health
```

---

## Load test & Benchmark (Artillery)

### REST PATCH  
**Bash & PowerShell**
```bash
artillery run misurazioni/artillery-discount-rest.yml
```
### MCP batch  
**Bash & PowerShell**
```bash
artillery run misurazioni/artillery-discount-mcp.yaml
```

### GraphQL
```bash
artillery run misurazioni/artillery-test-graphql.yml
```

### WebSocket
```bash
artillery run misurazioni/artillery-test-ws.yml
```

### Risultati (già presenti, estratti da report-mcp.json e report-rest.json):

| Metrica         | REST         | MCP          |
|-----------------|--------------|--------------|
| Latenza media   | 5.1 ms       | 5.1 ms       |
| P99             | 7 ms         | 7 ms         |
| Successi PATCH  | 222/300      | 243/300      |
| Errori 422      | 78           | 57           |
| Throughput      | 5 req/sec    | 5 req/sec    |
| VU failed       | 0            | 0            |

---

## Sezione test

### Test sicurezza

#### Rate limiting

1. In `.env`:
   ```
   RATE_LIMIT=5/minute
   ```
2. Restart `api-rest`.

**Bash**
```bash
for i in {1..10}; do curl http://localhost:8080/products; sleep 1; done
```
**PowerShell**
```powershell
1..10 | % { Invoke-RestMethod http://localhost:8080/products; Start-Sleep -Seconds 1 }
```

#### Depth limiting GraphQL

`.env`:
```
GRAPHQL_DEPTH_LIMIT=7
```

Test query >7 livelli:  
```bash
curl -X POST http://localhost:4000/graphql \
 -H "Content-Type: application/json" \
 -d '{"query":"{ products { recommendations { recommendations { ... } } } }"}'
```
*(PowerShell: usa Invoke-WebRequest con lo stesso payload)*

#### Allowed Origins/Payload WS

`.env`:
```
WS_ALLOWED_ORIGINS=http://localhost:3000
```
**Bash/PowerShell**
```bash
wscat -c ws://localhost:7070/ws -H "Origin: http://badorigin.com"   # bloccata
wscat -c ws://localhost:7070/ws -H "Origin: http://localhost:3000"  # ok
```

---

## Script e utility

- **Reset rapido prodotti:**

  **Bash**
  ```bash
  curl -X POST http://localhost:8080/reset
  ```
  **PowerShell**
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8080/reset" -Method Post
  ```

- **ws-events consumer:**  
  ```bash
  node scripts/ws-events-consumer.js
  ```
- **WS latency report:**  
  ```bash
  node misurazioni/ws-latency.js | python scripts/ws-latency-report.py
  ```

---

## Variabili d’ambiente

| Variabile             | Default                      | Descrizione                          |
|-----------------------|-----------------------------|--------------------------------------|
| `REST_BASE_URL`       | http://api-rest:8080        | URL REST per MCP-host/tools          |
| `REDIS_URL`           | redis://redis:6379/0        | URL redis                            |
| `JWT_SECRET`          | *(vuoto)*                   | Segreto JWT                          |
| `RATE_LIMIT`          | 100/minute                  | Limite rate REST                     |
| `WS_ALLOWED_ORIGINS`  | *                           | Origini consentite WS                |
| `WS_MAX_PAYLOAD`      | 1048576                     | Max payload WS                       |
| `LOW_STOCK_THRESHOLD` | 10                          | Threshold 'lowStock'                 |
| `GRAPHQL_DEPTH_LIMIT` | 10                          | Prof max query GraphQL               |

---

## Architettura logica

```
[REST API]      [GraphQL]       [WebSocket]
    │               │                │
    │─────────▲─────│────────▲───────│─────────
    │  pubsub │     │ eventi │       │
  ┌─▼─────────┴─────┴───────┬─▼─────┘
  │         Redis           │
  └─────────┬───────────────┘
            │
       [mcp-host]──► [MCP tool]
```

---

## Troubleshooting

| Problema               | Soluzione                                    |
|------------------------|----------------------------------------------|
| 401/403/429            | JWT scorretto, ruolo viewer, RATE_LIMIT      |
| Nessun evento WS       | Controlla ws-events/redis e i log            |
| MCP host exit subito   | Normale, one-shot: guarda docker compose logs|
| Patch non funzionante  | Controlla JWT, ruoli e che agent sia esplicito|
| Lentezza o errori conn.| Docker Compose la priorità: riavvia/ps/logs  |

**Comandi universali:**
```bash
docker compose ps
docker compose logs -f api-rest
Invoke-RestMethod http://localhost:8080/metrics
```

---