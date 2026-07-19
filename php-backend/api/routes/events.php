<?php
// Calendar events (Module 12).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function event_public(array $e): array {
    return [
        'id'          => $e['id'],
        'title'       => $e['title'],
        'description' => ($e['description'] ?? '') !== '' ? $e['description'] : null,
        'location'    => ($e['location'] ?? '') !== '' ? $e['location'] : null,
        'start_at'    => iso($e['start_at']),
        'end_at'      => iso($e['end_at'] ?? null),
        'all_day'     => (bool) $e['all_day'],
        'created_at'  => iso($e['created_at']),
        'updated_at'  => iso($e['updated_at']),
    ];
}

route('GET', '/events', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $where = 'user_id = ?'; $args = [$user['id']];
    // Optional window: ?from=ISO&to=ISO
    if (!empty($_GET['from']) && ($f = parse_dt($_GET['from']))) { $where .= ' AND (end_at IS NULL AND start_at >= ? OR end_at >= ?)'; $args[] = $f; $args[] = $f; }
    if (!empty($_GET['to'])   && ($t = parse_dt($_GET['to'])))   { $where .= ' AND start_at <= ?'; $args[] = $t; }
    $stmt = $pdo->prepare("SELECT * FROM events WHERE $where ORDER BY start_at ASC");
    $stmt->execute($args);
    json_out(array_map('event_public', $stmt->fetchAll()), 200);
});

route('POST', '/events', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $title = isset($b['title']) ? trim((string) $b['title']) : '';
    if ($title === '') error_out(422, 'validation_error', 'Event title is required.');
    $start = parse_dt($b['start_at'] ?? null);
    if ($start === null) error_out(422, 'validation_error', 'A valid start_at time is required.');
    $end = parse_dt($b['end_at'] ?? null);
    if ($end !== null && $end < $start) error_out(422, 'validation_error', 'end_at cannot be before start_at.');

    $now = now_utc(); $id = uuidv7();
    $pdo->prepare(
        'INSERT INTO events (id, user_id, title, description, location, start_at, end_at, all_day, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    )->execute([
        $id, $user['id'], mb_substr($title, 0, 300),
        isset($b['description']) && trim((string) $b['description']) !== '' ? (string) $b['description'] : null,
        isset($b['location']) && trim((string) $b['location']) !== '' ? mb_substr(trim((string) $b['location']), 0, 300) : null,
        $start, $end, b_int($b['all_day'] ?? false), $now, $now,
    ]);
    json_out(event_public(own_row($pdo, 'events', $user['id'], $id)), 201);
});

route('PATCH', '/events/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'events', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Event not found.');
    $b = body();

    $fields = []; $values = [];
    if (array_key_exists('title', $b))       { $t = trim((string) $b['title']); if ($t === '') error_out(422, 'validation_error', 'Title cannot be empty.'); $fields[] = 'title = ?'; $values[] = mb_substr($t, 0, 300); }
    if (array_key_exists('description', $b)) { $v = trim((string) $b['description']); $fields[] = 'description = ?'; $values[] = $v !== '' ? (string) $b['description'] : null; }
    if (array_key_exists('location', $b))    { $v = trim((string) $b['location']); $fields[] = 'location = ?'; $values[] = $v !== '' ? mb_substr($v, 0, 300) : null; }
    if (array_key_exists('start_at', $b))    { $s = parse_dt($b['start_at']); if ($s === null) error_out(422, 'validation_error', 'Invalid start_at.'); $fields[] = 'start_at = ?'; $values[] = $s; }
    if (array_key_exists('end_at', $b))      { $fields[] = 'end_at = ?'; $values[] = parse_dt($b['end_at']); }
    if (array_key_exists('all_day', $b))     { $fields[] = 'all_day = ?'; $values[] = b_int($b['all_day']); }
    if (!$fields) error_out(422, 'validation_error', 'Nothing to update.');

    $fields[] = 'updated_at = ?'; $values[] = now_utc(); $values[] = $row['id'];
    $pdo->prepare('UPDATE events SET ' . implode(', ', $fields) . ' WHERE id = ?')->execute($values);
    json_out(event_public(own_row($pdo, 'events', $user['id'], $row['id'])), 200);
});

route('DELETE', '/events/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'events', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Event not found.');
    $pdo->prepare('DELETE FROM events WHERE id = ?')->execute([$row['id']]);
    json_out(['detail' => 'Event deleted.'], 200);
});
