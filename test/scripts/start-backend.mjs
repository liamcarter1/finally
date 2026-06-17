/**
 * Cross-platform launcher for the FinAlly backend in E2E mode.
 *
 * Used by Playwright's `webServer.command`. Boots the FastAPI app via uvicorn
 * with:
 *   - LLM_MOCK=true        -> deterministic, offline mock LLM grammar
 *   - MASSIVE_API_KEY=""   -> built-in market simulator (no external data)
 *   - STATIC_DIR=../out    -> serves the built Next.js export (frontend/out)
 *   - FINALLY_DB_PATH=<tmp>/e2e-<pid>.db -> throwaway DB so the real db is
 *     never polluted and every run starts from a fresh, lazily-seeded state.
 *
 * Runs from the repo's backend/ directory (uv project root).
 */
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join } from 'node:path';
import { tmpdir } from 'node:os';
import { mkdtempSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
// test/scripts -> test -> repo root
const repoRoot = resolve(__dirname, '..', '..');
const backendDir = join(repoRoot, 'backend');
const staticDir = join(repoRoot, 'frontend', 'out');

const dbDir = mkdtempSync(join(tmpdir(), 'finally-e2e-'));
const dbPath = join(dbDir, 'e2e.db');

const host = process.env.E2E_HOST || '127.0.0.1';
const port = process.env.E2E_PORT || '8000';

const env = {
  ...process.env,
  LLM_MOCK: 'true',
  MASSIVE_API_KEY: '',
  OPENROUTER_API_KEY: '',
  STATIC_DIR: staticDir,
  FINALLY_DB_PATH: dbPath,
};

console.log(`[start-backend] backend dir : ${backendDir}`);
console.log(`[start-backend] static dir  : ${staticDir}`);
console.log(`[start-backend] db path     : ${dbPath}`);
console.log(`[start-backend] listening   : http://${host}:${port}`);

const child = spawn(
  'uv',
  [
    'run',
    'uvicorn',
    'app.main:app',
    '--host',
    host,
    '--port',
    String(port),
  ],
  {
    cwd: backendDir,
    env,
    stdio: 'inherit',
    shell: process.platform === 'win32', // resolve `uv` via PATH on Windows
  },
);

child.on('exit', (code) => process.exit(code ?? 0));

for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => {
    child.kill();
    process.exit(0);
  });
}
