<?php
// Privacy Controls (Module 29), Backup & Restore (Module 30), Cloud Sync (Module 27).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

/** Tables that hold a user's own data, keyed by user_id. */
const USER_DATA_TABLES = ['notes', 'tasks', 'reminders', 'events', 'habits', 'goals', 'memories', 'meetings', 'conversations', 'messages'];

/** Gather every row a user owns, table by table. */
function collect_user_data(PDO $pdo, array $user): array {
    $out = ['profile' => [
        'email'     => $user['email'],
        'full_name' => $user['full_name'],
        'bio'       => $user['bio'] ?? null,
        'timezone'  => $user['timezone'] ?? null,
        'created_at'=> iso($user['created_at']),
    ]];
    foreach (['notes', 'tasks', 'reminders', 'events', 'habits', 'goals', 'memories', 'meetings', 'conversations'] as $t) {
        $stmt = $pdo->prepare("SELECT * FROM $t WHERE user_id = ?");
        $stmt->execute([$user['id']]);
        $out[$t] = $stmt->fetchAll();
    }
    // Messages belong to the user's conversations.
    $stmt = $pdo->prepare(
        'SELECT m.* FROM messages m JOIN conversations c ON c.id = m.conversation_id WHERE c.user_id = ?'
    );
    $stmt->execute([$user['id']]);
    $out['messages'] = $stmt->fetchAll();
    return $out;
}

// ---- Export all my data (privacy / GDPR) ----
route('GET', '/account/export', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    audit($pdo, 'data_export', $user['id']);
    json_out([
        'exported_at' => iso(now_utc()),
        'version'     => 1,
        'data'        => collect_user_data($pdo, $user),
    ], 200);
});

// ---- Full backup (same payload, intended for re-import) ----
route('GET', '/backup', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    json_out([
        'created_at' => iso(now_utc()),
        'version'    => 1,
        'data'       => collect_user_data($pdo, $user),
    ], 200);
});

// ---- Restore notes/tasks/reminders/events/goals/habits/memories from a backup ----
route('POST', '/restore', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $data = $b['data'] ?? $b;   // accept a raw backup or {data:{...}}
    if (!is_array($data)) error_out(422, 'validation_error', 'Invalid backup payload.');

    $counts = [];
    $now = now_utc();

    $insert = function (string $sql, array $rows, callable $map) use ($pdo, $user, &$counts, $now) {
        $n = 0;
        foreach ($rows as $r) {
            if (!is_array($r)) continue;
            $stmt = $pdo->prepare($sql);
            $stmt->execute(array_merge([uuidv7(), $user['id']], $map($r), [$now, $now]));
            $n++;
        }
        return $n;
    };

    if (!empty($data['notes']) && is_array($data['notes'])) {
        $counts['notes'] = $insert(
            'INSERT INTO notes (id, user_id, title, body, color, pinned, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            $data['notes'],
            fn($r) => [isset($r['title']) ? mb_substr((string) $r['title'], 0, 300) : null, (string) ($r['body'] ?? ''), $r['color'] ?? null, b_int($r['pinned'] ?? 0)]
        );
    }
    if (!empty($data['tasks']) && is_array($data['tasks'])) {
        $counts['tasks'] = $insert(
            'INSERT INTO tasks (id, user_id, title, notes, priority, is_done, due_at, completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)',
            $data['tasks'],
            fn($r) => [mb_substr((string) ($r['title'] ?? 'Untitled'), 0, 300), $r['notes'] ?? null, max(0, min(2, (int) ($r['priority'] ?? 1))), b_int($r['is_done'] ?? 0), parse_dt($r['due_at'] ?? null)]
        );
    }
    if (!empty($data['reminders']) && is_array($data['reminders'])) {
        $counts['reminders'] = $insert(
            'INSERT INTO reminders (id, user_id, title, remind_at, is_done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            $data['reminders'],
            fn($r) => [mb_substr((string) ($r['title'] ?? 'Reminder'), 0, 300), parse_dt($r['remind_at'] ?? null) ?? now_utc(), b_int($r['is_done'] ?? 0)]
        );
    }
    if (!empty($data['events']) && is_array($data['events'])) {
        $counts['events'] = $insert(
            'INSERT INTO events (id, user_id, title, description, location, start_at, end_at, all_day, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            $data['events'],
            fn($r) => [mb_substr((string) ($r['title'] ?? 'Event'), 0, 300), $r['description'] ?? null, isset($r['location']) ? mb_substr((string) $r['location'], 0, 300) : null, parse_dt($r['start_at'] ?? null) ?? now_utc(), parse_dt($r['end_at'] ?? null), b_int($r['all_day'] ?? 0)]
        );
    }
    if (!empty($data['goals']) && is_array($data['goals'])) {
        $counts['goals'] = $insert(
            'INSERT INTO goals (id, user_id, title, description, target_date, progress, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            $data['goals'],
            fn($r) => [mb_substr((string) ($r['title'] ?? 'Goal'), 0, 300), $r['description'] ?? null, parse_date($r['target_date'] ?? null), max(0, min(100, (int) ($r['progress'] ?? 0))), in_array($r['status'] ?? 'active', ['active', 'done', 'archived'], true) ? $r['status'] : 'active']
        );
    }
    if (!empty($data['memories']) && is_array($data['memories'])) {
        $counts['memories'] = 0;
        foreach ($data['memories'] as $r) {
            if (!is_array($r)) continue;
            $tags = isset($r['tags']) && is_array($r['tags']) ? json_encode(array_values(array_map('strval', $r['tags']))) : '[]';
            $pdo->prepare(
                "INSERT INTO memories (id, user_id, source_type, source_ref, title, content, tags, importance, pinned, status, access_count, created_at, updated_at)
                 VALUES (?, ?, ?, NULL, ?, ?, ?, 0.5, ?, 'active', 0, ?, ?)"
            )->execute([uuidv7(), $user['id'], mb_substr((string) ($r['source_type'] ?? 'note'), 0, 32), $r['title'] ?? null, (string) ($r['content'] ?? ''), $tags, b_int($r['pinned'] ?? 0), $now, $now]);
            $counts['memories']++;
        }
    }

    audit($pdo, 'data_restore', $user['id']);
    json_out(['detail' => 'Backup restored.', 'imported' => $counts], 200);
});

// ---- Delete my account and all data (irreversible) ----
route('DELETE', '/account', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    if (!password_verify((string) ($b['password'] ?? ''), $user['password_hash'] ?? '')) {
        error_out(400, 'invalid_credentials', 'Password confirmation is incorrect.');
    }
    audit($pdo, 'account_delete', $user['id']);
    // FK ON DELETE CASCADE removes all owned rows.
    $pdo->prepare('DELETE FROM users WHERE id = ?')->execute([$user['id']]);
    json_out(['detail' => 'Your account and all data have been deleted.'], 200);
});

// ---- Pull sync: everything changed since ?since=ISO (Cloud Sync) ----
route('GET', '/sync', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $since = parse_dt($_GET['since'] ?? null) ?? '1970-01-01 00:00:00';

    $shapers = [
        'notes'     => 'note_public',
        'tasks'     => 'task_public',
        'reminders' => 'reminder_public',
        'events'    => 'event_public',
        'goals'     => 'goal_public',
    ];
    $out = ['since' => iso($since), 'now' => iso(now_utc()), 'changes' => []];
    foreach ($shapers as $table => $shaper) {
        $stmt = $pdo->prepare("SELECT * FROM $table WHERE user_id = ? AND updated_at > ? ORDER BY updated_at ASC");
        $stmt->execute([$user['id'], $since]);
        $out['changes'][$table] = array_map($shaper, $stmt->fetchAll());
    }
    json_out($out, 200);
});
