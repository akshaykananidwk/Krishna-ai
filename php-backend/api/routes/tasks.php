<?php
// Tasks (Module 10).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function task_public(array $t): array {
    return [
        'id'           => $t['id'],
        'title'        => $t['title'],
        'notes'        => ($t['notes'] ?? '') !== '' ? $t['notes'] : null,
        'priority'     => (int) $t['priority'],
        'is_done'      => (bool) $t['is_done'],
        'due_at'       => iso($t['due_at'] ?? null),
        'completed_at' => iso($t['completed_at'] ?? null),
        'created_at'   => iso($t['created_at']),
        'updated_at'   => iso($t['updated_at']),
    ];
}

route('GET', '/tasks', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $where = 'user_id = ?'; $args = [$user['id']];
    if (isset($_GET['done'])) { $where .= ' AND is_done = ?'; $args[] = b_int($_GET['done']); }
    $stmt = $pdo->prepare(
        "SELECT * FROM tasks WHERE $where
         ORDER BY is_done ASC, (due_at IS NULL) ASC, due_at ASC, priority DESC, created_at DESC"
    );
    $stmt->execute($args);
    json_out(array_map('task_public', $stmt->fetchAll()), 200);
});

route('POST', '/tasks', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $title = isset($b['title']) ? trim((string) $b['title']) : '';
    if ($title === '') error_out(422, 'validation_error', 'Task title is required.');

    $priority = (int) ($b['priority'] ?? 1);
    $priority = max(0, min(2, $priority));
    $now = now_utc();
    $id = uuidv7();
    $pdo->prepare(
        'INSERT INTO tasks (id, user_id, title, notes, priority, is_done, due_at, completed_at, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, 0, ?, NULL, ?, ?)'
    )->execute([
        $id, $user['id'], mb_substr($title, 0, 300),
        isset($b['notes']) ? (string) $b['notes'] : null,
        $priority, parse_dt($b['due_at'] ?? null), $now, $now,
    ]);
    json_out(task_public(own_row($pdo, 'tasks', $user['id'], $id)), 201);
});

route('PATCH', '/tasks/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'tasks', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Task not found.');
    $b = body();

    $fields = []; $values = [];
    if (array_key_exists('title', $b))    { $t = trim((string) $b['title']); if ($t === '') error_out(422, 'validation_error', 'Title cannot be empty.'); $fields[] = 'title = ?'; $values[] = mb_substr($t, 0, 300); }
    if (array_key_exists('notes', $b))    { $fields[] = 'notes = ?';    $values[] = ($b['notes'] === null || $b['notes'] === '') ? null : (string) $b['notes']; }
    if (array_key_exists('priority', $b)) { $fields[] = 'priority = ?'; $values[] = max(0, min(2, (int) $b['priority'])); }
    if (array_key_exists('due_at', $b))   { $fields[] = 'due_at = ?';   $values[] = parse_dt($b['due_at']); }
    if (array_key_exists('is_done', $b)) {
        $done = b_int($b['is_done']);
        $fields[] = 'is_done = ?';      $values[] = $done;
        $fields[] = 'completed_at = ?'; $values[] = $done ? now_utc() : null;
    }
    if (!$fields) error_out(422, 'validation_error', 'Nothing to update.');

    $fields[] = 'updated_at = ?'; $values[] = now_utc(); $values[] = $row['id'];
    $pdo->prepare('UPDATE tasks SET ' . implode(', ', $fields) . ' WHERE id = ?')->execute($values);
    json_out(task_public(own_row($pdo, 'tasks', $user['id'], $row['id'])), 200);
});

route('DELETE', '/tasks/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'tasks', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Task not found.');
    $pdo->prepare('DELETE FROM tasks WHERE id = ?')->execute([$row['id']]);
    json_out(['detail' => 'Task deleted.'], 200);
});
