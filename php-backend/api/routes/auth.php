<?php
// Auth endpoints. JSON shapes match exactly what the Flutter app expects.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

// A valid bcrypt hash of a random value, verified on the "user not found" path so
// login timing does not reveal which emails are registered.
const DUMMY_HASH = '$2y$12$HoKzBQEUQiC.mUA14T2wBesnXBFynw9MefnRLao78/pNXhIj0tAqC';

route('POST', '/auth/register', function () {
    global $pdo, $CONFIG;
    $b = body();
    $email = strtolower(trim($b['email'] ?? ''));
    $password = $b['password'] ?? '';
    $fullName = isset($b['full_name']) ? trim((string) $b['full_name']) : null;

    if (!valid_email($email)) error_out(422, 'validation_error', 'Enter a valid email address.');
    if ($err = password_error($password)) error_out(422, 'validation_error', $err);

    if (find_user_by_email($pdo, $email)) {
        error_out(409, 'email_already_registered', 'An account with this email already exists.');
    }

    $now = now_utc();
    $id = uuidv4();
    $pdo->prepare(
        'INSERT INTO users (id, email, password_hash, full_name, is_active, is_verified, is_admin, created_at, updated_at, last_login_at)
         VALUES (?, ?, ?, ?, 1, 0, 0, ?, ?, ?)'
    )->execute([$id, $email, password_hash($password, PASSWORD_BCRYPT), $fullName ?: null, $now, $now, $now]);

    $user = find_user_by_id($pdo, $id);
    $tokens = issue_tokens($pdo, $CONFIG, $user);
    audit($pdo, 'register', $id);

    json_out([
        'access_token'  => $tokens['access'],
        'refresh_token' => $tokens['refresh'],
        'token_type'    => 'bearer',
        'user'          => public_user($user),
    ], 201);
});

route('POST', '/auth/login', function () {
    global $pdo, $CONFIG;
    $b = body();
    $email = strtolower(trim($b['email'] ?? ''));
    $password = $b['password'] ?? '';

    $user = find_user_by_email($pdo, $email);
    $hash = ($user && $user['password_hash']) ? $user['password_hash'] : DUMMY_HASH;
    $ok = password_verify($password, $hash);

    if (!$user || !$ok) {
        audit($pdo, 'login_failed', $user['id'] ?? null, $email);
        error_out(401, 'invalid_credentials', 'The email or password is incorrect.');
    }
    if (!$user['is_active']) error_out(403, 'inactive_user', 'This account is deactivated.');

    $pdo->prepare('UPDATE users SET last_login_at = ? WHERE id = ?')->execute([now_utc(), $user['id']]);
    $user['last_login_at'] = now_utc();

    $tokens = issue_tokens($pdo, $CONFIG, $user);
    audit($pdo, 'login', $user['id']);

    json_out([
        'access_token'  => $tokens['access'],
        'refresh_token' => $tokens['refresh'],
        'token_type'    => 'bearer',
        'user'          => public_user($user),
    ], 200);
});

route('POST', '/auth/refresh', function () {
    global $pdo, $CONFIG;
    $b = body();
    $raw = $b['refresh_token'] ?? '';

    $payload = jwt_decode_verify((string) $raw, $CONFIG['jwt_secret'], 'refresh');
    if (!$payload) error_out(401, 'invalid_token', 'Refresh token is invalid or expired.');

    $row = active_refresh_row($pdo, $raw);
    if (!$row) error_out(401, 'invalid_token', 'Refresh token has been revoked or is unknown.');

    $user = find_user_by_id($pdo, $row['user_id']);
    if (!$user || !$user['is_active']) error_out(401, 'invalid_token', 'Refresh token is invalid.');

    // Rotate: revoke the presented token, issue a fresh pair.
    revoke_refresh($pdo, $row['id']);
    $tokens = issue_tokens($pdo, $CONFIG, $user);
    audit($pdo, 'token_refresh', $user['id']);

    json_out([
        'access_token'  => $tokens['access'],
        'refresh_token' => $tokens['refresh'],
        'token_type'    => 'bearer',
    ], 200);
});

route('POST', '/auth/logout', function () {
    global $pdo;
    $b = body();
    $raw = $b['refresh_token'] ?? '';
    $row = active_refresh_row($pdo, (string) $raw);
    if ($row) {
        revoke_refresh($pdo, $row['id']);
        audit($pdo, 'logout', $row['user_id']);
    }
    json_out(['detail' => 'Logged out successfully.'], 200);
});

route('GET', '/auth/me', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    json_out(public_user($user), 200);
});
