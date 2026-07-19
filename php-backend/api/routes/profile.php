<?php
// User Profile (Module 2) + per-user Settings (Module 28).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function profile_public(array $u): array {
    return [
        'id'            => $u['id'],
        'email'         => $u['email'],
        'full_name'     => $u['full_name'],
        'avatar_url'    => $u['avatar_url'] ?? null,
        'bio'           => $u['bio'] ?? null,
        'timezone'      => $u['timezone'] ?? null,
        'is_active'     => (bool) $u['is_active'],
        'is_verified'   => (bool) $u['is_verified'],
        'created_at'    => iso($u['created_at']),
        'last_login_at' => iso($u['last_login_at'] ?? null),
    ];
}

route('GET', '/profile', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    json_out(profile_public($user), 200);
});

route('PATCH', '/profile', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();

    $fields = [];
    $values = [];
    if (array_key_exists('full_name', $b)) {
        $fields[] = 'full_name = ?';
        $v = trim((string) $b['full_name']);
        $values[] = $v !== '' ? mb_substr($v, 0, 255) : null;
    }
    if (array_key_exists('bio', $b)) {
        $fields[] = 'bio = ?';
        $v = trim((string) $b['bio']);
        $values[] = $v !== '' ? mb_substr($v, 0, 500) : null;
    }
    if (array_key_exists('timezone', $b)) {
        $fields[] = 'timezone = ?';
        $v = trim((string) $b['timezone']);
        $values[] = $v !== '' ? mb_substr($v, 0, 64) : null;
    }
    if (array_key_exists('avatar_url', $b)) {
        $fields[] = 'avatar_url = ?';
        $v = trim((string) $b['avatar_url']);
        $values[] = $v !== '' ? mb_substr($v, 0, 512) : null;
    }
    if (!$fields) error_out(422, 'validation_error', 'No profile fields to update.');

    $fields[] = 'updated_at = ?';
    $values[] = now_utc();
    $values[] = $user['id'];
    $pdo->prepare('UPDATE users SET ' . implode(', ', $fields) . ' WHERE id = ?')->execute($values);

    json_out(profile_public(find_user_by_id($pdo, $user['id'])), 200);
});

route('POST', '/profile/password', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $current = (string) ($b['current_password'] ?? '');
    $new     = (string) ($b['new_password'] ?? '');

    if (!password_verify($current, $user['password_hash'] ?? '')) {
        error_out(400, 'invalid_credentials', 'Your current password is incorrect.');
    }
    if ($err = password_error($new)) error_out(422, 'validation_error', $err);

    $pdo->prepare('UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?')
        ->execute([password_hash($new, PASSWORD_BCRYPT), now_utc(), $user['id']]);

    // Force other sessions to re-authenticate.
    $pdo->prepare('UPDATE refresh_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL')
        ->execute([now_utc(), $user['id']]);

    audit($pdo, 'password_change', $user['id']);
    json_out(['detail' => 'Password updated. Please sign in again on other devices.'], 200);
});

// ---- Settings: a single JSON object per user ----
route('GET', '/settings', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $stmt = $pdo->prepare('SELECT data FROM user_settings WHERE user_id = ?');
    $stmt->execute([$user['id']]);
    $row = $stmt->fetch();
    $data = $row && $row['data'] ? json_decode($row['data'], true) : [];
    json_out(is_array($data) ? $data : [], 200);
});

route('PUT', '/settings', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $json = json_encode($b, JSON_UNESCAPED_UNICODE);
    $now = now_utc();
    // UPSERT that works on both MySQL and SQLite.
    $stmt = $pdo->prepare('SELECT user_id FROM user_settings WHERE user_id = ?');
    $stmt->execute([$user['id']]);
    if ($stmt->fetch()) {
        $pdo->prepare('UPDATE user_settings SET data = ?, updated_at = ? WHERE user_id = ?')
            ->execute([$json, $now, $user['id']]);
    } else {
        $pdo->prepare('INSERT INTO user_settings (user_id, data, updated_at) VALUES (?, ?, ?)')
            ->execute([$user['id'], $json, $now]);
    }
    json_out(is_array($b) ? $b : [], 200);
});
