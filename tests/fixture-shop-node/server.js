'use strict';

/**
 * fixture-shop-node — the same shop, a different stack.
 *
 *   node server.js --reset      seed the store
 *   node server.js              serve on 127.0.0.1:8124
 *
 * Node 22 + node:sqlite. No dependencies, no framework, no build step.
 */

const http = require('node:http');
const { DatabaseSync } = require('node:sqlite');
const crypto = require('node:crypto');
const path = require('node:path');

const DB_PATH = process.env.FIXTURE_DB || path.join(__dirname, 'var', 'shop.sqlite');
const SECRET = 'fixture-node-shared-secret';
const PORT = Number(process.env.PORT || 8124);

require('node:fs').mkdirSync(path.dirname(DB_PATH), { recursive: true });
const db = new DatabaseSync(DB_PATH);

const SCHEMA = `
CREATE TABLE IF NOT EXISTS products (
  sku TEXT PRIMARY KEY, title TEXT NOT NULL, price_cents INTEGER NOT NULL, stock INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT NOT NULL, qty INTEGER NOT NULL,
  total_cents INTEGER NOT NULL, status TEXT NOT NULL, email TEXT NOT NULL, placed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS webhook_events (
  event_id TEXT PRIMARY KEY, order_id INTEGER NOT NULL, result TEXT NOT NULL, seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notices (
  id INTEGER PRIMARY KEY AUTOINCREMENT, audience TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL
);`;
db.exec(SCHEMA);

const now = () => new Date().toISOString().replace('T', ' ').slice(0, 19);

function reset() {
  db.exec('DELETE FROM products; DELETE FROM orders; DELETE FROM webhook_events; DELETE FROM notices;');
  const add = db.prepare('INSERT INTO products (sku, title, price_cents, stock) VALUES (?, ?, ?, ?)');
  add.run('MUG-01', 'Enamel mug', 32000, 5);
  add.run('PLATE-01', 'Serving plate', 78000, 2);
  console.log(`seeded 2 products at ${DB_PATH}`);
}

// ---------------------------------------------------------------- the shop

function placeOrder(sku, qty, email) {
  const row = db.prepare('SELECT sku, price_cents, stock FROM products WHERE sku = ?').get(sku);
  if (!row) return { ok: false, reason: 'no such product' };
  if (row.stock < qty) return { ok: false, reason: 'not enough stock' };

  const slow = Number(process.env.FIXTURE_SLOW_MS || 0);
  if (slow > 0) {
    // A deliberate pause, for profiling the shop under load.
    const until = Date.now() + slow;
    while (Date.now() < until) { /* spin: this process has nothing else to do */ }
  }

  db.prepare('UPDATE products SET stock = ? WHERE sku = ?').run(row.stock - qty, sku);
  const res = db.prepare(
    `INSERT INTO orders (sku, qty, total_cents, status, email, placed_at)
     VALUES (?, ?, ?, 'pending', ?, ?)`
  ).run(sku, qty, qty * row.price_cents, email, now());
  return { ok: true, order_id: Number(res.lastInsertRowid) };
}

function sign(fields) {
  const flat = Object.keys(fields).sort().map((k) => `${k}=${fields[k]}`).join('&');
  return crypto.createHmac('sha256', SECRET).update(flat).digest('hex');
}

function handleWebhook(fields) {
  const given = fields.sig;
  const rest = { ...fields };
  delete rest.sig;
  const expected = sign(rest);
  if (!given || given.length !== expected.length
      || !crypto.timingSafeEqual(Buffer.from(given), Buffer.from(expected))) {
    return '0|signature';
  }

  const orderId = Number(fields.order_id || 0);
  try {
    if (fields.result === 'declined') {
      const order = db.prepare('SELECT sku, qty FROM orders WHERE id = ?').get(orderId);
      if (order) {
        db.prepare('UPDATE products SET stock = stock + ? WHERE sku = ?').run(order.qty, order.sku);
        db.prepare("UPDATE orders SET status = 'declined' WHERE id = ?").run(orderId);
      }
    } else {
      db.prepare("UPDATE orders SET status = 'paid' WHERE id = ? AND status = 'pending'").run(orderId);
    }
    db.prepare(
      'INSERT OR IGNORE INTO webhook_events (event_id, order_id, result, seen_at) VALUES (?, ?, ?, ?)'
    ).run(String(fields.event_id || ''), orderId, String(fields.result || ''), now());
    return '1|OK';
  } catch (err) {
    // The provider must not be left retrying something we have already seen.
    return '1|OK';
  }
}

// ---------------------------------------------------------------- the server

const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const page = (title, body) =>
  `<!doctype html><html lang="en"><head><meta charset="utf-8">`
  + `<meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title>`
  + `</head><body><nav><a href="/">Shop</a> <a href="/admin">Admin</a></nav><main>${body}</main></body></html>`;

function body(req) {
  return new Promise((resolve) => {
    let raw = '';
    req.on('data', (c) => { raw += c; });
    req.on('end', () => resolve(Object.fromEntries(new URLSearchParams(raw))));
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const send = (code, text, type = 'text/html; charset=utf-8') => {
    res.writeHead(code, { 'Content-Type': type });
    res.end(text);
  };

  if (url.pathname === '/' && req.method === 'GET') {
    const rows = db.prepare('SELECT sku, title, price_cents, stock FROM products ORDER BY sku').all();
    return send(200, page('Shop', '<h1>The node fixture shop</h1><ul>' + rows.map((r) =>
      `<li><a href="/product?sku=${esc(r.sku)}">${esc(r.title)}</a> — `
      + `<span data-stock="${esc(r.sku)}">${r.stock}</span> in stock</li>`).join('') + '</ul>'));
  }

  if (url.pathname === '/product' && req.method === 'GET') {
    const r = db.prepare('SELECT * FROM products WHERE sku = ?').get(url.searchParams.get('sku'));
    if (!r) return send(404, page('Not found', '<h1>No such product</h1>'));
    return send(200, page(r.title,
      `<h1>${esc(r.title)}</h1><p><span data-stock="${esc(r.sku)}">${r.stock}</span> in stock</p>`
      + `<form method="post" action="/checkout">`
      + `<input type="hidden" name="sku" value="${esc(r.sku)}">`
      + `<label for="qty">Quantity</label><input id="qty" name="qty" type="number" value="1" min="1" max="${r.stock}">`
      + `<label for="email">E-mail</label><input id="email" name="email" type="email" value="walk@example.com">`
      + `<button type="submit">Place the order</button></form>`));
  }

  if (url.pathname === '/checkout' && req.method === 'POST') {
    const f = await body(req);
    const out = placeOrder(String(f.sku || ''), Number(f.qty || 1), String(f.email || 'walk@example.com'));
    if (!out.ok) {
      res.writeHead(302, { Location: `/product?sku=${encodeURIComponent(String(f.sku || ''))}` });
      return res.end();
    }
    return send(200, page('Order placed',
      `<h1>Order ${out.order_id} placed</h1><p data-order-id="${out.order_id}">Pay within 30 minutes.</p>`));
  }

  if (url.pathname === '/webhook' && req.method === 'POST') {
    return send(200, handleWebhook(await body(req)), 'text/plain');
  }

  if (url.pathname === '/admin' && req.method === 'GET') {
    const rows = db.prepare('SELECT id, sku, qty, status, email FROM orders ORDER BY id DESC LIMIT 50').all();
    const notes = db.prepare("SELECT body, created_at FROM notices WHERE audience = 'operator' ORDER BY id DESC").all();
    return send(200, page('Admin', '<h1>Orders</h1><table>' + rows.map((o) =>
      `<tr><td>${o.id}</td><td>${esc(o.sku)}</td><td>${o.qty}</td>`
      + `<td data-order-status="${o.id}">${esc(o.status)}</td><td>${esc(o.email)}</td></tr>`).join('')
      + '</table><h2>Operator notices</h2><ul>'
      + notes.map((n) => `<li>${esc(n.created_at)} — ${esc(n.body)}</li>`).join('') + '</ul>'));
  }

  if (url.pathname === '/debug/state' && req.method === 'GET') {
    return send(200, JSON.stringify({
      products: db.prepare('SELECT sku, stock FROM products ORDER BY sku').all(),
      orders: db.prepare('SELECT id, sku, qty, total_cents, status FROM orders ORDER BY id').all(),
      events: db.prepare('SELECT event_id, order_id, result FROM webhook_events').all(),
      notices: db.prepare('SELECT audience, body FROM notices ORDER BY id').all(),
    }, null, 2), 'application/json');
  }

  send(404, page('Not found', '<h1>Not found</h1>'));
});

if (process.argv.includes('--reset')) {
  reset();
} else if (process.argv.includes('--sign')) {
  const [, , , orderId, result, eventId] = process.argv;
  const f = { order_id: String(orderId), result: String(result), event_id: String(eventId) };
  f.sig = sign(f);
  console.log(new URLSearchParams(f).toString());
} else if (process.argv.includes('--take')) {
  const i = process.argv.indexOf('--take');
  const out = placeOrder(process.argv[i + 1], Number(process.argv[i + 2] || 1), 'cli@example.com');
  console.log(JSON.stringify(out));
  process.exit(out.ok ? 0 : 1);
} else {
  server.listen(PORT, '127.0.0.1', () => console.log(`fixture-shop-node on http://127.0.0.1:${PORT}`));
}

module.exports = { placeOrder, sign, handleWebhook };
