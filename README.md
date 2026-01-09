# Architettura ibrida REST + GraphQL + WebSocket + MCP (demo tesi)

Questa demo implementa e mostra la coesistenza dei quattro paradigmi descritti in tesi:
- **REST** per gestione risorse CRUD e stato autorevole
- **GraphQL** per viste client-driven, riduzione over/under-fetching, aggregazione dati
- **WebSocket** per notifiche real-time di aggiornamenti
- **MCP (Model Context Protocol)** per orchestrazione agent-based: l’agente MCP-host applica sconti/azioni solo su richiesta esplicita tramite tool JSON-RPC, secondo lo standard MCP

---

## Indice

- [Requisiti](#requisiti)
- [Preparazione dell'ambiente](#preparazione-dellambiente)
- [Avvio rapido](#avvio-rapido)
- [Servizi inclusi](#servizi-inclusi)
- [Testing funzionale e test end-to-end](#testing-funzionale-e-test-end-to-end)
  - [REST](#test-rest)
  - [GraphQL](#test-graphql)
  - [WebSocket](#test-websocket)
  - [MCP Tool/Agent](#test-mcp-agent)
  - [Verifica effetti](#verifica-effetti)
- [Autenticazione JWT (opzionale)](#autenticazione-jwt-opzionale)
  - [Abilitazione JWT e generazione token](#abilitazione-jwt-e-generazione-token)
  - [Ruoli e policy](#ruoli-e-policy)
- [Osservabilità](#osservabilità)
- [Load Testing con Artillery](#load-testing-con-artillery)
  - [Risultati test presenti](#risultati-test-presenti)
  - [Benchmark & Confronto MCP/REST](#benchmark--confronto-mcprest)
- [Test avanzati](#test-avanzati)
  - [Test sicurezza](#test-sicurezza)
    - [JWT](#test-jwt)
    - [Rate Limiting](#test-rate-limiting)
    - [GraphQL Depth Limiting](#test-graphql-depth-limiting)
    - [WebSocket Allowed Origins e payload](#test-allowed-origins-e-payload)
  - [Test osservabilità](#test-osservabilità)
- [Script utility](#script-utility)
- [Variabili d'ambiente](#variabili-dambiente)
- [Architettura logica](#architettura-logica)
- [Troubleshooting](#troubleshooting)

---

## Requisiti

- **Docker** e **Docker Compose** installati (versione 20.10+ raccomandata)
- **Node.js (>=18.x)** (per `wscat` e Artillery)
- **Python 3.11+** (per test agent MCP e tool in locale)
- **Artillery**: `npm install -g artillery` (per load e benchmark)

---

## Preparazione dell'ambiente

1. Clona la repository:

   ```bash
   git clone https://github.com/LolloMaolons/progetto-tesi-lorenzo-maoloni.git
   cd progetto-tesi-lorenzo-maoloni
   ```

2. (Primo uso) Pulisci e costruisci:

   ```bash
   docker compose down -v
   docker compose build
   ```

3. Installa strumenti opzionali:

   - **Artillery:**  
     ```bash
     npm install -g artillery
     ```
   - **WebSocket client:**  
     ```bash
     npm install -g wscat
     ```

---

## Avvio rapido

### Avvia i servizi (stateless, in-memory)

```bash
docker compose up -d
docker compose ps
```

#### Pull-down/clean completa:

```bash
docker compose down -v
docker compose build
docker compose up -d
```

---

## Servizi inclusi

| Servizio                | Tecnologia        | Porta    | Descrizione                                               |
|-------------------------|------------------|----------|-----------------------------------------------------------|
| **redis**               | Redis 7.x        | 6379     | Pub/Sub eventi e storage volatile                         |
| **api-rest**            | FastAPI          | 8080     | API REST, stato prodotti (in-memory), genera eventi Redis |
| **gateway-graphql**     | Apollo Server    | 4000     | API GraphQL, aggrega dati REST, esegue logica composita   |
| **ws-events**           | Node.js + ws     | 7070     | WebSocket server, inoltra eventi Redis ai client          |
| **mcp-server-catalog**  | Python MCP       | 5002     | MCP server: tool su prodotti/catalogo                     |
| **mcp-server-orders**   | Python MCP (mock)| 5003     | MCP server: tool mock ordini                              |
| **mcp-host**            | FastAPI MCP host | 5000     | MCP orchestrator/agent: invoca tool su richiesta agent/LLM|

---

## Testing funzionale e test end-to-end

### Test REST

```bash
curl http://localhost:8080/products      # Lista
curl http://localhost:8080/products/1    # Dettaglio
curl -X PATCH "http://localhost:8080/products/1?stock=8&price=1000"
```
PowerShell:
```powershell
Invoke-RestMethod http://localhost:8080/products
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=8&price=1000" -Method Patch
```

### Test GraphQL

Apri browser su [http://localhost:4000/graphql](http://localhost:4000/graphql)

Esempio query:
```graphql
{
  products { id name price stock lowStock }
  product(id: 1) { id name price stock }
}
```

### Test WebSocket

Ricevi eventi live da Redis:

```bash
wscat -c ws://localhost:7070/ws
```

### Test MCP Agent

Esegui orchestrazione batch da agente:

```bash
docker compose run --rm mcp-host
# Oppure local:
python mcp-host/main.py
```

Chiamata tool singolo via MCP-host (JSON-RPC):

```bash
curl -X POST http://localhost:5000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"discountAllLowStock","params":{"discount":10,"threshold":15}}'
```

---

### Verifica effetti

Visualizza stato dopo i test:

```bash
curl http://localhost:8080/products/1
# O via GraphQL: vedi price, stock, lowStock aggiornati
```

---

## Autenticazione JWT (opzionale)

### Abilitazione JWT e generazione token

1. Crea `.env`:
   ```env
   JWT_SECRET=demo-secret
   ```
2. Riavvia:
   ```bash
   docker compose down -v
   docker compose build
   docker compose up -d
   ```
3. Genera token (Node.js):
   ```bash
   node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user1',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'demo-secret'));"
   ```
   (Valido 1 ora)

### Utilizzo token

REST:
```bash
curl -H "Authorization: Bearer <jwt>" http://localhost:8080/products
```
GraphQL: inserisci header nel playground:
```json
{ "Authorization": "Bearer <jwt>" }
```
WebSocket:
```bash
wscat -c "ws://localhost:7070/ws?token=<jwt>"
```

### Ruoli e policy

- **admin**: full access (GET, PATCH, POST)
- **viewer**: sola lettura (qualsiasi PATCH/POST = 403)

---

## Osservabilità

- **Logging JSON**:  
  Tutti i servizi loggano in JSON strutturato con request/trace_id.
- **Logs**:
  ```bash
  docker compose logs -f api-rest
  docker compose logs -f ws-events
  ```
- **Metriche Prometheus**:
  - http://localhost:8080/metrics  (REST)
  - http://localhost:9090/metrics  (GraphQL)
- **Health Check**:
  ```bash
  curl http://localhost:8080/health
  # {"status":"healthy","redis":"connected"}
  ```

---

## Load Testing con Artillery

Per test riproducibili sono forniti file YAML già configurati in `misurazioni/`.

**Test REST (PATCH sconto)**  
```bash
artillery run misurazioni/artillery-discount-rest.yml
```

**Test MCP (JSON-RPC, batch sconto MCP-host):**  
```bash
artillery run misurazioni/artillery-discount-mcp.yaml
```

**Test GraphQL:**  
```bash
artillery run misurazioni/artillery-test-graphql.yml
```

**Test WebSocket (messaggi):**  
```bash
artillery run misurazioni/artillery-test-ws.yml
```

### Risultati test presenti

- I risultati ufficiali delle run sono consultabili nei file:
  - `misurazioni/report-mcp.json` (MCP discount batch)
  - `misurazioni/report-rest.json` (REST sconto batch)
- Estratto analytics da questi file:
  - REST PATCH: 222 su 300 richieste PATCH applicate (resto 422, es. già scontato)
  - MCP: 243 su 300 richieste PATCH batch batch applicate; meno errori, nessun vusers.failed
  - Latenza media: 5.1ms (entrambi), percentile 99: 7ms
  - Nessun VU fallito in nessun test
  - REST usa leggermente più banda totale

### Benchmark & Confronto MCP/REST

| Metrica         | REST         | MCP          |
|-----------------|--------------|--------------|
| Latenza media   | 5.1 ms       | 5.1 ms       |
| P99             | 7 ms         | 7 ms         |
| Successo PATCH  | 222/300      | 243/300      |
| Errori 422      | 78           | 57           |
| Throughput      | 5 req/sec    | 5 req/sec    |
| VU failed       | 0            | 0            |

**Conclusione**:  
Entrambi i paradigmi sono equivalenti per performance, MCP riduce richieste inutili e bandiera errori inferiori in batch, la differenza è architetturale non prestazionale.

---

## Test avanzati

### Test sicurezza

#### Test JWT

1. JWT non impostato: tutte le API pubbliche.
2. JWT settato: PATCH/POST solo per admin; viewer = 403.
   ```bash
   curl -H "Authorization: Bearer <jwt_admin>" -X PATCH ...
   # 200 OK
   curl -H "Authorization: Bearer <jwt_viewer>" -X PATCH ...
   # 403 Forbidden
   ```

#### Test Rate Limiting

Imposta `RATE_LIMIT="5/minute"` in `.env` e testa:

```bash
for i in {1..10}; do curl http://localhost:8080/products; sleep 1; done
# Atteso: 200 x 5 poi 429
```

#### Test GraphQL Depth Limiting

Con:
```env
GRAPHQL_DEPTH_LIMIT=7
```
Prova una query >7 livelli:  
```bash
curl -X POST http://localhost:4000/graphql -H "Content-Type: application/json" -d '{"query":"{ products { recommendations { recommendations { recommendations { recommendations { recommendations { id } } } } } } }"}'
# Atteso: 400 Bad Request "exceeds maximum operation depth"
```

#### Test Allowed Origins e payload WebSocket

Imposta in `.env`:
```
WS_ALLOWED_ORIGINS=http://localhost:3000
```
Prova connessione con wscat:
```bash
wscat -c ws://localhost:7070/ws -H "Origin: http://notallowed.com" # rifiutata
wscat -c ws://localhost:7070/ws -H "Origin: http://localhost:3000" # ok
```

---

## Test osservabilità

- Verifica log JSON e tracciamento:
  ```bash
  curl -H "X-Trace-ID: test-xxx" http://localhost:8080/products/1
  docker compose logs api-rest --tail=5 | grep test-xxx
  ```
- Health check: vedere stato e connessioni redis.

---

## Script utility

- **Reset prodotti:**
  ```bash
  curl -X POST http://localhost:8080/reset
  ```
- **ws-events consumer:**
  ```bash
  node scripts/ws-events-consumer.js
  ```
- **Report latency WebSocket:**
  ```bash
  node misurazioni/ws-latency.js | python scripts/ws-latency-report.py
  ```

---

## Variabili d'ambiente

| Variabile         | Default            | Descrizione                                        |
|-------------------|-------------------|----------------------------------------------------|
| `REDIS_URL`       | redis://redis:6379/0 | Redis per eventi                                   |
| `REST_BASE_URL`   | http://api-rest:8080 | URL REST per MCP                                   |
| `JWT_SECRET`      | *(vuoto)*         | Segreto JWT (abilita autenticazione)               |
| `RATE_LIMIT`      | 100/minute        | Limite rate REST                                   |
| `WS_ALLOWED_ORIGINS` | *              | Origini autorizzate WS                             |
| `WS_MAX_PAYLOAD`  | 1048576           | Massimo payload WS                                 |
| `LOW_STOCK_THRESHOLD` | 10            | Soglia di "low stock"                              |
| `GRAPHQL_DEPTH_LIMIT` | 10            | Profondità max query GraphQL                       |

---

## Architettura logica

```
┌───────────┐    ┌──────────────┐   ┌─────────┐
│  REST     │    │  GraphQL     │   │ WebSocket │
│  :8080    │    │  :4000       │   │  :7070    │
└────┬──────┘    └────▲─────────┘   └─────▲────┘
     │               │                     │
     │     pub/sub   │      eventi         │
     └─────────┬─────┴───────────┬─────────┘
               ▼                 ▼
           ���─────────┐      ┌──────────────┐
           │ Redis   │      │  mcp-host    │
           └─────────┘      └────┬─────────┘
                                 │
                          ┌──────▼────┐
                          │ MCP tool  │
                          └───────────┘
```

---

## Troubleshooting

| Problema            | Causa                               | Soluzione                           |
|---------------------|-------------------------------------|-------------------------------------|
| 401 Unauthorized    | JWT non inviato o scorretto         | Genera token, passa in header       |
| 403 Forbidden       | Viewer tenta PATCH/POST             | Usa token admin                     |
| 429 Too Many Req    | Rate limit superato                 | Attendi/min, alza RATE_LIMIT        |
| No WS events        | Redis/ws-events non up/down         | docker compose logs ws-events       |
| MCP host exit       | One-shot ok                         | docker compose logs mcp-host        |
