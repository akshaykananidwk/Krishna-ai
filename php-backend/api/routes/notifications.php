<?php
// Notifications (Module 25): device push-token registration + in-app feed.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function notification_public(array $n): array {
    return [
        'id'         => $n['id'],
        'title'      => $n['title'],
        'body'       => ($n['body'] ?? '') !== '' ? $n['body'] : null,
        'type'       => $n['type'],
        'is_read'    => (bool) $n['is_read'],
        'created_at' => iso($n['created_at']),
    ];
}

// ---- Register / refresh a device push token ----
route('POST', '/notifications/token', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $token = isset($b['token']) ? trim((string) $b['token']) : '';
    if ($token === '') error_out(422, 'validation_error', 'A device token is required.');
    $platform = in_array($b['platform'] ?? 'android', ['android', 'ios', 'web'], true) ? $b['platform'] : 'android';

    // Move the token to this user (tokens are globally unique).
    $stmt = $pdo->prepare('SELECT id FROM device_tokens WHERE token = ?');
    $stmt->execute([$token]);
    if ($row = $stmt->fetch()) {
        $pdo->prepare('UPDATE device_tokens SET user_id = ?, platform = ? WHERE id = ?')
            ->execute([$user['id'], $platform, $row['id']]);
    } else {
        $pdo->prepare('INSERT INTO device_tokens (id, user_id, token, platform, created_at) VALUES (?, ?, ?, ?, ?)')
            ->execute([uuidv7(), $user['id'], mb_substr($token, 0, 512), $platform, now_utc()]);
    }
    json_out(['detail' => 'Device registered for notifications.'], 200);
});

route('DELETE', '/notifications/token', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $token = isset($b['token']) ? trim((string) $b['token']) : '';
    if ($token !== '') {
        $pdo->prepare('DELETE FROM device_tokens WHERE user_id = ? AND token = ?')
            ->execute([$user['id'], $token]);
    }
    json_out(['detail' => 'Device unregistered.'], 200);
});

// ---- In-app notification feed ----
route('GET', '/notifications', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $limit = max(1, min(100, (int) ($_GET['limit'] ?? 50)));
    $stmt = $pdo->prepare("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT $limit");
    $stmt->execute([$user['id']]);
    $items = array_map('notification_public', $stmt->fetchAll());

    $cnt = $pdo->prepare('SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0');
    $cnt->execute([$user['id']]);
    json_out(['unread' => (int) $cnt->fetchColumn(), 'notifications' => $items], 200);
});

route('POST', '/notifications/{id}/read', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'notifications', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Notification not found.');
    $pdo->prepare('UPDATE notifications SET is_read = 1 WHERE id = ?')->execute([$row['id']]);
    json_out(['detail' => 'Marked as read.'], 200);
});

route('POST', '/notifications/read-all', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $pdo->prepare('UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0')->execute([$user['id']]);
    json_out(['detail' => 'All notifications marked as read.'], 200);
});
