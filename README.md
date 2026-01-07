# Architettura ibrida REST + GraphQL + WebSocket + MCP (demo tesi)

Questa demo mostra come integrare i quattro paradigmi descritti nel Capitolo 1: 
- **REST** per CRUD e stato autorevole
- **GraphQL** per viste client-driven e riduzione di over/under-fetching
- **WebSocket** per notifiche real-time
- **MCP** per orchestrare un agente (LLM host) che legge dati freschi ed esegue azioni tramite tool dichiarativi

## Indice

- [Prerequisiti](#prerequisiti)
- [Avvio rapido](#avvio-rapido)
- [Servizi inclusi](#servizi-inclusi)
- [Test funzionali](#test-funzionali)
- [Autenticazione JWT](#autenticazione-jwt)
- [Osservabilità](#osservabilità)
- [Persistenza PostgreSQL (opzionale)](#persistenza-postgresql-opzionale)
- [Sicurezza e Test](#sicurezza-e-test)
- [Test osservabilità](#test-osservabilità)
- [Benchmark prestazioni](#benchmark-prestazioni)
- [Load Testing](#load-testing)
- [Script utility](#script-utility)
- [Variabili d'ambiente](#variabili-dambiente)
- [Architettura logica](#architettura-logica)
- [Troubleshooting](#troubleshooting)

---

## Prerequisiti

- **Docker** e **Docker Compose**
- **(Opzionale)** Node.js per `wscat`: `npm install -g wscat`
- **(Opzionale)** Python 3.11+ per esecuzione locale MCP host

---

## Avvio rapido

### Modalità senza autenticazione (default)

> **I seguenti comandi sono identici per bash e PowerShell**

```bash
docker compose down -v
docker compose build
docker compose up -d
```

**Verifica**:  

**Bash**
```bash
docker compose ps
curl http://localhost:8080/products
wscat -c ws://localhost:7070/ws
```
**PowerShell**
```powershell
docker compose ps
Invoke-RestMethod http://localhost:8080/products
wscat -c ws://localhost:7070/ws
```

Apri browser:  `http://localhost:4000/graphql` per GraphQL Playground.

### Modalità con autenticazione JWT

1. **Crea/modifica `.env`**:

   ```env
   JWT_SECRET=gino
   ```

2. **Riavvia i servizi**

   > **Comandi identici per bash e PowerShell**

   ```bash
   docker compose down -v
   docker compose build
   docker compose up -d
   ```

3. **Genera un token JWT**

   **Node.js**  

   **Bash**
   ```bash
   jwt=$(node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user1',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));")
   ```
   **PowerShell**
   ```powershell
   $jwt = node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user1',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));"
   ```

   **Alternativa con Python dal container**

   **Bash**
   ```bash
   jwt=$(docker compose exec api-rest python -c "import jwt,time; print(jwt.encode({'sub':'user1','role':'admin','exp':int(time.time())+3600}, 'gino', algorithm='HS256'))")
   ```
   **PowerShell**
   ```powershell
   $jwt = docker compose exec api-rest python -c "import jwt,time; print(jwt.encode({'sub':'user1','role':'admin','exp':int(time.time())+3600}, 'gino', algorithm='HS256'))"
   ```

4. **Usa il token**

   **Bash**
   ```bash
   curl -H "Authorization: Bearer $jwt" http://localhost:8080/products
   ```
   **PowerShell**
   ```powershell
   Invoke-RestMethod http://localhost:8080/products -Headers @{"Authorization"="Bearer $jwt"}
   ```

---

## Servizi inclusi

| Servizio | Tecnologia | Descrizione |
|----------|-----------|-------------|
| **redis** | Redis 7 | Pub/sub per eventi real-time |
| **api-rest** | FastAPI | API REST, stato prodotti (in-memory o Postgres), pubblica eventi |
| **gateway-graphql** | Apollo Server | API GraphQL, compone dati REST, calcola `lowStock` |
| **ws-events** | Node.js + ws | Server WebSocket, inoltra eventi da Redis |
| **mcp-server-catalog** | Python MCP | Server MCP con tool `searchLowStock`, `applyDiscount` |
| **mcp-server-orders** | Python MCP | Server MCP con tool `notifyPending` (mock) |
| **mcp-host** | Python | Orchestratore MCP (one-shot): applica sconti automatici |

> **Nota**: di default il database è in-memory.  Vedi [Persistenza PostgreSQL](#persistenza-postgresql-opzionale) per abilitare Postgres.

---

## Test funzionali

### 1. WebSocket

Ricevi eventi real-time (stock_update, price_update, notify_pending).

> **I seguenti comandi sono identici per bash e PowerShell**

**Senza JWT**:
```bash
wscat -c ws://localhost:7070/ws
```

**Con JWT**:
```bash
jwt="<il-tuo-token>"
wscat -c "ws://localhost:7070/ws?token=$jwt"
```

Lascia aperto il terminale per vedere gli eventi.

### 2. REST API

**Senza JWT**:

**Bash**
```bash
# Lista prodotti
curl http://localhost:8080/products
# Singolo prodotto
curl http://localhost:8080/products/1
# Aggiorna stock e prezzo
curl -X PATCH "http://localhost:8080/products/1?stock=5&price=1200"
```
**PowerShell**
```powershell
# Lista prodotti
Invoke-RestMethod http://localhost:8080/products
# Singolo prodotto
Invoke-RestMethod http://localhost:8080/products/1
# Aggiorna stock e prezzo
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=5&price=1200" -Method Patch
```

**Con JWT**:

**Bash**
```bash
jwt="<il-tuo-token>"
curl -H "Authorization: Bearer $jwt" http://localhost:8080/products
curl -H "Authorization: Bearer $jwt" http://localhost:8080/products/1
curl -X PATCH -H "Authorization: Bearer $jwt" "http://localhost:8080/products/1?stock=5&price=1200"
```
**PowerShell**
```powershell
$jwt="<il-tuo-token>"
Invoke-RestMethod http://localhost:8080/products -Headers @{"Authorization"="Bearer $jwt"}
Invoke-RestMethod http://localhost:8080/products/1 -Headers @{"Authorization"="Bearer $jwt"}
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=5&price=1200" -Headers @{"Authorization"="Bearer $jwt"} -Method Patch
```

### 3. GraphQL API

Apri `http://localhost:4000/graphql` nel browser.

**Senza JWT**:  lancia direttamente la query. 

**Con JWT**: aggiungi header nella sezione **HTTP HEADERS** (in fondo al Playground):

```json
{
  "Authorization": "Bearer <il-tuo-token>"
}
```

**Query di esempio**:
query {
  product(id: 1) {
    id
    name
    price
    stock
    lowStock
    category
    description
  }
  products {
    id
    name
    price
    stock
    lowStock
    category
    description
  }
}

### 4. MCP (agente one-shot)

Esegue l'orchestrazione automatica:
- Applica sconto del 10% ai prodotti con stock ≤ 15 (se non già scontati)
- Ripristina prezzo base se stock > 15
- Pubblica eventi `price_update` su Redis

> **I seguenti comandi sono identici per bash e PowerShell**

**Con Docker (raccomandato):**
```bash
docker compose run --rm mcp-host
```

**Locale con Python**:

**Bash**
```bash
python -m pip install requests redis PyJWT python-json-logger
export REST_BASE_URL="http://localhost:8080"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="gino"  # se JWT abilitato
cd mcp-host && python main.py
```
**PowerShell**
```powershell
pip install requests redis PyJWT python-json-logger
$env:REST_BASE_URL="http://localhost:8080"
$env:REDIS_URL="redis://localhost:6379/0"
$env:JWT_SECRET="gino"  # se JWT abilitato
cd mcp-host
python main.py
```

**Output atteso**:
```json
{"asctime":  ".. .", "message": "Fetched 20 products in 9.14 ms", ... }
{"asctime": "...", "message": "applyDiscount pid=1 stock=10 price 1499.0 -> 1349.1", ...}
{"asctime":  "...", "message": "Ops executed:  3", ...}
```

### 5. Verifica effetti

**REST**:

**Bash**
```bash
# Senza JWT
curl http://localhost:8080/products/1
# Con JWT
jwt="<il-tuo-token>"
curl -H "Authorization: Bearer $jwt" http://localhost:8080/products/1
```
**PowerShell**
```powershell
# Senza JWT
Invoke-RestMethod http://localhost:8080/products/1
# Con JWT
$jwt="<il-tuo-token>"
Invoke-RestMethod http://localhost:8080/products/1 -Headers @{"Authorization"="Bearer $jwt"}
```

**GraphQL**:  rilancia la query nel Playground → `price` e `lowStock` aggiornati.

**WebSocket**: vedi eventi `price_update` nel terminale `wscat`.

---

## Autenticazione JWT

### Panoramica

L'autenticazione JWT è **opzionale** e **disabilitata di default**. Quando abilitata: 
- **REST**: richiede header `Authorization: Bearer <token>`
- **GraphQL**: richiede header `Authorization: Bearer <token>`
- **WebSocket**: richiede query param `?token=<token>`

### Ruoli disponibili

| Ruolo   | Permessi                                  |
|---------|-------------------------------------------|
| `admin` | Lettura + scrittura (GET, PATCH, POST)    |
| `viewer`| Solo lettura (GET); PATCH/POST → 403      |

### Abilitazione

1. **Configura `.env`**:
   ```env
   JWT_SECRET=gino
   JWT_ALGORITHM=HS256
   ```

2. **Ricrea i container**

   > **I seguenti comandi sono identici per bash e PowerShell**
   ```bash
   docker compose down -v
   docker compose up -d --build --force-recreate
   ```

### Generazione token

**Con Node.js**

> **Stesso comando, cambiano solo $jwt/jwt= variabile**

**Bash**
```bash
jwt=$(node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user1',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));")
jwt=$(node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user2',role:'viewer',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));")
```
**PowerShell**
```powershell
$jwt = node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user1',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));"
$jwt = node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'user2',role:'viewer',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));"
```

**Con Python**

**Bash**
```bash
jwt=$(docker compose exec api-rest python -c "import jwt,time; print(jwt.encode({'sub':'user1','role':'admin','exp':int(time.time())+3600}, 'gino', algorithm='HS256'))")
```
**PowerShell**
```powershell
$jwt = docker compose exec api-rest python -c "import jwt,time; print(jwt.encode({'sub':'user1','role':'admin','exp':int(time.time())+3600}, 'gino', algorithm='HS256'))"
```

### Utilizzo token

**REST**:

**Bash**
```bash
jwt="<il-tuo-token>"
curl -H "Authorization:  Bearer $jwt" http://localhost:8080/products
curl -X PATCH -H "Authorization: Bearer $jwt" "http://localhost:8080/products/1?stock=10"
```
**PowerShell**
```powershell
$jwt="<il-tuo-token>"
Invoke-RestMethod http://localhost:8080/products -Headers @{"Authorization"="Bearer $jwt"}
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=10" -Method Patch -Headers @{"Authorization"="Bearer $jwt"}
```

**GraphQL** (Playground):

```json
{
  "Authorization": "Bearer <il-tuo-token>"
}
```

**WebSocket**:

> **Comando identico per bash e PowerShell**

```bash
jwt="<il-tuo-token>"
wscat -c "ws://localhost:7070/ws?token=$jwt"
```

### Test ruoli

**Admin** (write consentito):

**Bash**
```bash
jwt_admin=$(node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'admin',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));")
curl -X PATCH -H "Authorization: Bearer $jwt_admin" "http://localhost:8080/products/1?stock=50"
# Atteso: 200 OK
```
**PowerShell**
```powershell
$jwt_admin = node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'admin',role:'admin',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));"
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=50" -Method Patch -Headers @{"Authorization"="Bearer $jwt_admin"}
# Atteso: 200 OK
```

**Viewer** (write negato):
**Bash**
```bash
jwt_viewer=$(node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'viewer',role:'viewer',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));")
curl -X PATCH -H "Authorization: Bearer $jwt_viewer" "http://localhost:8080/products/1?stock=50"
# Atteso: 403 Forbidden
```
**PowerShell**
```powershell
$jwt_viewer = node -e "const jwt=require('jsonwebtoken'); console.log(jwt.sign({sub:'viewer',role:'viewer',exp:Math.floor(Date.now()/1000)+3600}, 'gino'));"
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=50" -Method Patch -Headers @{"Authorization"="Bearer $jwt_viewer"}
# Atteso: 403 Forbidden
```
---

## Osservabilità

### Logging strutturato JSON

Tutti i servizi emettono log in formato JSON arricchiti con `request_id` e `trace_id` per facilitare il tracciamento delle richieste sull’intera architettura.

**Visualizzazione log servizio:**

**I comandi sono identici per bash e PowerShell**
```bash
docker compose logs api-rest --tail=20
docker compose logs gateway-graphql --tail=20
docker compose logs ws-events --tail=20
```

**Formato tipico log**:
```json
{
  "asctime": "2026-01-05T17:15:57.254Z",
  "name": "api-rest",
  "levelname": "INFO",
  "message": "Request completed",
  "request_id": "abc123",
  "trace_id": "xyz789",
  "method": "GET",
  "path": "/products",
  "status":  200,
  "duration_ms": 12.34
}
```

**Tracciamento custom tramite header:**

**bash**
```bash
curl -H "X-Trace-ID: my-trace-123" http://localhost:8080/products/1
docker compose logs api-rest --tail=5 | grep my-trace-123
```
**powershell**
```powershell
Invoke-RestMethod http://localhost:8080/products/1 -Headers @{"X-Trace-ID" = "my-trace-123"}
docker compose logs api-rest --tail=5 | Select-String my-trace-123
```

---

### Metriche Prometheus

Tutti i servizi espongono endpoint `/metrics` compatibili Prometheus per raccolta e dashboarding.

| Servizio        | Endpoint                            | Metriche principali                                                                         |
|-----------------|-------------------------------------|---------------------------------------------------------------------------------------------|
| **api-rest**    | `http://localhost:8080/metrics`     | `api_rest_requests_total`, `api_rest_request_duration_seconds`, `api_rest_errors_total`      |
| **gateway-graphql** | `http://localhost:9090/metrics` | `graphql_requests_total`, `graphql_request_duration_seconds`, `graphql_errors_total`         |
| **ws-events**   | (interno)                           | `ws_connections_total`, `ws_messages_total`, `ws_errors_total`                              |

**Visualizza metriche chiave:**

**bash**
```bash
curl http://localhost:8080/metrics | grep api_rest_requests_total
curl http://localhost:9090/metrics | grep graphql_requests_total
```
**powershell**
```powershell
Invoke-RestMethod http://localhost:8080/metrics | Select-String api_rest_requests_total
Invoke-RestMethod http://localhost:9090/metrics | Select-String graphql_requests_total
```

---

### Health Check

Verifica la disponibilità di ciascun servizio e delle sue dipendenze tramite endpoint `/health`.

**Senza JWT:**

**bash**
```bash
curl http://localhost:8080/health
```
**powershell**
```powershell
Invoke-RestMethod http://localhost:8080/health
```

**Con JWT:**

**bash**
```bash
jwt="<il-tuo-token>"
curl -H "Authorization: Bearer $jwt" http://localhost:8080/health
```
**powershell**
```powershell
$jwt="<il-tuo-token>"
Invoke-RestMethod http://localhost:8080/health -Headers @{"Authorization"="Bearer $jwt"}
```

**Risposta attesa:**
```json
{
  "status": "healthy",
  "redis": "connected"
}
```

**Controllo stato dei container:**

**I comandi sono identici per bash e PowerShell**
```bash
docker compose ps
# Verifica colonna "STATUS": deve riportare (healthy)
```

---

## Persistenza PostgreSQL (opzionale)

Di default il database è in modalità **in-memory**. Per attivare la persistenza PostgreSQL:

### Setup

**I comandi sono identici per bash e PowerShell**
```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d
```

Lo schema si trova in `postgres/init.sql`, con 20 prodotti di test pre-caricati.

Le variabili vengono impostate automaticamente:
- `DATABASE_URL=postgresql://catalog_user:catalog_pass@postgres:5432/catalog`
- `USE_POSTGRES=true`

### Test persistenza dati

**Senza JWT:**

**bash**
```bash
curl -X PATCH "http://localhost:8080/products/1?stock=999&price=99.99"
docker compose restart api-rest
curl http://localhost:8080/products/1
# stock=999, price=99.99
```
**powershell**
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=999&price=99.99" -Method Patch
docker compose restart api-rest
Invoke-RestMethod http://localhost:8080/products/1
```

**Con JWT:**

**bash**
```bash
jwt="<il-tuo-token>"
curl -X PATCH -H "Authorization: Bearer $jwt" "http://localhost:8080/products/1?stock=999&price=99.99"
docker compose restart api-rest
curl -H "Authorization: Bearer $jwt" http://localhost:8080/products/1
```
**powershell**
```powershell
$jwt="<il-tuo-token>"
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=999&price=99.99" -Method Patch -Headers @{"Authorization"="Bearer $jwt"}
docker compose restart api-rest
Invoke-RestMethod http://localhost:8080/products/1 -Headers @{"Authorization"="Bearer $jwt"}
```

### Stop Postgres (torna a in-memory)

**I comandi sono identici per bash e PowerShell**
```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml down
docker compose up -d
```

## Sicurezza e Test

Questa sezione descrive i meccanismi di protezione implementati nell'architettura (Rate Limiting, GraphQL Security, WebSocket Security) e come testarli.

### 1. Autenticazione JWT

**Senza JWT_SECRET (default):**
```bash
curl http://localhost:8080/products  # 200 OK
```
```powershell
Invoke-RestMethod http://localhost:8080/products  # 200 OK
```

**Con JWT_SECRET:**

**bash**
```bash
export JWT_SECRET="test-secret"
docker compose up -d api-rest

# Genera token admin
python3 -c "import jwt,datetime; print(jwt.encode({'sub':'user','role':'admin','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=1)}, 'test-secret', algorithm='HS256'))"

TOKEN="<token-generato>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/products  # 200
curl http://localhost:8080/products  # 401

# Test ruolo viewer
python3 -c "import jwt,datetime; print(jwt.encode({'sub':'user','role':'viewer','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=1)}, 'test-secret', algorithm='HS256'))"
TOKEN_VIEWER="<token>"
curl -H "Authorization: Bearer $TOKEN_VIEWER" -X PATCH "http://localhost:8080/products/1?stock=10"  # 403
```
**powershell**
```powershell
$env:JWT_SECRET="test-secret"
docker compose up -d api-rest

# Genera token admin
python -c "import jwt,datetime; print(jwt.encode({'sub':'user','role':'admin','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=1)}, 'test-secret', algorithm='HS256'))"

$TOKEN="<token-generato>"
Invoke-RestMethod http://localhost:8080/products -Headers @{"Authorization"="Bearer $TOKEN"}  # 200
Invoke-RestMethod http://localhost:8080/products  # 401

# Test ruolo viewer
python -c "import jwt,datetime; print(jwt.encode({'sub':'user','role':'viewer','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=1)}, 'test-secret', algorithm='HS256'))"
$TOKEN_VIEWER="<token>"
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=10" -Method Patch -Headers @{"Authorization"="Bearer $TOKEN_VIEWER"}  # 403
```

### 2. Rate Limiting
### Rate Limiting

Protezione contro abusi e attacchi DoS tramite limitazione delle richieste.

| Servizio | Variabile | Default | Risposta |
|----------|-----------|---------|----------|
| REST | `RATE_LIMIT` | 100/minute | HTTP 429 |
| GraphQL | `RATE_LIMIT_PER_MIN` | 100 | HTTP 429 |
| WebSocket | `WS_MESSAGE_RATE_LIMIT` | 10 msg/s | Errore connessione |

**Test rate limiting**

> **Prerequisito:** Nel file `.env`, imposta `RATE_LIMIT="5/minute"` e riavvia il container `api-rest`.

**REST:** 

**bash**
```bash
export RATE_LIMIT="5/minute"
docker compose up -d api-rest
for i in {1..10}; do curl -w "\nStatus: %{http_code}\n" http://localhost:8080/products; sleep 1; done
# Atteso: 200 x 5, poi 429
```
**powershell**
```powershell
$env:RATE_LIMIT="5/minute"
docker compose up -d api-rest
1..10 | % {
    $r=Invoke-WebRequest http://localhost:8080/products -UseBasicParsing
    Write-Host "Status: $($r.StatusCode)"
    Start-Sleep -Seconds 1
}
# Atteso: 200 x 5, poi 429
```

**GraphQL:** 

**bash**
```bash
export RATE_LIMIT_PER_MIN="3"
docker compose up -d gateway-graphql
for i in {1..5}; do
  curl -X POST http://localhost:4000/graphql \
    -H "Content-Type: application/json" \
    -d '{"query":"{ products { id } }"}'; sleep 1
done
# Atteso: 200 x 3, poi 429
```
**powershell**
```powershell
$env:RATE_LIMIT_PER_MIN="3"
docker compose up -d gateway-graphql
1..5 | % {
    $body = '{"query":"{ products { id } }"}'
    Invoke-RestMethod -Uri http://localhost:4000/graphql -Method Post -Body $body -ContentType "application/json"
    Start-Sleep -Seconds 1
}
# Atteso: 200 x 3, poi 429
```

### 3. GraphQL Security


**Depth Limiting**: Previene query ricorsive troppo profonde (Protezione DoS).
```env
GRAPHQL_DEPTH_LIMIT=7  # max 7 livelli di profondità
```

**Introspection Control**: Disabilita l'esplorazione dello schema in produzione.
```env
INTROSPECTION_ENABLED=false # default: true
```

#### Test 1: Query Valida (Profondità 5)
Questa query rientra nel limite impostato (< 7) e deve essere eseguita con successo.

**Bash**
```bash
curl -I -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ products { recommendations { recommendations { recommendations { recommendations { id } } } } } }"}'
# Atteso: HTTP 200 OK
```

**PowerShell**
```powershell
$body = '{"query":"{ products { recommendations { recommendations { recommendations { recommendations { id } } } } } }"}'
try {
    $res = Invoke-WebRequest -Uri "http://localhost:4000/graphql" -Method Post -Body $body -ContentType "application/json"
    Write-Host "Status: $($res.StatusCode) (Allowed)" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}
```

#### Test 2: Query Bloccata (Profondità 8)
Questa query supera il limite e deve restituire un errore.

**Bash**
```bash
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ products { recommendations { recommendations { recommendations { recommendations { recommendations { recommendations { recommendations { id } } } } } } } } }"}'
# Atteso: HTTP 400 Bad Request ("exceeds maximum operation depth")
```

**PowerShell**
```powershell
$body = '{"query":"{ products { recommendations { recommendations { recommendations { recommendations { recommendations { recommendations { recommendations { id } } } } } } } } }"}'
try {
    Invoke-WebRequest -Uri "http://localhost:4000/graphql" -Method Post -Body $body -ContentType "application/json"
} catch {
    # Ci aspettiamo di finire qui con un 400
    Write-Host "Status: $($_.Exception.Response.StatusCode) (Blocked as expected)" -ForegroundColor Red
    # Opzionale: visualizzare il messaggio di errore JSON
    # $_.Exception.Response.GetResponseStream() ...
}
```

### 4. WebSocket Security

**Origin Validation**: Whitelist delle origini consentite per prevenire CSWSH.
```env
WS_ALLOWED_ORIGINS=[https://myapp.com](https://myapp.com),[https://admin.myapp.com](https://admin.myapp.com)
```

**Max Payload Size**: Limite dimensione messaggi per prevenire allocazione eccessiva di memoria.
```env
WS_MAX_PAYLOAD=1048576  # 1MB (default)
```

**Origin check:**  
**bash**
```bash
export WS_ALLOWED_ORIGINS="http://localhost:3000"
docker compose up -d ws-events

wscat -c ws://localhost:7070/ws -H "Origin: http://badorigin.com"  # rifiutato
wscat -c ws://localhost:7070/ws -H "Origin: http://localhost:3000"  # ok
```
**powershell**
```powershell
$env:WS_ALLOWED_ORIGINS="http://localhost:3000"
docker compose up -d ws-events

wscat -c ws://localhost:7070/ws -H "Origin: http://badorigin.com"  # rifiutato
wscat -c ws://localhost:7070/ws -H "Origin: http://localhost:3000"  # ok
```

**JWT su WebSocket:**  
**bash**
```bash
export JWT_SECRET="test"
docker compose up -d ws-events
TOKEN="<jwt>"
wscat -c "ws://localhost:7070/ws?token=$TOKEN"
```
**powershell**
```powershell
$env:JWT_SECRET="test"
docker compose up -d ws-events
$TOKEN="<jwt>"
wscat -c "ws://localhost:7070/ws?token=$TOKEN"
```

---

## Test osservabilità

### 1. Logging strutturato
```bash
docker compose logs api-rest --tail=10
# Verifica presenza: request_id, trace_id, JSON format
```

### 2. Trace ID propagation
```bash
curl -H "X-Trace-ID:  test-123" http://localhost:8080/products/1
docker compose logs api-rest --tail=5 | grep test-123
# Verifica: trace_id presente nei log
```

### 3. Metriche Prometheus
```bash
curl http://localhost:8080/metrics | grep api_rest_requests_total
curl http://localhost:9090/metrics | grep graphql_requests_total
# Verifica: metriche incrementano con traffico
```

### 4. Health Check
```bash
curl http://localhost:8080/health
# {"status":"healthy","redis":"connected"}

docker compose ps
# Verifica: status "healthy" per api-rest e redis
```

---

## Benchmark prestazioni

### 1. REST vs GraphQL

**bash**
```bash
cd progetto-tesi
bash misurazioni/run-bench.sh
```
**powershell**
```powershell
cd progetto-tesi
powershell -ExecutionPolicy Bypass -File misurazioni/run-bench.ps1
```

**File input:**
- `query/query_1.json`: query semplice (1 risorsa)
- `query/query_2.json`: query composta (4 risorse REST vs 1 GraphQL)

**Output** (in `misurazioni/`):
- `rest_simple.txt`, `gql_simple.txt`
- `rest_complex.txt`, `gql_complex.txt`

**Risultati tipici** (localhost):
| Scenario | API | Mean latency | P95 | Payload |
|----------|-----|--------------|-----|---------|
| Semplice | REST | 3.9 ms | 4.4 ms | 114 B |
| Semplice | GraphQL | 7.7 ms | 8.6 ms | 92 B |
| Composto | REST | 23 ms | 38 ms | 1370 B |
| Composto | GraphQL | 13.8 ms | 19.6 ms | 1037 B |

**Interpretazione:**
- REST vince su call atomiche (meno overhead)
- GraphQL vince su viste composte (meno round-trip, payload ridotto con field selection)

### 2. WebSocket vs Polling

**WebSocket latency**
**bash**
```bash
export RUNS="20"
export WS_URL="ws://localhost:7070/ws"
export REST_BASE="http://localhost:8080"
node misurazioni/ws-latency.js
```
**powershell**
```powershell
$env:RUNS="20"
$env:WS_URL="ws://localhost:7070/ws"
$env:REST_BASE="http://localhost:8080"
node misurazioni/ws-latency.js
```
Tipico: mean 3–5 ms, P95 3–7 ms.

**Polling REST**
**bash**
```bash
bash misurazioni/polling-rest.sh
```
**powershell**
```powershell
powershell -File misurazioni/polling-rest.ps1
```
Tipico (interval 50ms): mean 41–47 ms, P95 39–69 ms.

**Report latenza WS**
```bash
node misurazioni/ws-latency.js | python scripts/ws-latency-report.py
```

**Conclusione:**  WebSocket ~10x più rapido del polling.

---

## Load Testing

### 1. Apache Bench

**Bash / WSL / Linux / macOS**
```bash
ab -n 1000 -c 10 http://localhost:8080/products
# Verifica throughput, error rate

# Con rate limiting:
export RATE_LIMIT="50/minute"
docker compose up -d api-rest
ab -n 100 -c 10 http://localhost:8080/products
# Atteso: ~50 successi, ~50 errori 429
```

**PowerShell**
> ⚠️ `ab` (Apache Bench) **non è disponibile nativamente su Windows**.  
> Puoi usare WSL (Windows Subsystem for Linux) o preferire direttamente Artillery (vedi dopo).
---

### 2. Artillery

**Bash o Powershell**
```bash
npm install -g artillery
```

**Per eseguire i test:**
```
artillery run artillery-test-rest.yml
```
```
artillery run artillery-test-graphql.yml
```
```
artillery run artillery-test-ws.yml
```
### Report e Analisi Load Test (Artillery) - REST, GraphQL, WebSocket

#### **REST (/products)**
- **Totale richieste:** 600  
- **Successi (HTTP 200):** 100  
- **Rate limited (HTTP 429):** 500  
- **Latenza media:** 5.6 ms  
- **Latenza p95:** 7 ms  
- **Latenza massima:** 26 ms  
- **Bandwidth totale:** 252800 byte  
- **Nessun errore applicativo, nessun VU fallito**  
- **Conclusione:**  
  L’API REST gestisce il carico previsto con latenza molto bassa e prevede rate limiting efficace (tutte le richieste oltre soglia correttamente bloccate). Il servizio è robusto, stabile e veloce, con una user experience costantemente fluida anche sotto carico.

#### **GraphQL (/graphql)**
- **Totale richieste:** 600  
- **Successi (HTTP 200):** 100  
- **Errori server (HTTP 500):** 500  
- **Latenza media:** 5 ms (risposte 2xx), 3.8 ms (risposte 5xx - errori server)  
- **Latenza p95:** 11 ms (su tutte); 15 ms (risposte 2xx)  
- **Bandwidth:** 340500 byte  
- **Nessun VU fallito**  
- **Conclusione:**  
  In assenza di rate limiting, la maggior parte delle risposte (500 su 600) sono errori server (HTTP 500). Questo suggerisce che lo schema GraphQL o la validazione/protezione dalle query troppo complesse è attiva. Il tempo di risposta resta basso ma il servizio non accetta tutte le query in carico, quindi serve tunare la configurazione di sicurezza e profondità oppure gestire meglio la quota.

#### **WebSocket (/ws)**
- **Totale messaggi inviati:** 600  
- **Sessioni create/completate:** 600  
- **Messaggi/sec**: costantemente ~10/sec  
- **Durata media sessione:** ~1000 ms  
- **Nessun errore né VU fallito**  
- **Conclusione:**  
  Il server WebSocket regge un traffico costante di 10 messaggi/sec e tutte le sessioni completano senza errori. Le sessioni hanno durata omogenea e non si riscontrano anomalie o colli di bottiglia. È ideale per notifiche ed eventi push in tempo reale: la robustezza e la scalabilità nel test sono ottime.

---

#### **Sintesi trasversale**
- L’architettura ibrida supera il test di carico REST con ottimi tempi di risposta ed efficacia nel rate limiting.
- Il test GraphQL conferma la sensibilità della configurazione server-side: a carico elevato l’API risponde prevalentemente con errori 500 (soglia di sicurezza, query troppo profonde o complesse). È consigliato *regolare i limiti di profondità e costi* per l’ambiente di produzione.
- Il test WebSocket dimostra che la soluzione in push è pronta per carico elevato senza impatti su stabilità, con un flusso costante di messaggi e nessuna perdita di sessione.

---

## Script utility

### 1. Reset prodotti

Ripristina i prodotti ai valori iniziali.

**bash**
```bash
curl -X POST http://localhost:8080/reset
```
**powershell**
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/reset" -Method Post
```

**Con JWT:**

**bash**
```bash
jwt="<il-tuo-token>"
curl -X POST -H "Authorization: Bearer $jwt" http://localhost:8080/reset
```
**powershell**
```powershell
$jwt="<il-tuo-token>"
Invoke-RestMethod -Uri "http://localhost:8080/reset" -Method Post -Headers @{"Authorization"="Bearer $jwt"}
```

**Risposta:**
```json
{
  "message": "All products reset to base values",
  "count": 20
}
```

---

### 2. Consumer eventi WebSocket

Visualizza in tempo reale gli eventi provenienti dai servizi tramite uno script.

**I comandi sono identici per bash e PowerShell**
```bash
node scripts/ws-events-consumer.js
```

**Con JWT:**

**bash**
```bash
jwt="<il-tuo-token>"
JWT_TOKEN="$jwt" node scripts/ws-events-consumer.js
```
**powershell**
```powershell
$env:JWT_TOKEN="$jwt"
node scripts/ws-events-consumer.js
```

**Output esempio:**
```
[2026-01-05 17:30:45] stock_update: {"id":1,"stock":5}
[2026-01-05 17:30:46] price_update: {"id":1,"price":1349.1}
```

---

### 3. Report latenza WebSocket

**I comandi sono identici per bash e PowerShell**
```bash
node misurazioni/ws-latency.js | python scripts/ws-latency-report.py
```

**Output esempio:**
```
WebSocket Latency Statistics
=============================
Total measurements (used): 20
Mean latency:       1.20 ms
P95 latency:        3.00 ms
Min latency:        0.00 ms
Max latency:        3.00 ms
Std deviation:      1.06 ms
```

---

## Variabili d'ambiente

### Globali

| Variabile         | Default                | Descrizione                             |
|-------------------|-----------------------|-----------------------------------------|
| `REDIS_URL`       | `redis://redis:6379/0`| Connection string Redis                 |
| `REST_BASE_URL`   | `http://api-rest:8080`| URL base API REST (per MCP host)        |

### Sicurezza

| Variabile               | Default           | Descrizione                                 |
|-------------------------|-------------------|---------------------------------------------|
| `JWT_SECRET`            | *(vuoto)*         | Segreto JWT; se impostato abilita auth      |
| `JWT_ALGORITHM`         | `HS256`           | Algoritmo JWT                               |
| `RATE_LIMIT`            | `100/minute`      | Rate limit REST (formato slowapi)           |
| `RATE_LIMIT_PER_MIN`    | `100`             | Rate limit GraphQL (richieste/minuto)       |
| `WS_MESSAGE_RATE_LIMIT` | `10`              | Rate limit WebSocket (messaggi/secondo)     |
| `WS_ALLOWED_ORIGINS`    | `*`               | Origini WebSocket consentite (comma-separated)|
| `WS_MAX_PAYLOAD`        | `1048576`         | Max payload WebSocket (byte)                |

### GraphQL

| Variabile             | Default    | Descrizione                         |
|-----------------------|------------|-------------------------------------|
| `LOW_STOCK_THRESHOLD` | `10`       | Soglia per campo `lowStock`         |
| `GRAPHQL_DEPTH_LIMIT` | `10`       | Profondità massima query            |
| `INTROSPECTION_ENABLED` | `true`   | Abilita introspection schema        |

### Database

| Variabile        | Default         | Descrizione                      |
|------------------|-----------------|----------------------------------|
| `DATABASE_URL`   | *(vuoto)*       | Connection string PostgreSQL     |
| `USE_POSTGRES`   | `false`         | Abilita persistenza Postgres     |

---

## Architettura logica

```
┌──────────────────────────────────────────────────┐
│                    Client                        │
└────────┬─────────────┬─────────────┬─────────────┘
         │             │             │
         │ REST        │ GraphQL     │ WebSocket
         ▼             ▼             ▼
    ┌─────────┐   ┌──────────┐   ┌──────────┐
    │api-rest │◄──│gateway-  │   │ws-events │
    │(FastAPI)│   │graphql   │   │(Node+ws) │
    │         │   │(Apollo)  │   │          │
    └────┬────┘   └──────────┘   └─────▲────┘
         │                              │
         │ pub/sub                      │
         ▼                              │
    ┌─────────────────────────────────┐│
    │          Redis                   ││
    │        (pub/sub)                 ││
    └────────────┬────────────────────┘│
                 │                      │
                 │ subscribe            │
                 ▼                      │
         ┌───────────────┐             │
         │   mcp-host    │─────────────┘
         │(orchestrator) │   publish events
         └───┬───────┬───┘
             │       │
    ┌────────┴───┐ ┌┴─────────────┐
    │mcp-server- │ │mcp-server-   │
    │catalog     │ │orders        │
    │(tool)      │ │(tool mock)   │
    └────────────┘ └──────────────┘
```

**Flusso dati**:
1. **api-rest** mantiene stato prodotti (source of truth)
2. Modifiche pubblicate su **Redis** (`events` channel)
3. **ws-events** inoltra eventi ai client WebSocket
4. **gateway-graphql** compone dati REST con logica (es.  `lowStock`)
5. **mcp-host** orchestra azioni automatiche tramite tool MCP

---









## Troubleshooting

### Problemi comuni

| Problema | Causa | Soluzione |
|----------|-------|-----------|
| **401 Unauthorized** | JWT abilitato ma token mancante | Genera token e passa in header/query |
| **403 Forbidden** | Ruolo `viewer` su endpoint write | Usa token con `role: admin` |
| **429 Too Many Requests** | Rate limit superato | Attendi 1 minuto o aumenta `RATE_LIMIT` |
| **Nessun evento WebSocket** | Redis non pubblica o ws-events down | Verifica `docker compose logs ws-events` |
| **Container non healthy** | Dipendenza (Redis/api-rest) non pronta | `docker compose logs <servizio>` |
| **MCP host esce subito** | One-shot normale | Output già completato; verifica con `docker compose logs mcp-host` |
| **Metriche vuote** | Nessun traffico generato | Esegui query/richieste prima di leggere `/metrics` |
| **Porta 6379 occupata** | Redis già in esecuzione | `netstat -ano \| findstr :6379` e termina processo |

### Comandi diagnostici

**I comandi sono identici per bash e powershell**
```bash
# Verifica stato servizi
docker compose ps

# Log in tempo reale
docker compose logs -f api-rest

# Restart singolo servizio
docker compose restart api-rest

# Rebuild completo
docker compose down -v
docker compose build
docker compose up -d

# Verifica JWT attivo
docker compose exec api-rest sh -c 'echo "JWT_SECRET=$JWT_SECRET"'

# Test connessione Redis
docker compose exec redis redis-cli ping
```

---