import WebSocket from 'ws';

const runs = parseInt(process.env.RUNS || '23', 10);
const wsUrl = process.env.WS_URL || 'ws://localhost:7070/ws';
const restBase = process.env.REST_BASE || 'http://localhost:8080';
const productId = process.env.PRODUCT_ID || '1';

function p95(vals) {
  const s = [...vals].sort((a, b) => a - b);
  const idx = Math.max(0, Math.ceil(s.length * 0.95) - 1);
  return s[idx];
}

async function main() {
  const ws = new WebSocket(wsUrl);
  const deltas = [];
  const pending = [];

  ws.on('open', async () => {
    console.log(`WS connected to ${wsUrl}`);
    for (let i = 0; i < runs; i++) {
      const ts = Date.now();
      pending.push(ts);
      await fetch(`${restBase}/products/${productId}?price=1200&stock=5`, { method: 'PATCH' });
      await new Promise((resolve) => {
        const check = () => {
          if (pending.length === 0) resolve();
          else setTimeout(check, 1);
        };
        check();
      });
    }
  });

  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString());
      if (msg.type === 'price_update' || msg.type === 'stock_update') {
        if (pending.length > 0) {
          const sent = pending.shift();
          const delta = Date.now() - sent;
          deltas.push(delta);
          console.log(`Event ${msg.type} delta=${delta} ms (count=${deltas.length}/${runs})`);
          console.log(`Latency ${deltas.length}: ${delta} ms`);
          if (deltas.length >= runs) {
            const mean = deltas.reduce((a, b) => a + b, 0) / deltas.length;
            console.log(`\nWS latency results (publish→receive): runs=${runs}`);
            console.log(`mean=${mean.toFixed(2)} ms, p95=${p95(deltas).toFixed(2)} ms`);
            ws.close();
            process.exit(0);
          }
        }
      }
    } catch (e) {
      console.error('Parse error', e);
    }
  });

  ws.on('error', (err) => console.error('WS error', err));
}

main().catch((e) => console.error(e));