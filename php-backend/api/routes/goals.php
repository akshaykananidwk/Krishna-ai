<?php
// Goals (Module 24).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function goal_public(array $g): array {
    return [
        'id'          => $g['id'],
        'title'       => $g['title'],
        'description' => ($g['description'] ?? '') !== '' ? $g['description'] : null,
        'target_date' => $g['target_date'] ?: null,
        'progress'    => (int) $g['progress'],
        'status'      => $g['status'],
        'created_at'  => iso($g['created_at']),
        'updated_at'  => iso($g['updated_at']),
    ];
}

route('GET', '/goals', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $where = 'user_id = ?'; $args = [$user['id']];
    if (!empty($_GET['status'])) { $where .= ' AND status = ?'; $args[] = (string) $_GET['status']; }
    $stmt = $pdo->prepare("SELECT * FROM goals WHERE $where ORDER BY (status='active') DESC, (target_date IS NULL) ASC, target_date ASC, created_at DESC");
    $stmt->execute($args);
    json_out(array_map('goal_public', $stmt->fetchAll()), 200);
});

route('POST', '/goals', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $title = isset($b['title']) ? trim((string) $b['title']) : '';
    if ($title === '') error_out(422, 'validation_error', 'Goal title is required.');

    $now = now_utc(); $id = uuidv7();
    $pdo->prepare(
        'INSERT INTO goals (id, user_id, title, description, target_date, progress, status, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
    )->execute([
        $id, $user['id'], mb_substr($title, 0, 300),
        isset($b['description']) && trim((string) $b['description']) !== '' ? (string) $b['description'] : null,
        parse_date($b['target_date'] ?? null),
        max(0, min(100, (int) ($b['progress'] ?? 0))),
        'active', $now, $now,
    ]);
    json_out(goal_public(own_row($pdo, 'goals', $user['id'], $id)), 201);
});

route('PATCH', '/goals/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'goals', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Goal not found.');
    $b = body();

    $fields = []; $values = [];
    if (array_key_exists('title', $b))       { $t = trim((string) $b['title']); if ($t === '') error_out(422, 'validation_error', 'Title cannot be empty.'); $fields[] = 'title = ?'; $values[] = mb_substr($t, 0, 300); }
    if (array_key_exists('description', $b)) { $v = trim((string) $b['description']); $fields[] = 'description = ?'; $values[] = $v !== '' ? (string) $b['description'] : null; }
    if (array_key_exists('target_date', $b)) { $fields[] = 'target_date = ?'; $values[] = parse_date($b['target_date']); }
    if (array_key_exists('progress', $b))    { $fields[] = 'progress = ?'; $values[] = max(0, min(100, (int) $b['progress'])); }
    if (array_key_exists('status', $b))      { if (!in_array($b['status'], ['active', 'done', 'archived'], true)) error_out(422, 'validation_error', 'status must be active, done or archived.'); $fields[] = 'status = ?'; $values[] = $b['status']; }
    if (!$fields) error_out(422, 'validation_error', 'Nothing to update.');

    $fields[] = 'updated_at = ?'; $values[] = now_utc(); $values[] = $row['id'];
    $pdo->prepare('UPDATE goals SET ' . implode(', ', $fields) . ' WHERE id = ?')->execute($values);
    json_out(goal_public(own_row($pdo, 'goals', $user['id'], $row['id'])), 200);
});

route('DELETE', '/goals/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'goals', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Goal not found.');
    $pdo->prepare('DELETE FROM goals WHERE id = ?')->execute([$row['id']]);
    json_out(['detail' => 'Goal deleted.'], 200);
});
