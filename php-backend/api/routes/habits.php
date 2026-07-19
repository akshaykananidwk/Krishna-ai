<?php
// Habit Tracker (Module 23).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function habit_public(array $h, array $extra = []): array {
    return array_merge([
        'id'         => $h['id'],
        'name'       => $h['name'],
        'schedule'   => $h['schedule'],
        'color'      => $h['color'] ?? null,
        'archived'   => (bool) $h['archived'],
        'created_at' => iso($h['created_at']),
        'updated_at' => iso($h['updated_at']),
    ], $extra);
}

/** Count check-ins and detect whether the habit is checked for today (UTC). */
function habit_stats(PDO $pdo, string $habitId): array {
    $total = (int) $pdo->query('SELECT COUNT(*) FROM habit_checkins WHERE habit_id = ' . $pdo->quote($habitId))->fetchColumn();
    $stmt = $pdo->prepare('SELECT 1 FROM habit_checkins WHERE habit_id = ? AND check_date = ?');
    $stmt->execute([$habitId, gmdate('Y-m-d')]);
    return ['total_checkins' => $total, 'done_today' => (bool) $stmt->fetch()];
}

route('GET', '/habits', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $stmt = $pdo->prepare("SELECT * FROM habits WHERE user_id = ? ORDER BY archived ASC, created_at ASC");
    $stmt->execute([$user['id']]);
    $out = [];
    foreach ($stmt->fetchAll() as $h) $out[] = habit_public($h, habit_stats($pdo, $h['id']));
    json_out($out, 200);
});

route('POST', '/habits', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $name = isset($b['name']) ? trim((string) $b['name']) : '';
    if ($name === '') error_out(422, 'validation_error', 'Habit name is required.');
    $schedule = in_array($b['schedule'] ?? 'daily', ['daily', 'weekly'], true) ? $b['schedule'] : 'daily';

    $now = now_utc(); $id = uuidv7();
    $pdo->prepare(
        'INSERT INTO habits (id, user_id, name, schedule, color, archived, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, 0, ?, ?)'
    )->execute([
        $id, $user['id'], mb_substr($name, 0, 200), $schedule,
        isset($b['color']) ? mb_substr(trim((string) $b['color']), 0, 16) : null, $now, $now,
    ]);
    json_out(habit_public(own_row($pdo, 'habits', $user['id'], $id), habit_stats($pdo, $id)), 201);
});

route('PATCH', '/habits/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'habits', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Habit not found.');
    $b = body();

    $fields = []; $values = [];
    if (array_key_exists('name', $b))     { $n = trim((string) $b['name']); if ($n === '') error_out(422, 'validation_error', 'Name cannot be empty.'); $fields[] = 'name = ?'; $values[] = mb_substr($n, 0, 200); }
    if (array_key_exists('schedule', $b)) { if (!in_array($b['schedule'], ['daily', 'weekly'], true)) error_out(422, 'validation_error', 'schedule must be daily or weekly.'); $fields[] = 'schedule = ?'; $values[] = $b['schedule']; }
    if (array_key_exists('color', $b))    { $v = trim((string) $b['color']); $fields[] = 'color = ?'; $values[] = $v !== '' ? mb_substr($v, 0, 16) : null; }
    if (array_key_exists('archived', $b)) { $fields[] = 'archived = ?'; $values[] = b_int($b['archived']); }
    if (!$fields) error_out(422, 'validation_error', 'Nothing to update.');

    $fields[] = 'updated_at = ?'; $values[] = now_utc(); $values[] = $row['id'];
    $pdo->prepare('UPDATE habits SET ' . implode(', ', $fields) . ' WHERE id = ?')->execute($values);
    json_out(habit_public(own_row($pdo, 'habits', $user['id'], $row['id']), habit_stats($pdo, $row['id'])), 200);
});

route('DELETE', '/habits/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'habits', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Habit not found.');
    $pdo->prepare('DELETE FROM habits WHERE id = ?')->execute([$row['id']]);
    json_out(['detail' => 'Habit deleted.'], 200);
});

// ---- Toggle today's check-in (or a given ?date=YYYY-MM-DD) ----
route('POST', '/habits/{id}/check', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'habits', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Habit not found.');
    $b = body();
    $date = parse_date($b['date'] ?? null) ?? gmdate('Y-m-d');

    $stmt = $pdo->prepare('SELECT id FROM habit_checkins WHERE habit_id = ? AND check_date = ?');
    $stmt->execute([$row['id'], $date]);
    $existing = $stmt->fetch();
    if ($existing) {
        $pdo->prepare('DELETE FROM habit_checkins WHERE id = ?')->execute([$existing['id']]);
        $checked = false;
    } else {
        $pdo->prepare('INSERT INTO habit_checkins (id, habit_id, user_id, check_date, created_at) VALUES (?, ?, ?, ?, ?)')
            ->execute([uuidv7(), $row['id'], $user['id'], $date, now_utc()]);
        $checked = true;
    }
    json_out(habit_public($row, array_merge(habit_stats($pdo, $row['id']), ['date' => $date, 'checked' => $checked])), 200);
});
