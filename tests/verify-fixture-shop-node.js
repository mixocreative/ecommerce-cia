'use strict';

/**
 * Prove that every row of EXPECTED-fixture-shop-node.md still reproduces.
 *
 *   node tests/verify-fixture-shop-node.js
 *
 * Scorer's tool, not the auditor's: it names every planted defect. Exit 0 when all five rows
 * (four defects, one control) behave as the key says.
 */

const { execFileSync, spawn, spawnSync } = require('node:child_process');
const path = require('node:path');

const SHOP = path.join(__dirname, 'fixture-shop-node');
const BASE = 'http://127.0.0.1:8124';
const results = [];

function check(row, ok, detail) {
  results.push([row, ok]);
  console.log(`  ${ok ? 'REPRODUCED' : 'GONE      '}  ${row.padEnd(26)} ${detail}`);
}

const node = (args, env) =>
  execFileSync(process.execPath, ['server.js', ...args],
    { cwd: SHOP, encoding: 'utf8', env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'ignore'] }).trim();

const reset = () => node(['--reset']);

async function get(p) { return (await fetch(BASE + p)).text(); }
async function post(p, body) {
  return (await fetch(BASE + p, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })).text();
}
const state = async () => JSON.parse(await get('/debug/state'));
const stock = (st, sku) => st.products.find((p) => p.sku === sku).stock;

(async () => {
  reset();
  const server = spawn(process.execPath, ['server.js'], { cwd: SHOP, stdio: 'ignore' });
  await new Promise((r) => setTimeout(r, 1200));

  try {
    console.log('fixture-shop-node — planted rows and the control\n');

    // N1 — two processes, one unit, both win
    reset();
    spawnSync(process.execPath, ['-e',
      `const {DatabaseSync}=require('node:sqlite');`
      + `new DatabaseSync('var/shop.sqlite').prepare('UPDATE products SET stock=1 WHERE sku=?').run('PLATE-01');`],
      { cwd: SHOP, stdio: 'ignore' });
    const env = { FIXTURE_SLOW_MS: '400' };
    const racers = [1, 2].map(() => spawn(process.execPath, ['server.js', '--take', 'PLATE-01', '1'],
      { cwd: SHOP, env: { ...process.env, ...env }, stdio: 'ignore' }));
    await Promise.all(racers.map((r) => new Promise((res) => r.on('exit', res))));
    let st = await state();
    check('N1 oversell race', st.orders.length === 2 && stock(st, 'PLATE-01') <= 0,
      `${st.orders.length} orders for 1 unit; stock ${stock(st, 'PLATE-01')}`);

    // N2 — the same declined notification twice releases twice
    reset();
    await post('/checkout', 'sku=MUG-01&qty=2&email=w@example.com');
    const oid = (await state()).orders[0].id;
    const body = node(['--sign', String(oid), 'declined', 'evt-dup']);
    await post('/webhook', body);
    const mid = stock(await state(), 'MUG-01');
    await post('/webhook', body);
    st = await state();
    check('N2 duplicate release', mid === 5 && stock(st, 'MUG-01') === 7,
      `one release -> ${mid}, the same notification again -> ${stock(st, 'MUG-01')}`);

    // N3 — the catch acknowledges what it did not write (a ghost order proves the shape)
    reset();
    const ghost = await post('/webhook', node(['--sign', '9999', 'paid', 'evt-ghost']));
    st = await state();
    check('N3 ack without a write', ghost.trim() === '1|OK' && st.orders.length === 0,
      `answered '${ghost.trim()}' for an order that does not exist; ${st.orders.length} orders`);

    // N4 — a refusal nobody is told about
    reset();
    await post('/checkout', 'sku=MUG-01&qty=999&email=w@example.com');
    st = await state();
    check('N4 silent refusal', st.orders.length === 0 && st.notices.length === 0,
      'no order, no notice, no message anywhere');

    // NC1 — the control: a tampered signature is refused and changes nothing
    reset();
    await post('/checkout', 'sku=MUG-01&qty=1&email=w@example.com');
    const id2 = (await state()).orders[0].id;
    const good = node(['--sign', String(id2), 'declined', 'evt-tamper']);
    const tampered = good.replace('result=declined', 'result=paid');
    const answer = await post('/webhook', tampered);
    st = await state();
    check('NC1 control: signature', answer.trim() === '0|signature' && stock(st, 'MUG-01') === 4,
      'refused, nothing changed — must NOT be filed as a defect');

    reset();
  } finally {
    server.kill();
  }

  const gone = results.filter(([, ok]) => !ok).map(([r]) => r);
  console.log();
  if (gone.length) {
    console.log(`FAIL: ${gone.length} row(s) no longer reproduce: ${gone.join(', ')}`);
    process.exit(1);
  }
  console.log(`OK: ${results.length} rows reproduce (4 defects + 1 control).`);
})();
