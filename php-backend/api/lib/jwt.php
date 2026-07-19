<?php
// Minimal JWT (HS256) — no external libraries.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function b64url_encode(string $data): string {
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

function b64url_decode(string $data): string {
    $pad = strlen($data) % 4;
    if ($pad) $data .= str_repeat('=', 4 - $pad);
    return base64_decode(strtr($data, '-_', '+/'));
}

/**
 * Encode a JWT. $payload should include at least: sub, type, iat, exp.
 */
function jwt_encode(array $payload, string $secret): string {
    $header = ['alg' => 'HS256', 'typ' => 'JWT'];
    $segments = [
        b64url_encode(json_encode($header, JSON_UNESCAPED_SLASHES)),
        b64url_encode(json_encode($payload, JSON_UNESCAPED_SLASHES)),
    ];
    $signing_input = implode('.', $segments);
    $signature = hash_hmac('sha256', $signing_input, $secret, true);
    $segments[] = b64url_encode($signature);
    return implode('.', $segments);
}

/**
 * Decode + verify a JWT. Returns the payload array, or null if the token is
 * invalid, tampered, expired, or of the wrong type.
 */
function jwt_decode_verify(string $token, string $secret, ?string $expectedType = null): ?array {
    $parts = explode('.', $token);
    if (count($parts) !== 3) return null;
    [$h, $p, $s] = $parts;

    $expected = hash_hmac('sha256', "$h.$p", $secret, true);
    $given = b64url_decode($s);
    if (!hash_equals($expected, $given)) return null;

    $payload = json_decode(b64url_decode($p), true);
    if (!is_array($payload)) return null;

    if (isset($payload['exp']) && time() >= (int) $payload['exp']) return null;
    if ($expectedType !== null && ($payload['type'] ?? null) !== $expectedType) return null;

    return $payload;
}
