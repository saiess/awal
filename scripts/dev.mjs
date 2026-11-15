// One foreground command owns both development servers. No additional packages.
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const frontend = resolve(root, 'frontend');
const requireFrontend = createRequire(resolve(frontend, 'package.json'));
const python = resolve(root, '.venv-chatterbox/Scripts/python.exe');
let backend, backendExit, vite;
let stopping = false;
let finish;
const stopped = new Promise(done => { finish = done; });
function stop() { stopping = true; finish(); }
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
// Also allow a parent test process to request graceful shutdown without signals.
if (process.argv.includes('--stop-on-stdin')) {
  process.stdin.resume();
  process.stdin.once('data', stop);
  process.stdin.once('end', stop);
}

async function health() {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/health', { signal: AbortSignal.timeout(1500) });
    if (!response.ok) return false;
    const body = await response.json();
    if (body.status !== 'ok' || body.engine_id !== 'chatterbox-turbo') {
      throw new Error('Port 8000 is occupied by another service. Close it before running .\\dev.');
    }
    return true;
  } catch (error) {
    if (error.message.startsWith('Port 8000')) throw error;
    return false;
  }
}

try {
  // Resolve installed Vite before starting any processes.
  const { createServer } = await import(pathToFileURL(requireFrontend.resolve('vite')).href);
  if (!await health()) {
    if (!existsSync(python)) throw new Error('Python environment missing. Run setup.bat first.');
    console.log('Starting FastAPI on port 8000. Waiting for the local engine...');
    backend = spawn(python, ['-B', '-u', 'scripts/serve.py', '--stop-on-stdin'], {
      cwd: root, stdio: ['pipe', 'inherit', 'inherit'], windowsHide: true,
    });
    backend.stdin.on('error', () => {});
    backendExit = new Promise(done => {
      backend.once('error', error => { console.error(error.message); done(1); });
      backend.once('exit', code => done(code ?? 1));
    });
    let exited = false;
    backendExit.then(() => {
      exited = true;
      if (!stopping) {
        console.error('FastAPI stopped. Check the server output above, then run .\\dev again.');
        process.exitCode = 1;
        stop();
      }
    });
    const deadline = Date.now() + 180_000;
    while (!stopping && !await health()) {
      if (exited || Date.now() > deadline) throw new Error('FastAPI did not become ready. See the server output above.');
      await Promise.race([delay(500), stopped]);
    }
  } else console.log('Using the FastAPI server already running on port 8000.');

  if (!stopping) {
    // If a frontend was started separately, restore its backend without spawning a duplicate.
    let existing = false;
    try {
      const response = await fetch('http://127.0.0.1:3000/', { signal: AbortSignal.timeout(1500) });
      existing = response.ok && (await response.text()).includes('/@vite/client');
    } catch { /* No frontend is listening yet. */ }
    if (existing) console.log('Using the frontend already running on port 3000.');
    else {
      vite = await createServer({ root: frontend, configFile: resolve(frontend, 'vite.config.ts') });
      await vite.listen();
    }
    console.log('Local Narration ready: http://127.0.0.1:3000');
    console.log('Keep this terminal open. Ctrl+C stops servers started by this command.');
    await stopped;
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  stopping = true;
  if (vite) await vite.close();
  if (backend && backend.exitCode === null) {
    console.log('Stopping FastAPI; waiting for any active generation to finish...');
    backend.stdin.end('\n');
    await backendExit;
  }
  process.stdin.pause();
  process.removeListener('SIGINT', stop);
  process.removeListener('SIGTERM', stop);
}
