
# Architettura ibrida REST + GraphQL + WebSocket + MCP (demo tesi)

Questa demo mostra come integrare e confrontare i quattro principali paradigmi di comunicazione moderni:
- **REST**: per operazioni CRUD e gestione dello stato autorevole dei dati
- **GraphQL**: per viste client-driven e riduzione di over/under-fetching
- **WebSocket**: per notifiche real-time e comunicazione bidirezionale
- **MCP**: per orchestrare un agente (LLM host) che legge dati freschi ed esegue azioni tramite tool dichiarativi

L’obiettivo è fornire un’architettura di riferimento, facilmente testabile e osservabile, per confrontare prestazioni, flessibilità e limiti di ciascun modello, sia lato server che lato client.


## Indice


- [Prerequisiti](#prerequisiti)
- [Preparazione ambiente](#preparazione-ambiente)
- [Avvio rapido](#avvio-rapido)
- [Servizi inclusi](#servizi-inclusi)
- [Funzionamento dettagliato](#funzionamento-dettagliato)
- [Test funzionali (API e orchestrazione)](#test-funzionali-api-e-orchestrazione)
- [Dashboard frontend](#dashboard-frontend)
- [Testing](#testing)
- [Osservabilità](#osservabilita)
- [Rate Limiting](#rate-limiting)
- [GraphQL: Depth Limiting](#graphql-depth-limiting)
- [WebSocket Security](#websocket-security)
- [Script utility](#script-utility)
- [Variabili d'ambiente](#variabili-dambiente)
- [Problemi comuni](#problemi-comuni)
- [Comandi diagnostici](#comandi-diagnostici)


---


## Prerequisiti

- **Docker** e **Docker Compose**
- **Node.js** (per wscat, artillery, dashboard)
- **Python 3.11+** (opzionale: test locali, MCP host)


---

## Preparazione ambiente

### 1. Clona la repo

```bash
git clone https://github.com/LolloMaolons/progetto-tesi-lorenzo-maoloni.git
cd progetto-tesi-lorenzo-maoloni
```

### 2. Installa Artillery

```bash
npm install -g artillery
```

### 3. Installa wscat

```bash
npm install -g wscat
```
---


## Avvio rapido

Esegui questi comandi (identici per Bash e PowerShell):

```bash
docker compose down -v
docker compose build
docker compose up -d
```

Apri nel browser:
- `http://localhost:4000/graphql` per GraphQL Playground
- `http://localhost:5173` per la dashboard frontend (vedi sezione dedicata)


---


## Servizi inclusi

| Servizio              | Tecnologia         | Descrizione                                                                 |
|-----------------------|-------------------|----------------------------------------------------------------------------|
| **redis**             | Redis 7           | Pub/sub per eventi real-time                                                |
| **api-rest**          | FastAPI           | API REST, stato prodotti (in-memory o Postgres), pubblica eventi            |
| **gateway-graphql**   | Apollo Server     | API GraphQL, compone dati REST, calcola `lowStock`                          |
| **ws-events**         | Node.js + ws      | Server WebSocket, inoltra eventi da Redis                                   |
| **mcp-server-catalog**| Python MCP        | Server MCP con tool `searchLowStock`, `applyDiscount`                       |
| **mcp-server-orders** | Python MCP        | Server MCP con tool `notifyPending` (mock)                                  |
| **mcp-host**          | Python LLM/MCP    | Orchestratore MCP/LLM: applica sconti automatici, tool batch, azioni agent  |
| **dashboard**         | React + Vite      | Frontend per test funzionali e visualizzazione dati                         |

> **Nota**: di default il database è in-memory.


---


## Funzionamento dettagliato e orchestrazione LLM

L’architettura è composta da microservizi che comunicano tramite REST, GraphQL, WebSocket e MCP. Tutti i servizi sono containerizzati e orchestrati tramite Docker Compose. Le modifiche ai dati (prodotti) vengono propagate in tempo reale tramite eventi Redis e WebSocket. La dashboard frontend consente di testare e confrontare i paradigmi direttamente da interfaccia grafica, mentre tutti i servizi espongono endpoint per test funzionali e raccolta metriche.

**Flusso dati tipico:**
1. Il client (dashboard o CLI) effettua richieste REST, GraphQL o WebSocket.
2. Le modifiche ai prodotti sono gestite da api-rest e propagate tramite Redis.
3. ws-events inoltra gli eventi ai client WebSocket.
4. gateway-graphql compone dati REST e logica custom.
5. mcp-host e i server MCP/LLM orchestrano azioni batch, tool automatici e agenti LLM.

---

Questa architettura supporta diversi tipi di test, tutti raccolti in questa sezione:

### Test funzionali (API, orchestrazione MCP/LLM e rate limiting)
**MCP/LLM (agente one-shot e tool JSON-RPC)**

L’agente MCP/LLM esegue:
- Sconti automatici su prodotti low stock
- Ripristino prezzi su prodotti high stock
- Notifiche batch
- Orchestrazione tramite tool JSON-RPC

**Esempi di test MCP/LLM:**
```bash
curl -X POST http://localhost:5000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"discountAllLowStock","params":{"discount":10,"threshold":15}}'
```
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/rpc" -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"discountAllLowStock","params":{"discount":10,"threshold":15}}'
```

### Test rate limiting REST/GraphQL

Script Python `scripts/test-5-rate-limiting.py`:
- Esegue 25 richieste REST e GraphQL
- Mostra chiaramente 10 risposte 200 e 15 risposte 429 (REST), 9 risposte 200 e 16 risposte 429 (GraphQL)
- Dimostra l’efficacia del rate limit

**Esecuzione:**
```bash
python scripts/test-5-rate-limiting.py
```
**Output:**
File `risultati-misurazioni/test-5-rate-limiting.json` con statistiche dettagliate

### Test orchestrazione MCP/LLM

Script Python e tool JSON-RPC permettono di testare l’agente MCP/LLM:
- Sconti automatici
- Ripristino prezzi
- Notifiche batch

**Esecuzione:**
```bash
python scripts/test-8-mcp-llm-orchestration.py
```
**Output:**
File `risultati-misurazioni/test-8-mcp-llm-orchestration.json` con risultati delle azioni LLM


**WebSocket**

Ricevi eventi real-time (stock_update, price_update, notify_pending):

**Comandi identici per Bash e Powershell**
```bash
wscat -c ws://localhost:7070/ws
```

**REST API**

**Bash**
```bash
# Lista prodotti
curl http://localhost:8080/products
```

```bash
# Singolo prodotto
curl http://localhost:8080/products/1
```

```bash
# Aggiorna stock e prezzo
curl -X PATCH "http://localhost:8080/products/1?stock=5&price=1200"
```
```bash
# Ripristina i prodotti ai valori iniziali.
curl -X POST http://localhost:8080/reset
```

**PowerShell**

```powershell
# Lista prodotti
Invoke-RestMethod http://localhost:8080/products
```

```powershell
# Singolo prodotto
Invoke-RestMethod http://localhost:8080/products/1
```

```powershell
# Aggiorna stock e prezzo
Invoke-RestMethod -Uri "http://localhost:8080/products/1?stock=5&price=1200" -Method Patch
```

```powershell
# Ripristina i prodotti ai valori iniziali.
Invoke-RestMethod -Uri "http://localhost:8080/reset" -Method Post
```

**GraphQL API**

Apri `http://localhost:4000/graphql` nel browser e lancia la query:

```graphql
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
```

**MCP (agente one-shot)**

Esegue l'orchestrazione automatica:
- Applica sconto del 10% ai prodotti con stock ≤ 25 (se non già scontati)
- Ripristina prezzo base se stock > 25
- Pubblica eventi `price_update` su Redis

**Funzioni MCP tool (JSON-RPC):**

- Sconto su tutti i prodotti low stock:
  **Bash**
  ```bash
  curl -X POST http://localhost:5000/rpc -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"discountAllLowStock","params":{"discount":10,"threshold":15}}'
  ```
  **PowerShell**
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:5000/rpc" -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"discountAllLowStock","params":{"discount":10,"threshold":15}}'
  ```
- Ripristino prezzo solo dei prodotti high stock:
  **Bash**
  ```bash
  curl -X POST http://localhost:5000/rpc -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"resetAllHighStock","params":{"threshold":15}}'
  ```
  **PowerShell**
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:5000/rpc" -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"resetAllHighStock","params":{"threshold":15}}'
  ```


---


## Dashboard frontend: test paradigmi e orchestrazione LLM

La dashboard (cartella `dashboard/`) è un frontend React che permette di:
 - Testare tutte le API (REST, GraphQL, WebSocket, MCP/LLM) da interfaccia grafica
 - Visualizzare risposte, metriche e confronti tra paradigmi
 - Salvare e ripetere richieste di test
 - Orchestrare azioni MCP/LLM direttamente dal frontend
- Testare tutte le API (REST, GraphQL, WebSocket, MCP) da interfaccia grafica
- Visualizzare risposte, metriche e confronti tra paradigmi
- Salvare e ripetere richieste di test

**Avvio dashboard:**
```bash
cd dashboard
npm install
npm run dev
```
Apri il browser su `http://localhost:5173`


---


## TESTING

### Analisi sperimentale: tutti gli script di test

La cartella `scripts/` contiene tutti gli script Python e PowerShell usati per l’analisi sperimentale e il confronto tra paradigmi. Ogni script genera un file di output in `risultati-misurazioni/`.

**Elenco script principali:**

- `test-1-rest-vs-graphql-simple.py`: confronto REST vs GraphQL su query semplice
- `test-2-rest-vs-graphql-composite.py`: confronto REST vs GraphQL su query composta
- `test-3-bandwidth-field-selection.py`: analisi payload e selezione campi GraphQL
- `test-4-websocket-vs-polling.py`: confronto latenza WebSocket vs polling REST
- `test-5-rate-limiting.py`: test dimostrativo rate limiting REST/GraphQL (HTTP 429)
- `test-6-websocket-concurrent.py`: test carico e concorrenza su WebSocket
- `test-7-mcp-direct.py`: test tool MCP diretti (JSON-RPC)
- `test-8-mcp-llm-orchestration.py`: orchestrazione automatica MCP/LLM (sconti, azioni batch)
- `test-9-redis-failover.ps1`: test resilienza Redis e failover eventi
- `test-10-prometheus-metrics.ps1`: raccolta e analisi metriche Prometheus
- `test-11-trace-id-logging.ps1`: verifica tracciamento distribuito e logging
- `run-all-tests.ps1`: esecuzione batch di tutti i test

**Esecuzione tipica:**
```bash
python scripts/test-1-rest-vs-graphql-simple.py
python scripts/test-2-rest-vs-graphql-composite.py
python scripts/test-3-bandwidth-field-selection.py
python scripts/test-4-websocket-vs-polling.py
python scripts/test-5-rate-limiting.py
python scripts/test-6-websocket-concurrent.py
python scripts/test-7-mcp-direct.py
python scripts/test-8-mcp-llm-orchestration.py
```
**PowerShell:**
```powershell


**Output:**
Tutti i risultati sono salvati in `risultati-misurazioni/` e includono statistiche su latenza, errori, payload, efficacia rate limit, orchestrazione MCP/LLM, failover e logging.

**Dashboard:**
La dashboard React consente di visualizzare e confrontare i risultati dei test, orchestrare azioni MCP/LLM e analizzare metriche in tempo reale.

**Note:**
- Tutti gli script sono documentati nei commenti e nel README.
- I test sono pensati per essere riproducibili e confrontabili tra paradigmi.


## Osservabilità

Tutti i servizi emettono log strutturati in JSON con `request_id` e `trace_id` per il tracciamento distribuito.

**Visualizzazione log servizio:**
```bash
docker compose logs api-rest --tail=20
docker compose logs gateway-graphql --tail=20
docker compose logs ws-events --tail=20
```

**Esempio di log:**
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

**Bash**
```bash
curl -H "X-Trace-ID: my-trace-123" http://localhost:8080/products/1
docker compose logs api-rest --tail=5 | grep my-trace-123
```

**PowerShell**
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/products/1" -Headers @{"X-Trace-ID"="my-trace-123"}
docker compose logs api-rest --tail=5 | Select-String my-trace-123
```

### Health Check

Verifica la disponibilità di ciascun servizio e delle sue dipendenze tramite endpoint `/health`.

**Bash**
```bash
curl http://localhost:8080/health
```
**PowerShell**
```powershell
Invoke-RestMethod http://localhost:8080/health
```

**Risposta attesa:**
```json
{
  "status": "healthy",
  "redis": "connected"
}
```

**Controllo stato dei container:**


```bash
docker compose ps
```


---


## Rate Limiting

Protezione contro abusi e attacchi DoS tramite limitazione delle richieste.

| Servizio | Variabile | Default | Risposta |
|----------|-----------|---------|----------|
| REST | `RATE_LIMIT` | 100/minute | HTTP 429 |
| GraphQL | `RATE_LIMIT_PER_MIN` | 100 | HTTP 429 |
| WebSocket | `WS_MESSAGE_RATE_LIMIT` | 10 msg/s | Errore connessione |


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


---


## GraphQL: Depth Limiting

Previene query ricorsive troppo profonde (Protezione DoS).

```env
GRAPHQL_DEPTH_LIMIT=7  # max 7 livelli di profondità
```

**Introspection Control**: Disabilita l'esplorazione dello schema in produzione.
```env
INTROSPECTION_ENABLED=false # default: true
```

### Test 1: Query Valida (Profondità 5)
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

### Test 2: Query Bloccata (Profondità 8)
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


---


## WebSocket Security

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


---


## Variabili d'ambiente

### Globali

| Variabile         | Default                | Descrizione                             |
|-------------------|-----------------------|-----------------------------------------|
| `REDIS_URL`       | `redis://redis:6379/0`| Connection string Redis                 |
| `REST_BASE_URL`   | `http://api-rest:8080`| URL base API REST (per MCP host)        |

### Sicurezza

| Variabile               | Default           | Descrizione                                   |
|-------------------------|-------------------|-----------------------------------------------|
| `RATE_LIMIT`            | `100/minute`      | Rate limit REST (formato slowapi)             |
| `RATE_LIMIT_PER_MIN`    | `100`             | Rate limit GraphQL (richieste/minuto)         |
| `WS_MESSAGE_RATE_LIMIT` | `10`              | Rate limit WebSocket (messaggi/secondo)       |
| `WS_ALLOWED_ORIGINS`    | `*`               | Origini WebSocket consentite (comma-separated)|
| `WS_MAX_PAYLOAD`        | `1048576`         | Max payload WebSocket (byte)                  |

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


## Problemi comuni

| Problema | Causa | Soluzione |
|----------|-------|-----------|
| **429 Too Many Requests** | Rate limit superato | Attendi 1 minuto o aumenta `RATE_LIMIT` |
| **Nessun evento WebSocket** | Redis non pubblica o ws-events down | Verifica `docker compose logs ws-events` |
| **Container non healthy** | Dipendenza (Redis/api-rest) non pronta | `docker compose logs <servizio>` |
| **MCP host esce subito** | One-shot normale | Output già completato; verifica con `docker compose logs mcp-host` |
| **Metriche vuote** | Nessun traffico generato | Esegui query/richieste prima di leggere `/metrics` |
| **Porta 6379 occupata** | Redis già in esecuzione | `netstat -ano | findstr :6379` e termina processo |
| **WebSocket origin non permessa** | Origin non whitelisted | Controlla variabile `WS_ALLOWED_ORIGINS` |
| **Query GraphQL troppo profonda** | Depth limit superato | Riduci profondità query o aumenta `GRAPHQL_DEPTH_LIMIT` |

## Comandi diagnostici

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

# Test connessione Redis
docker compose exec redis redis-cli ping

# Visualizza metriche REST
curl http://localhost:8080/metrics | grep api_rest_requests_total

# Visualizza metriche GraphQL
curl http://localhost:9090/metrics | grep graphql_requests_total

# Test health check
curl http://localhost:8080/health
```

---