<?php
// Authentication helpers: token issuance/rotation, current user, audit log.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

/** Build the public representation of a user (never exposes the password hash). */
function public_user(array $u): array {
    return [
        'id'            => $u['id'],
        'email'         => $u['email'],
        'full_name'     => $u['full_name'],
        'is_active'     => (bool) $u['is_active'],
        'is_verified'   => (bool) $u['is_verified'],
        'created_at'    => iso($u['created_at']),
        'last_login_at' => iso($u['last_login_at'] ?? null),
    ];
}

/** Issue a fresh access + refresh token pair and persist the refresh token hash. */
function issue_tokens(PDO $pdo, array $config, array $user): array {
    $now = time();
    $access = jwt_encode([
        'sub'   => $user['id'],
        'email' => $user['email'],
        'type'  => 'access',
        'iat'   => $now,
        'exp'   => $now + (int) $config['access_ttl'],
        'jti'   => bin2hex(random_bytes(8)),
    ], $config['jwt_secret']);

    $refresh = jwt_encode([
        'sub'  => $user['id'],
        'type' => 'refresh',
        'iat'  => $now,
        'exp'  => $now + (int) $config['refresh_ttl'],
        'jti'  => bin2hex(random_bytes(8)),
    ], $config['jwt_secret']);

    $stmt = $pdo->prepare(
        'INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, created_at)
         VALUES (?, ?, ?, ?, ?)'
    );
    $stmt->execute([
        uuidv4(),
        $user['id'],
        hash('sha256', $refresh),
        gmdate('Y-m-d H:i:s', $now + (int) $config['refresh_ttl']),
        now_utc(),
    ]);

    return ['access' => $access, 'refresh' => $refresh];
}

/** Look up a non-revoked, non-expired refresh token by its raw value. */
function active_refresh_row(PDO $pdo, string $rawToken): ?array {
    $stmt = $pdo->prepare('SELECT * FROM refresh_tokens WHERE token_hash = ?');
    $stmt->execute([hash('sha256', $rawToken)]);
    $row = $stmt->fetch();
    if (!$row) return null;
    if ($row['revoked_at'] !== null) return null;
    if (strtotime($row['expires_at'] . ' UTC') <= time()) return null;
    return $row;
}

function revoke_refresh(PDO $pdo, string $id): void {
    $pdo->prepare('UPDATE refresh_tokens SET revoked_at = ? WHERE id = ?')
        ->execute([now_utc(), $id]);
}

/** Write an audit-log row (best-effort). */
function audit(PDO $pdo, string $action, ?string $userId = null, ?string $detail = null): void {
    try {
        $pdo->prepare(
            'INSERT INTO audit_log (id, user_id, action, detail, ip_address, user_agent, created_at)
             VALUES (?, ?, ?, ?, ?, ?, ?)'
        )->execute([
            uuidv4(), $userId, $action,
            $detail !== null ? mb_substr($detail, 0, 500) : null,
            client_ip(), user_agent(), now_utc(),
        ]);
    } catch (Throwable $e) {
        // Auditing must never break the request.
    }
}

function find_user_by_email(PDO $pdo, string $email): ?array {
    $stmt = $pdo->prepare('SELECT * FROM users WHERE email = ?');
    $stmt->execute([strtolower(trim($email))]);
    return $stmt->fetch() ?: null;
}

function find_user_by_id(PDO $pdo, string $id): ?array {
    $stmt = $pdo->prepare('SELECT * FROM users WHERE id = ?');
    $stmt->execute([$id]);
    return $stmt->fetch() ?: null;
}

/** Resolve the authenticated user from the Bearer access token, or send 401/403. */
function require_user(PDO $pdo, array $config): array {
    $token = bearer_token();
    if (!$token) error_out(401, 'invalid_token', 'Missing bearer token.');

    $payload = jwt_decode_verify($token, $config['jwt_secret'], 'access');
    if (!$payload || empty($payload['sub'])) {
        error_out(401, 'invalid_token', 'Invalid or expired token.');
    }

    $user = find_user_by_id($pdo, $payload['sub']);
    if (!$user) error_out(401, 'invalid_token', 'Invalid or expired token.');
    if (!$user['is_active']) error_out(403, 'inactive_user', 'This account is deactivated.');

    return $user;
}
