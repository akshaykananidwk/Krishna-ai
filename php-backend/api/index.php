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

// Load every helper library. New files under lib/ are picked up automatically,
// so you never have to edit this file when adding a module.
foreach (glob(__DIR__ . '/lib/*.php') as $lib) {
    require $lib;
}

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

// Register every route file. Drop a new file in routes/ and it just works.
foreach (glob(__DIR__ . '/routes/*.php') as $routeFile) {
    require $routeFile;
}

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
