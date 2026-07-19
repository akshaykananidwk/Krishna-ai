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

/**
 * UUID version 7: a 48-bit millisecond timestamp followed by random bits.
 * These sort lexicographically in creation order, so rows keyed by them stay in
 * the right order even when their DATETIME (second-precision) values collide.
 */
function uuidv7(): string {
    $ms  = (int) (microtime(true) * 1000);
    $ts  = str_pad(dechex($ms), 12, '0', STR_PAD_LEFT);   // 48 bits → 12 hex chars
    $b   = hex2bin($ts) . random_bytes(10);               // 6 + 10 = 16 bytes
    $b[6] = chr((ord($b[6]) & 0x0f) | 0x70);              // version 7
    $b[8] = chr((ord($b[8]) & 0x3f) | 0x80);             // RFC 4122 variant
    $h = bin2hex($b);
    return sprintf('%s-%s-%s-%s-%s',
        substr($h, 0, 8), substr($h, 8, 4), substr($h, 12, 4),
        substr($h, 16, 4), substr($h, 20, 12));
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

/** Parse an incoming ISO-8601 timestamp into UTC 'Y-m-d H:i:s', or null. */
function parse_dt($v): ?string {
    if ($v === null || $v === '' || !is_string($v)) return null;
    $ts = strtotime($v);
    return $ts === false ? null : gmdate('Y-m-d H:i:s', $ts);
}

/** Parse an incoming date (YYYY-MM-DD) into 'Y-m-d', or null. */
function parse_date($v): ?string {
    if ($v === null || $v === '' || !is_string($v)) return null;
    $ts = strtotime($v);
    return $ts === false ? null : gmdate('Y-m-d', $ts);
}

/** Coerce a JSON value (bool/int/string) into a 0/1 integer for TINYINT columns. */
function b_int($v): int {
    return ($v === true || $v === 1 || $v === '1' || $v === 'true' || $v === 'yes') ? 1 : 0;
}

/**
 * Fetch a row from $table owned by $userId, or null. $table is always a
 * hard-coded literal from route code (never user input), so it is safe to
 * interpolate.
 */
function own_row(PDO $pdo, string $table, string $userId, string $id): ?array {
    $stmt = $pdo->prepare("SELECT * FROM $table WHERE id = ? AND user_id = ?");
    $stmt->execute([$id, $userId]);
    return $stmt->fetch() ?: null;
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
