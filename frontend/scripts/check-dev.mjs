// Developer smoke check: FastAPI must already be running on localhost:8000.
import { createServer } from 'vite';
const server = await createServer();
try {
  await server.listen();
  const address = server.httpServer.address();
  if (!address || typeof address === 'string' || address.port !== 3000) throw new Error('Expected the owned Vite server on port 3000');
  const html = await fetch('http://127.0.0.1:3000/');
  if (!html.ok || !(await html.text()).includes('/@vite/client')) throw new Error('Development entry did not load');
  const module = await fetch('http://127.0.0.1:3000/src/App.tsx');
  if (!module.ok) throw new Error('TSX transformation failed');
  const preview = await fetch('http://127.0.0.1:3000/api/segment', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Origin: 'http://127.0.0.1:3000' },
    body: JSON.stringify({ script: 'Development proxy origin check.' }),
  });
  if (!preview.ok || JSON.stringify((await preview.json()).segments) !== '["Development proxy origin check."]') {
    throw new Error('API proxy failed; run FastAPI on port 8000 and retain same-origin checks');
  }
  console.log('Vite port 3000, TSX transformation, and same-origin POST proxy to FastAPI passed.');
} finally {
  await server.close();
}
