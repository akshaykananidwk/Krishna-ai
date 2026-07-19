<?php
// Reminders (Module 11).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function reminder_public(array $r): array {
    return [
        'id'         => $r['id'],
        'title'      => $r['title'],
        'remind_at'  => iso($r['remind_at']),
        'is_done'    => (bool) $r['is_done'],
        'created_at' => iso($r['created_at']),
        'updated_at' => iso($r['updated_at']),
    ];
}

route('GET', '/reminders', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $where = 'user_id = ?'; $args = [$user['id']];
    if (isset($_GET['done'])) { $where .= ' AND is_done = ?'; $args[] = b_int($_GET['done']); }
    $stmt = $pdo->prepare("SELECT * FROM reminders WHERE $where ORDER BY is_done ASC, remind_at ASC");
    $stmt->execute($args);
    json_out(array_map('reminder_public', $stmt->fetchAll()), 200);
});

route('POST', '/reminders', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $title = isset($b['title']) ? trim((string) $b['title']) : '';
    if ($title === '') error_out(422, 'validation_error', 'Reminder title is required.');
    $when = parse_dt($b['remind_at'] ?? null);
    if ($when === null) error_out(422, 'validation_error', 'A valid remind_at time is required.');

    $now = now_utc(); $id = uuidv7();
    $pdo->prepare(
        'INSERT INTO reminders (id, user_id, title, remind_at, is_done, created_at, updated_at)
         VALUES (?, ?, ?, ?, 0, ?, ?)'
    )->execute([$id, $user['id'], mb_substr($title, 0, 300), $when, $now, $now]);
    json_out(reminder_public(own_row($pdo, 'reminders', $user['id'], $id)), 201);
});

route('PATCH', '/reminders/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'reminders', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Reminder not found.');
    $b = body();

    $fields = []; $values = [];
    if (array_key_exists('title', $b))     { $t = trim((string) $b['title']); if ($t === '') error_out(422, 'validation_error', 'Title cannot be empty.'); $fields[] = 'title = ?'; $values[] = mb_substr($t, 0, 300); }
    if (array_key_exists('remind_at', $b)) { $w = parse_dt($b['remind_at']); if ($w === null) error_out(422, 'validation_error', 'Invalid remind_at time.'); $fields[] = 'remind_at = ?'; $values[] = $w; }
    if (array_key_exists('is_done', $b))   { $fields[] = 'is_done = ?'; $values[] = b_int($b['is_done']); }
    if (!$fields) error_out(422, 'validation_error', 'Nothing to update.');

    $fields[] = 'updated_at = ?'; $values[] = now_utc(); $values[] = $row['id'];
    $pdo->prepare('UPDATE reminders SET ' . implode(', ', $fields) . ' WHERE id = ?')->execute($values);
    json_out(reminder_public(own_row($pdo, 'reminders', $user['id'], $row['id'])), 200);
});

route('DELETE', '/reminders/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'reminders', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Reminder not found.');
    $pdo->prepare('DELETE FROM reminders WHERE id = ?')->execute([$row['id']]);
    json_out(['detail' => 'Reminder deleted.'], 200);
});
