<?php
// AI text helpers: Meeting Summaries (Module 9) + Email Assistant (Module 20).
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

function meeting_public(array $m): array {
    $items = [];
    if (!empty($m['action_items'])) {
        $decoded = json_decode($m['action_items'], true);
        if (is_array($decoded)) $items = array_values(array_map('strval', $decoded));
    }
    return [
        'id'           => $m['id'],
        'title'        => $m['title'],
        'transcript'   => $m['transcript'],
        'summary'      => $m['summary'] ?: null,
        'action_items' => $items,
        'created_at'   => iso($m['created_at']),
        'updated_at'   => iso($m['updated_at']),
    ];
}

route('GET', '/meetings', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $stmt = $pdo->prepare('SELECT * FROM meetings WHERE user_id = ? ORDER BY created_at DESC, id DESC');
    $stmt->execute([$user['id']]);
    json_out(array_map('meeting_public', $stmt->fetchAll()), 200);
});

route('GET', '/meetings/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'meetings', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Meeting not found.');
    json_out(meeting_public($row), 200);
});

// Create a meeting from a transcript and generate a summary + action items.
route('POST', '/meetings', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $transcript = isset($b['transcript']) ? trim((string) $b['transcript']) : '';
    if ($transcript === '') error_out(422, 'validation_error', 'A meeting transcript is required.');
    $title = isset($b['title']) && trim((string) $b['title']) !== ''
        ? mb_substr(trim((string) $b['title']), 0, 300) : 'Meeting ' . gmdate('Y-m-d H:i');

    $summary = null; $actionItems = [];
    if (($b['summarize'] ?? true)) {
        $res = gemini_complete(
            $CONFIG,
            'You summarise meeting transcripts. Reply with a short paragraph summary, then a line "ACTIONS:" followed by action items each starting with "- ". If there are no action items, write "- none".',
            "Summarise this meeting transcript:\n\n" . $transcript,
            1500
        );
        if ($res['ok']) {
            $text = trim($res['text']);
            if (preg_match('/ACTIONS:\s*(.*)$/is', $text, $mm)) {
                $summary = trim(substr($text, 0, strpos($text, $mm[0])));
                foreach (preg_split('/\r?\n/', $mm[1]) as $line) {
                    $line = trim(ltrim(trim($line), '-*• '));
                    if ($line !== '' && strtolower($line) !== 'none') $actionItems[] = $line;
                }
            } else {
                $summary = $text;
            }
        }
    }

    $now = now_utc(); $id = uuidv7();
    $pdo->prepare(
        'INSERT INTO meetings (id, user_id, title, transcript, summary, action_items, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
    )->execute([$id, $user['id'], $title, $transcript, $summary, json_encode($actionItems, JSON_UNESCAPED_UNICODE), $now, $now]);
    json_out(meeting_public(own_row($pdo, 'meetings', $user['id'], $id)), 201);
});

route('DELETE', '/meetings/{id}', function ($p) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $row = own_row($pdo, 'meetings', $user['id'], $p[0]);
    if (!$row) error_out(404, 'not_found', 'Meeting not found.');
    $pdo->prepare('DELETE FROM meetings WHERE id = ?')->execute([$row['id']]);
    json_out(['detail' => 'Meeting deleted.'], 200);
});

// ---- Email Assistant: draft or reply to an email (not persisted) ----
route('POST', '/ai/email', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $prompt = isset($b['prompt']) ? trim((string) $b['prompt']) : '';
    if ($prompt === '') error_out(422, 'validation_error', 'Describe the email you want (prompt).');
    $tone    = isset($b['tone']) ? preg_replace('/[^a-zA-Z ]/', '', (string) $b['tone']) : 'professional';
    $context = isset($b['context']) ? trim((string) $b['context']) : '';

    $sys = 'You are an expert email assistant. Write a ready-to-send email in a '
         . ($tone !== '' ? $tone : 'professional') . ' tone. Return only the email (optional Subject line, then body), no commentary.';
    $userMsg = $prompt;
    if ($context !== '') $userMsg .= "\n\nEmail to reply to / context:\n" . $context;

    $res = gemini_complete($CONFIG, $sys, $userMsg, 1200);
    if (!$res['ok']) error_out(502, 'ai_error', $res['error'] ?: 'AI service unavailable.');
    json_out(['result' => trim($res['text'])], 200);
});
