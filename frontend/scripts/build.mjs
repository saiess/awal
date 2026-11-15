import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync, readdirSync, copyFileSync, renameSync, existsSync, lstatSync, realpathSync } from 'node:fs';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repository = resolve(root, '..');
const output = resolve(repository, 'app/static/ui');
// Vite may empty only this dedicated generated directory.
if (relative(repository, output).replaceAll('\\', '/') !== 'app/static/ui') throw new Error('Invalid build directory');
if (relative(resolve(realpathSync(repository), 'app/static'), realpathSync(dirname(output))) !== '' ||
    (existsSync(output) && lstatSync(output).isSymbolicLink())) throw new Error('Refusing to empty linked build output');
function run(args) {
  const result = spawnSync(process.execPath, args, { cwd: root, stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
if (!process.env.npm_execpath) throw new Error('Run npm run build from frontend/.');
run([process.env.npm_execpath, 'run', 'typecheck']);
run([resolve(root, 'node_modules/vite/bin/vite.js'), 'build']);

const licenses = {};
mkdirSync(resolve(output, 'licenses'), { recursive: true });
for (const name of ['react', 'react-dom', 'scheduler', 'vite']) {
  const folder = resolve(root, 'node_modules', name);
  const license = readdirSync(folder).find(file => /^license(?:\.(?:md|txt))?$/i.test(file));
  if (!license) throw new Error(`Missing license for ${name}`);
  copyFileSync(resolve(folder, license), resolve(output, 'licenses', `${name}.LICENSE`));
  const metadata = JSON.parse(readFileSync(resolve(folder, 'package.json'), 'utf8'));
  licenses[name] = { version: metadata.version, license: metadata.license };
}
writeFileSync(resolve(output, 'licenses/inventory.json'), JSON.stringify(licenses, null, 2));
const sha = data => createHash('sha256').update(data).digest('hex');
const walk = folder => readdirSync(folder, { withFileTypes: true }).flatMap(entry =>
  entry.isDirectory() ? walk(resolve(folder, entry.name)) : [resolve(folder, entry.name)]);
const sources = ['package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts', 'index.html', 'scripts/build.mjs', 'scripts/check-dev.mjs',
  ...walk(resolve(root, 'src')).map(file => relative(root, file).replaceAll('\\', '/'))];
const inputs = Object.fromEntries(sources.sort().map(name => [name, sha(readFileSync(resolve(root, name)))]));
const assets = Object.fromEntries(walk(output).sort().map(file => [relative(output, file).replaceAll('\\', '/'), sha(readFileSync(file))]));
writeFileSync(resolve(output, 'build-info.json'), JSON.stringify({ format_version: 1, inputs, assets }, null, 2));
// Keep the existing FastAPI entry path so an already-running local server can
// serve the new interface on refresh without changing its routes.
const entry = resolve(repository, 'app/static/index.html');
writeFileSync(`${entry}.tmp`, readFileSync(resolve(output, 'index.html')));
renameSync(`${entry}.tmp`, entry);
console.log('Frontend built for FastAPI; runtime licenses and build checksums saved.');
