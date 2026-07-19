<?php
// AI Chat endpoints (conversations + streaming messages).
// JSON shapes and SSE frames match exactly what the Flutter app parses.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

// The assistant's persona / behaviour.
const CHAT_SYSTEM_PROMPT =
    "You are Krishna, a warm, concise and genuinely helpful personal AI assistant. " .
    "Answer clearly and directly. Use plain language. When you are unsure, say so.";
const CHAT_MAX_TOKENS = 2048;

/** Shape a conversation row the way the Flutter app expects. */
function conversation_public(array $c): array {
    return [
        'id'              => $c['id'],
        'title'           => $c['title'],
        'last_message_at' => iso($c['last_message_at'] ?? null),
        'created_at'      => iso($c['created_at']),
        'updated_at'      => iso($c['updated_at']),
    ];
}

/** Shape a message row the way the Flutter app expects. */
function message_public(array $m): array {
    return [
        'id'         => $m['id'],
        'role'       => $m['role'],
        'content'    => $m['content'],
        'model'      => $m['model'] ?? null,
        'created_at' => iso($m['created_at']),
    ];
}

/** Fetch a conversation owned by this user, or send 404. */
function require_conversation(PDO $pdo, string $userId, string $id): array {
    $stmt = $pdo->prepare('SELECT * FROM conversations WHERE id = ? AND user_id = ?');
    $stmt->execute([$id, $userId]);
    $row = $stmt->fetch();
    if (!$row) error_out(404, 'not_found', 'Conversation not found.');
    return $row;
}

// ---- Create a conversation ----
route('POST', '/chat/conversations', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $b = body();
    $title = isset($b['title']) ? trim((string) $b['title']) : '';
    if ($title === '') $title = 'New chat';
    $title = mb_substr($title, 0, 200);

    $now = now_utc();
    $id = uuidv7();
    $pdo->prepare(
        'INSERT INTO conversations (id, user_id, title, last_message_at, created_at, updated_at)
         VALUES (?, ?, ?, NULL, ?, ?)'
    )->execute([$id, $user['id'], $title, $now, $now]);

    $conv = require_conversation($pdo, $user['id'], $id);
    json_out(conversation_public($conv), 201);
});

// ---- List conversations (most recently active first) ----
route('GET', '/chat/conversations', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $stmt = $pdo->prepare(
        'SELECT * FROM conversations WHERE user_id = ?
         ORDER BY COALESCE(last_message_at, created_at) DESC, created_at DESC'
    );
    $stmt->execute([$user['id']]);
    $out = array_map('conversation_public', $stmt->fetchAll());
    json_out($out, 200);
});

// ---- Get one conversation with its messages ----
route('GET', '/chat/conversations/{id}', function ($params) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $conv = require_conversation($pdo, $user['id'], $params[0]);

    $stmt = $pdo->prepare(
        'SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC, id ASC'
    );
    $stmt->execute([$conv['id']]);
    $messages = array_map('message_public', $stmt->fetchAll());

    $out = conversation_public($conv);
    $out['messages'] = $messages;
    json_out($out, 200);
});

// ---- Rename a conversation ----
route('PATCH', '/chat/conversations/{id}', function ($params) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $conv = require_conversation($pdo, $user['id'], $params[0]);

    $b = body();
    $title = isset($b['title']) ? trim((string) $b['title']) : '';
    if ($title === '') error_out(422, 'validation_error', 'Title cannot be empty.');
    $title = mb_substr($title, 0, 200);

    $pdo->prepare('UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?')
        ->execute([$title, now_utc(), $conv['id']]);

    $conv = require_conversation($pdo, $user['id'], $conv['id']);
    json_out(conversation_public($conv), 200);
});

// ---- Delete a conversation (messages cascade) ----
route('DELETE', '/chat/conversations/{id}', function ($params) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $conv = require_conversation($pdo, $user['id'], $params[0]);

    $pdo->prepare('DELETE FROM conversations WHERE id = ?')->execute([$conv['id']]);
    json_out(['detail' => 'Conversation deleted.'], 200);
});

// ---- Send a message and stream the assistant reply (Server-Sent Events) ----
route('POST', '/chat/conversations/{id}/messages', function ($params) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $conv = require_conversation($pdo, $user['id'], $params[0]);

    $b = body();
    $content = isset($b['content']) ? trim((string) $b['content']) : '';
    if ($content === '') error_out(422, 'validation_error', 'Message content cannot be empty.');

    // Persist the user's message.
    $now = now_utc();
    $userMsgId = uuidv7();
    $pdo->prepare(
        'INSERT INTO messages (id, conversation_id, role, content, model, created_at)
         VALUES (?, ?, ?, ?, NULL, ?)'
    )->execute([$userMsgId, $conv['id'], 'user', $content, $now]);

    // First real message in a still-untitled chat → derive a title from it.
    if ($conv['title'] === 'New chat') {
        $derived = trim(preg_replace('/\s+/', ' ', mb_substr($content, 0, 80)));
        if ($derived !== '') {
            $pdo->prepare('UPDATE conversations SET title = ? WHERE id = ?')
                ->execute([mb_substr($derived, 0, 200), $conv['id']]);
        }
    }

    // Build the model conversation history (user/assistant turns only).
    $stmt = $pdo->prepare(
        "SELECT role, content FROM messages
         WHERE conversation_id = ? AND role IN ('user','assistant')
         ORDER BY created_at ASC, id ASC"
    );
    $stmt->execute([$conv['id']]);
    $history = [];
    foreach ($stmt->fetchAll() as $m) {
        $history[] = ['role' => $m['role'], 'content' => $m['content']];
    }

    // --- Switch the response into a Server-Sent Events stream ---
    header('Content-Type: text/event-stream; charset=utf-8');
    header('Cache-Control: no-cache');
    header('Connection: keep-alive');
    header('X-Accel-Buffering: no'); // ask nginx (if any) not to buffer
    while (ob_get_level() > 0) ob_end_flush();

    $send = function (array $frame) {
        echo 'data: ' . json_encode($frame, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . "\n\n";
        @ob_flush();
        @flush();
    };

    $send(['type' => 'start', 'conversation_id' => $conv['id'], 'message_id' => $userMsgId]);

    $model = $CONFIG['anthropic_model'] ?: 'claude-opus-4-8';
    $result = anthropic_stream(
        $CONFIG,
        CHAT_SYSTEM_PROMPT,
        $history,
        CHAT_MAX_TOKENS,
        function (string $text) use ($send) {
            if ($text !== '') $send(['type' => 'delta', 'text' => $text]);
        }
    );

    if (!$result['ok']) {
        $send(['type' => 'error', 'detail' => $result['error'] ?: 'The AI service is unavailable.']);
        exit;
    }

    // Persist the assistant reply and finish.
    $assistantId = uuidv7();
    $doneAt = now_utc();
    $pdo->prepare(
        'INSERT INTO messages (id, conversation_id, role, content, model, created_at)
         VALUES (?, ?, ?, ?, ?, ?)'
    )->execute([$assistantId, $conv['id'], 'assistant', $result['text'], $model, $doneAt]);

    $pdo->prepare('UPDATE conversations SET last_message_at = ?, updated_at = ? WHERE id = ?')
        ->execute([$doneAt, $doneAt, $conv['id']]);

    $send([
        'type'       => 'done',
        'message_id' => $assistantId,
        'content'    => $result['text'],
    ]);
    exit;
});
