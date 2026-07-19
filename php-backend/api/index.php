<?php
// ============================================================
// Krishna AI — PHP API front controller (router).
// All /api/* requests are rewritten here by api/.htaccess.
// ============================================================
define('KRISHNA', true);

// Never leak PHP errors as HTML into the API; return JSON instead.
error_reporting(E_ALL);
ini_set('display_errors', '0');

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Authorization, Content-Type');
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// --- Locate config written by the installer ---
$configPath = dirname(__DIR__) . '/config.php';
if (!file_exists($configPath)) {
    http_response_code(503);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode([
        'error_code' => 'not_installed',
        'detail'     => 'Backend not installed yet. Open /install in your browser.',
    ]);
    exit;
}
$CONFIG = require $configPath;

require __DIR__ . '/lib/helpers.php';
require __DIR__ . '/lib/db.php';
require __DIR__ . '/lib/jwt.php';
require __DIR__ . '/lib/auth.php';

// --- Route registry ---
$ROUTES = [];
function route(string $method, string $pattern, callable $handler): void {
    global $ROUTES;
    $ROUTES[] = [$method, $pattern, $handler];
}

// --- Connect to the database ---
try {
    $pdo = db_connect($CONFIG);
} catch (Throwable $e) {
    error_out(500, 'db_error', 'Database connection failed.');
}

// --- Register routes ---
require __DIR__ . '/routes/auth.php';
// Part 2 (chat) and Part 3 (memory) route files are added here later.

// --- Work out the path after /api (also accepts an optional /v1) ---
$uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
$path = preg_replace('#^.*?/api#', '', $uri);   // strip everything up to the first /api
$path = preg_replace('#^/v1#', '', $path);        // tolerate /api/v1/... too
$path = '/' . trim($path, '/');
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

// --- Dispatch ---
try {
    foreach ($ROUTES as [$m, $p, $handler]) {
        if ($m !== $method) continue;
        $regex = '#^' . preg_replace('#\{[^}]+\}#', '([^/]+)', $p) . '$#';
        if (preg_match($regex, $path, $matches)) {
            array_shift($matches);
            $handler(array_map('rawurldecode', $matches));
            exit;
        }
    }
    error_out(404, 'not_found', 'Route not found: ' . $method . ' ' . $path);
} catch (Throwable $e) {
    error_out(500, 'server_error', 'Internal server error.');
}
