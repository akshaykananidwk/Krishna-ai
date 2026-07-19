<?php
// Notes (Module 7) + Smart Notes AI enhance (Module 8).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function note_public(array $n): array {
    return [
        'id'         => $n['id'],
        'title'      => ($n['title'] ?? '') !== '' ? $n['title'] : null,
        'body'       => $n['body'],
        'color'      => $n['color'] ?? null,
        'pinned'     => (bool) $n['pinned'],
        'created_at' => iso($n['created_at']),
        'updated_at' => iso($n['updated_at']),
    ];
}

route('GET', '/notes', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $limit  = max(1, min(200, (int) ($_GET['limit'] ?? 100)));
    $offset = max(0, (int) ($_GET['offset'] ?? 0));
    $stmt = $pdo->prepare(
        "SELECT * FROM notes WHERE user_id = ?
         ORDER BY pinned DESC, updated_at DESC, id DESC LIMIT $limit OFFSET $offset"
    );
    $stmt->execute([$user['id']]);
    json_out(array_map('note_public', $stmt->fetchAll()), 200);
});

route('POST', '/notes', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $bodyText = isset($b['body']) ? trim((string) $b['body']) : '';
    $title    = isset($b['title']) ? trim((string) $b['title']) : '';
    if ($bodyText === '' && $title === '') error_out(422, 'validation_error', 'A note needs a title or body.');

    $now = now_utc();
    $id = uuidv7();
    $pdo->prepare(
        'INSERT INTO notes (id, user_id, title, body, color, pinned, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
    )->execute([
        $id, $user['id'],
        $title !== '' ? mb_substr($title, 0, 300) : null,
        $bodyText,
        isset($b['color']) ? mb_substr(trim((string) $b['color']), 0, 16) : null,
        b_int($b['pinned'] ?? false),
        $now, $now,
    ]);
    json_out(note_public(own_row($pdo, 'notes', $user['id'], $id)), 201);
});

route('GET', '/notes/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'notes', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Note not found.');
    json_out(note_public($row), 200);
});

route('PATCH', '/notes/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'notes', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Note not found.');
    $b = body();

    $fields = []; $values = [];
    if (array_key_exists('title', $b))  { $fields[] = 'title = ?';  $v = trim((string) $b['title']); $values[] = $v !== '' ? mb_substr($v, 0, 300) : null; }
    if (array_key_exists('body', $b))   { $fields[] = 'body = ?';   $values[] = (string) $b['body']; }
    if (array_key_exists('color', $b))  { $fields[] = 'color = ?';  $v = trim((string) $b['color']); $values[] = $v !== '' ? mb_substr($v, 0, 16) : null; }
    if (array_key_exists('pinned', $b)) { $fields[] = 'pinned = ?'; $values[] = b_int($b['pinned']); }
    if (!$fields) error_out(422, 'validation_error', 'Nothing to update.');

    $fields[] = 'updated_at = ?'; $values[] = now_utc(); $values[] = $row['id'];
    $pdo->prepare('UPDATE notes SET ' . implode(', ', $fields) . ' WHERE id = ?')->execute($values);
    json_out(note_public(own_row($pdo, 'notes', $user['id'], $row['id'])), 200);
});

route('DELETE', '/notes/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'notes', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Note not found.');
    $pdo->prepare('DELETE FROM notes WHERE id = ?')->execute([$row['id']]);
    json_out(['detail' => 'Note deleted.'], 200);
});

// ---- Smart Notes: AI enhance (summarise / clean up / extract action items) ----
route('POST', '/notes/{id}/enhance', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'notes', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Note not found.');
    $b = body();
    $mode = in_array($b['mode'] ?? 'summary', ['summary', 'cleanup', 'action_items'], true)
        ? $b['mode'] : 'summary';

    $instructions = [
        'summary'      => 'Summarise the following note in 2-4 concise bullet points.',
        'cleanup'      => 'Rewrite the following note with clear structure, fixing grammar and spelling. Keep all facts.',
        'action_items' => 'Extract a checklist of concrete action items from the following note. One item per line, starting with "- ".',
    ][$mode];

    $result = gemini_complete(
        $CONFIG,
        'You are a helpful note-taking assistant. Return only the requested output, no preamble.',
        $instructions . "\n\n---\n" . ($row['title'] ? $row['title'] . "\n" : '') . $row['body'],
        1024
    );
    if (!$result['ok']) error_out(502, 'ai_error', $result['error'] ?: 'AI service unavailable.');

    json_out(['mode' => $mode, 'result' => trim($result['text'])], 200);
});
