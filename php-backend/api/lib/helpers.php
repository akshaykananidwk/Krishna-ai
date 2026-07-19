<?php
// Shared helpers. Loaded by the front controller (api/index.php).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

/** Send a JSON response and stop. */
function json_out($data, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

/** Send a JSON error envelope (matches the Flutter app's error handling). */
function error_out(int $code, string $errorCode, string $detail): void {
    json_out(['error_code' => $errorCode, 'detail' => $detail], $code);
}

/** Decode the JSON request body into an associative array. */
function body(): array {
    $raw = file_get_contents('php://input');
    if ($raw === '' || $raw === false) return [];
    $data = json_decode($raw, true);
    return is_array($data) ? $data : [];
}

/** RFC 4122 version-4 UUID. */
function uuidv4(): string {
    $b = random_bytes(16);
    $b[6] = chr((ord($b[6]) & 0x0f) | 0x40);
    $b[8] = chr((ord($b[8]) & 0x3f) | 0x80);
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($b), 4));
}

/** Current UTC time as 'Y-m-d H:i:s' (all timestamps are stored in UTC). */
function now_utc(): string {
    return gmdate('Y-m-d H:i:s');
}

/** Convert a stored 'Y-m-d H:i:s' UTC value to ISO-8601 (e.g. 2026-01-01T12:00:00Z). */
function iso(?string $dt): ?string {
    if ($dt === null || $dt === '') return null;
    return str_replace(' ', 'T', $dt) . 'Z';
}

function client_ip(): ?string {
    return $_SERVER['REMOTE_ADDR'] ?? null;
}

function user_agent(): ?string {
    $ua = $_SERVER['HTTP_USER_AGENT'] ?? null;
    return $ua ? mb_substr($ua, 0, 500) : null;
}

/** Read the Bearer token from the Authorization header (handles CGI/FastCGI quirks). */
function bearer_token(): ?string {
    $header = null;
    if (isset($_SERVER['HTTP_AUTHORIZATION'])) {
        $header = $_SERVER['HTTP_AUTHORIZATION'];
    } elseif (isset($_SERVER['REDIRECT_HTTP_AUTHORIZATION'])) {
        $header = $_SERVER['REDIRECT_HTTP_AUTHORIZATION'];
    } elseif (function_exists('getallheaders')) {
        foreach (getallheaders() as $k => $v) {
            if (strcasecmp($k, 'Authorization') === 0) { $header = $v; break; }
        }
    }
    if ($header && preg_match('/Bearer\s+(.+)/i', $header, $m)) {
        return trim($m[1]);
    }
    return null;
}

/** Validate an email address. */
function valid_email(?string $email): bool {
    return is_string($email) && filter_var($email, FILTER_VALIDATE_EMAIL) !== false;
}

/**
 * Validate a password against the same policy the Flutter app enforces:
 * >= 8 chars, at least one lowercase, one uppercase and one digit.
 * Returns null if OK, or an error message.
 */
function password_error(?string $pw): ?string {
    if (!is_string($pw) || strlen($pw) < 8) return 'Password must be at least 8 characters.';
    if (!preg_match('/[a-z]/', $pw)) return 'Password must contain a lowercase letter.';
    if (!preg_match('/[A-Z]/', $pw)) return 'Password must contain an uppercase letter.';
    if (!preg_match('/[0-9]/', $pw)) return 'Password must contain a digit.';
    return null;
}
