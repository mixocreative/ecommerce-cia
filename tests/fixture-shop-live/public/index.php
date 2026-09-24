<?php

declare(strict_types=1);

/**
 * fixture-shop-live — the whole front door.
 *
 * Run it with:  php -S 127.0.0.1:8123 -t public
 */

require dirname(__DIR__) . '/src/Db.php';
require dirname(__DIR__) . '/src/Checkout.php';
require dirname(__DIR__) . '/src/RefundDesk.php';
require dirname(__DIR__) . '/src/Admin.php';
require dirname(__DIR__) . '/src/Jobs.php';
require dirname(__DIR__) . '/src/Gateway/Callback.php';

use Fixture\Admin;
use Fixture\Checkout;
use Fixture\Db;
use Fixture\Gateway\Callback;
use Fixture\RefundDesk;

$path   = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

function page(string $title, string $body): void
{
    echo "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">";
    echo "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">";
    echo "<title>{$title}</title><link rel=\"stylesheet\" href=\"/shop.css\"></head><body>";
    echo "<nav><a href=\"/\">Shop</a> <a href=\"/admin/stock\">Stock</a> <a href=\"/admin/orders\">Orders</a></nav>";
    echo "<main>{$body}</main></body></html>";
}

function h(?string $s): string
{
    return htmlspecialchars((string) $s, ENT_QUOTES, 'UTF-8');
}

// --------------------------------------------------------------------- storefront

if ($path === '/' && $method === 'GET') {
    $rows = Db::conn()->query(
        'SELECT p.sku, p.title, p.price_cents, c.qty
           FROM products p LEFT JOIN stock_cache c ON c.sku = p.sku ORDER BY p.sku'
    )->fetchAll();

    $body = '<h1>The fixture shop</h1><ul>';
    foreach ($rows as $r) {
        $body .= '<li><a href="/product?sku=' . h($r['sku']) . '">' . h($r['title']) . '</a> — '
            . 'NT$' . number_format(((int) $r['price_cents']) / 100, 0) . ' — '
            . '<span data-stock="' . h($r['sku']) . '">' . (int) $r['qty'] . '</span> in stock</li>';
    }
    page('The fixture shop', $body . '</ul>');
    return;
}

if ($path === '/product' && $method === 'GET') {
    $sku = (string) ($_GET['sku'] ?? '');
    $stmt = Db::conn()->prepare(
        'SELECT p.sku, p.title, p.price_cents, c.qty
           FROM products p LEFT JOIN stock_cache c ON c.sku = p.sku WHERE p.sku = ?'
    );
    $stmt->execute([$sku]);
    $r = $stmt->fetch();

    if ($r === false) {
        http_response_code(404);
        page('Not found', '<h1>No such product</h1>');
        return;
    }

    $qty  = (int) $r['qty'];
    $body = '<h1>' . h($r['title']) . '</h1>'
        . '<p>NT$' . number_format(((int) $r['price_cents']) / 100, 0) . '</p>'
        . '<p><span data-stock="' . h($r['sku']) . '">' . $qty . '</span> in stock</p>'
        . '<form method="post" action="/checkout">'
        . '<input type="hidden" name="sku" value="' . h($r['sku']) . '">'
        . '<label for="qty">Quantity</label>'
        . '<input id="qty" name="qty" type="number" value="1" min="1" max="' . $qty . '">'
        . '<label for="email">E-mail</label>'
        . '<input id="email" name="email" type="email" value="walk@example.com">'
        . '<button type="submit">Place the order</button></form>';
    page(h($r['title']), $body);
    return;
}

if ($path === '/checkout' && $method === 'POST') {
    $result = Checkout::place(
        (string) ($_POST['sku'] ?? ''),
        (int) ($_POST['qty'] ?? 1),
        (string) ($_POST['email'] ?? 'walk@example.com')
    );

    if (!$result['ok']) {
        header('Location: /product?sku=' . urlencode((string) ($_POST['sku'] ?? '')), true, 302);
        return;
    }

    page('Order placed', '<h1>Order ' . (int) $result['order_id'] . ' placed</h1>'
        . '<p data-order-id="' . (int) $result['order_id'] . '">Pay within 30 minutes.</p>');
    return;
}

// ----------------------------------------------------------------------- gateway

if ($path === '/gateway/callback' && $method === 'POST') {
    header('Content-Type: text/plain');
    echo Callback::handle($_POST);
    return;
}

// ------------------------------------------------------------------------- admin

if ($path === '/admin/stock' && $method === 'GET') {
    $body = '<h1>Stock</h1><table><tr><th>SKU</th><th>Title</th><th>Stock</th></tr>';
    foreach (Admin::stockRows() as $r) {
        $body .= '<tr><td>' . h($r['sku']) . '</td><td>' . h($r['title']) . '</td>'
            . '<td data-admin-stock="' . h($r['sku']) . '">' . (int) $r['stock'] . '</td></tr>';
    }
    $body .= '</table><form method="post" action="/admin/stock">'
        . '<label for="sku">SKU</label><input id="sku" name="sku">'
        . '<label for="qty">Set to</label><input id="qty" name="qty" type="number">'
        . '<button type="submit">Save</button></form>';
    page('Stock', $body);
    return;
}

if ($path === '/admin/stock' && $method === 'POST') {
    Admin::setStock((string) ($_POST['sku'] ?? ''), (int) ($_POST['qty'] ?? 0));
    header('Location: /admin/stock', true, 302);
    return;
}

if ($path === '/admin/orders' && $method === 'GET') {
    $body = '<h1>Orders</h1><table><tr><th>#</th><th>SKU</th><th>Qty</th><th>Status</th><th>E-mail</th></tr>';
    foreach (Admin::orders() as $o) {
        $body .= '<tr><td>' . (int) $o['id'] . '</td><td>' . h($o['sku']) . '</td><td>' . (int) $o['qty'] . '</td>'
            . '<td data-order-status="' . (int) $o['id'] . '">' . h($o['status']) . '</td><td>' . h($o['email']) . '</td>'
            . '<td><form method="post" action="/admin/refund"><input type="hidden" name="order_id" value="' . (int) $o['id'] . '">'
            . '<button type="submit">Refund</button></form></td></tr>';
    }
    $body .= '</table><h2>Operator notices</h2><ul>';
    foreach (Admin::notices() as $n) {
        $body .= '<li>' . h($n['created_at']) . ' — ' . h($n['body']) . '</li>';
    }
    page('Orders', $body . '</ul>');
    return;
}

if ($path === '/admin/refund' && $method === 'POST') {
    RefundDesk::refund((int) ($_POST['order_id'] ?? 0));
    header('Location: /admin/orders', true, 302);
    return;
}

// -------------------------------------------------------------- the machine view

if ($path === '/debug/state' && $method === 'GET') {
    // Not a shop page: the walk's read-back of what the store actually holds.
    header('Content-Type: application/json');
    $pdo = Db::conn();
    echo json_encode([
        'products'   => $pdo->query('SELECT sku, parent_sku, stock FROM products ORDER BY sku')->fetchAll(),
        'cache'      => $pdo->query('SELECT sku, qty, refreshed_at FROM stock_cache ORDER BY sku')->fetchAll(),
        'orders'     => $pdo->query('SELECT id, sku, qty, total_cents, status FROM orders ORDER BY id')->fetchAll(),
        'events'     => $pdo->query('SELECT event_id, order_id, result FROM gateway_events')->fetchAll(),
        'notices'    => $pdo->query('SELECT audience, order_id, body FROM notices ORDER BY id')->fetchAll(),
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    return;
}

if ($path === '/shop.css') {
    header('Content-Type: text/css');
    echo "body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}nav a{margin-right:1rem}"
        . "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.3rem .6rem}"
        . "label{display:block;margin-top:.5rem}:focus-visible{outline:2px solid #06c}";
    return;
}

http_response_code(404);
page('Not found', '<h1>Not found</h1>');
