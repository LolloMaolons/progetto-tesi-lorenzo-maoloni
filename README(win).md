# Architettura ibrida REST + GraphQL + WebSocket + MCP (Demo tesi) – Guida PowerShell

Questa guida fornisce **tutti i principali comandi e test** per ambiente **Windows/PowerShell** per la demo di architettura ibrida REST/GraphQL/WebSocket/MCP, allineata al capitolo metodologico e ai casi di benchmarking/sicurezza della tesi.

## Indice

- [Requisiti](#requisiti)
- [Preparazione ambiente](#preparazione-ambiente)
- [Avvio rapido e verifiche](#avvio-rapido-e-verifiche)
- [Servizi inclusi](#servizi-inclusi)
- [Test funzionali](#test-funzionali)
  - [Test REST](#test-rest)
  - [Test GraphQL](#test-graphql)
  - [Test WebSocket](#test-websocket)
  - [Test strumenti MCP (Agent)](#test-strumenti-mcp-agent)
  - [Verifica su tutti i layer](#verifica-su-tutti-i-layer)
- [Autenticazione JWT (opzionale)](#autenticazione-jwt-opzionale)
- [Osservabilità (log, metriche, trace)](#osservabilità-log-metriche-trace)
- [Load test Artillery](#load-test-artillery)
  - [Risultati Artillery e Benchmark](#risultati-artillery-e-benchmark)
- [Test sicurezza](#test-sicurezza)
  - [Rate limiting](#rate-limiting)
  - [Depth limiting GraphQL](#depth-limiting-graphql)
  - [Allowed Origins/Payload WS](#allowed-originspayload-ws)
- [Test osservabilità](#test-osservabilità)
- [Script e utility](#script-e-utility)
- [Variabili d’ambiente](#variabili-dambiente)
- [Diagramma architetturale](#diagramma-architetturale)
- [Troubleshooting](#troubleshooting)

---

## Requisiti

- **Docker Desktop (con Compose)**
- **Node.js** (`wscat`, `artillery`)
- **Python 3.11+** (per test MCP locale, opzionale)
- **Artillery:**  
  ```powershell
  npm install -g artillery
  ```
- **wscat** (WebSocket client):
  ```powershell
  npm install -g wscat
  ```
- *Consigliato*: PowerShell >=7

---

## Preparazione ambiente

Apri PowerShell nella root repo.

1. Clone:
   ```powershell
   git clone https://github.com/LolloMaolons/progetto-tesi-lorenzo-maoloni.git
   cd progetto-tesi-lorenzo-maoloni
   ```
2. Build e cleanup:
   ```powershell
   docker compose down -v
   docker compose build
   ```

---

## Avvio rapido e verifiche

1. Avvio stack:
   ```powershell
   docker compose up -d
   docker compose ps
   ```
2. Verifiche servizi:
   ```powershell
   Invoke-RestMethod http://localhost:8080/products
   wscat -c ws://localhost:7070/ws
   Start-Process "http://localhost:4000/graphql"
   ```

---

## Servizi inclusi

| Servizio             | Porta | Ruolo (breve)           |
|----------------------|-------|-------------------------|
| api-rest             | 8080  | API REST, core prodotti |
| gateway-graphql      | 4000  | Query API GraphQL       |
| ws-events            | 7070  | WebSocket events        |
| redis                | 6379  | Pub/Sub                 |
| mcp-host             | 5000  | Orchestratore MCP agent |
| mcp-server-catalog   | 5002  | Tool MCP prodotti       |
| mcp-server-orders    | 5003  | Tool MCP mock ordini    |

---

## Test funzionali

### Test REST

```powershell
# Lista prodotti
Invoke-RestMethod http://localhost:8080/products
# Singolo prodotto
Invoke-RestMethod http://localhost:8080/products/1
# Aggiorna stock e prezzo
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=8&price=1000" -Method Patch
```

### Test GraphQL

Apri [http://localhost:4000/graphql](http://localhost:4000/graphql)  
Nel playground esegui:

```graphql
{
  product(id: 1) { id name price stock }
  products { id name price stock }
}
```

### Test WebSocket

Ricevi price/stock update real-time in PowerShell:

```powershell
wscat -c ws://localhost:7070/ws
```

### Test strumenti MCP (Agent)

Avvia orchestration MCP (solo via tool/agent, *non autonomo!*):
```powershell
docker compose run --rm mcp-host
```
*Loggherà le PATCH eseguite.*

**Test tool singolo (manuale):**
```powershell
Invoke-WebRequest -Uri http://localhost:5000/rpc -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"jsonrpc":"2.0", "id":1, "method":"discountAllLowStock", "params":{"discount":10,"threshold":15}}'
```

---

### Verifica su tutti i layer

```powershell
# Dopo un sconto/promo:
Invoke-RestMethod http://localhost:8080/products/1
# (price cambia)
Invoke-RestMethod http://localhost:8080/products
# vedi lotti scontati anche da GraphQL
```

---

## Autenticazione JWT (opzionale)

### Abilitazione
1. `.env`:
   ```
   JWT_SECRET=mia-pwd-test
   ```
2. Restart:
   ```powershell
   docker compose down -v
   docker compose build
   docker compose up -d
   ```

### Token generation
**Node.js:**
```powershell
$jwt = node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'admin',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'mia-pwd-test'));"
```
**Python (da dentro api-rest):**
```powershell
$jwt = docker compose exec api-rest python -c "import jwt,time; print(jwt.encode({'sub':'user1','role':'admin','exp':int(time.time())+3600}, 'mia-pwd-test', algorithm='HS256'))"
```

### Uso token

REST:
```powershell
Invoke-RestMethod http://localhost:8080/products -Headers @{"Authorization"="Bearer $jwt"}
```
GraphQL (nella sezione HTTP HEADERS nel playground):
```json
{
  "Authorization": "Bearer <jwt>"
}
```
WebSocket:
```powershell
wscat -c "ws://localhost:7070/ws?token=$jwt"
```

**Ruoli:**  
- admin = full CRUD  
- viewer = sola lettura (PATCH/POST → 403)

---

## Osservabilità (log, metriche, trace)

- **Logs**:
  ```powershell
  docker compose logs -f api-rest
  docker compose logs -f ws-events
  ```
- **Log tracciato**:
  ```powershell
  Invoke-RestMethod http://localhost:8080/products/1 -Headers @{"X-Trace-ID" = "test-pw-001"}
  docker compose logs api-rest --tail=5 | Select-String test-pw-001
  ```
- **Metriche Prometheus**:
  ```powershell
  Invoke-RestMethod http://localhost:8080/metrics | Select-String api_rest_requests_total
  Invoke-RestMethod http://localhost:9090/metrics | Select-String graphql_requests_total
  ```
- **Health check**:
  ```powershell
  Invoke-RestMethod http://localhost:8080/health
  ```

---

## Load test Artillery

**REST PATCH:**
```powershell
artillery run misurazioni/artillery-discount-rest.yml
```
**MCP batch:**
```powershell
artillery run misurazioni/artillery-discount-mcp.yaml
```
**GraphQL:**
```powershell
artillery run misurazioni/artillery-test-graphql.yml
```
**WebSocket:**
```powershell
artillery run misurazioni/artillery-test-ws.yml
```

### Risultati Artillery e Benchmark

**REST PATCH (report-rest.json):**
- 222 richieste OK su 300
- errori 422: 78
- Mean: 5.1ms
- P99: 7ms

**MCP batch (report-mcp.json):**
- 243 OK su 300
- errori 422: 57
- Mean: 5.1ms
- P99: 7ms

**Conclusione:**  
Performance batch REST e batch MCP sono comparabili; MCP batch con meno errori e PATCH inutili.

---

## Test sicurezza

### Rate limiting

Imposta in `.env`:
```
RATE_LIMIT=5/minute
```
Restart:
```powershell
docker compose up -d api-rest
```
Test:
```powershell
1..10 | % { Invoke-RestMethod http://localhost:8080/products; Start-Sleep -Seconds 1 }
# Atteso: 200 x5 poi 429
```

### Depth limiting GraphQL

In `.env`:
```
GRAPHQL_DEPTH_LIMIT=7
```
Test (nel playground o con `Invoke-WebRequest`), lancia una query over-depth → errore HTTP 400.

### Allowed Origins/Payload WS

In `.env`:
```
WS_ALLOWED_ORIGINS=http://localhost:3000
```
Test connessione:
```powershell
wscat -c ws://localhost:7070/ws -H "Origin: http://badorigin.com"   # rifiutata
wscat -c ws://localhost:7070/ws -H "Origin: http://localhost:3000"  # accettata
```

---

## Test osservabilità

```powershell
Invoke-RestMethod http://localhost:8080/products/1 -Headers @{"X-Trace-ID" = "audit-ps-01"}
docker compose logs api-rest --tail=10 | Select-String audit-ps-01
```
Healthcheck:
```powershell
Invoke-RestMethod http://localhost:8080/health
```

---

## Script e utility

- **Reset prodotti:**
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8080/reset" -Method Post
  ```
- **ws-events consumer:**
  ```powershell
  node scripts/ws-events-consumer.js
  ```
- **WS latency report:**
  ```powershell
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

## Diagramma architetturale

```
[REST API]      [GraphQL]       [WebSocket]
    │               │                │
    │──────────▲────│─────────▲──────│────────────
    │   pubsub │    │  eventi │      │
  ┌─▼──────────┴────┴───────┬─▼──────┘
  │         Redis           │
  └──────────┬──────────────┘
             │
        [mcp-host]───► [MCP tools]
```

---

## Troubleshooting

| Problema              | Soluzione                                       |
|-----------------------|-------------------------------------------------|
| 401 Unauthorized      | Rigenera ed usa il token JWT                    |
| 403 Forbidden         | Token viewer su PATCH/POST: usa admin           |
| 429 Too Many Requests | Superato il RATE_LIMIT: attendi o aumenta quota |
| Nessun evento WS      | ws-events/redis down: controlla logs            |
| MCP host exit         | Normale, one-shot: controlla logs se dubbi      |

Tip per diagnostica:
```powershell
docker compose ps
docker compose logs -f api-rest
Invoke-RestMethod http://localhost:8080/metrics
```

---