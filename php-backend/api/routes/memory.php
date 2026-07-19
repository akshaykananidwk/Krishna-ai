<?php
// Memory / notes endpoints with MySQL FULLTEXT search.
// JSON shapes match exactly what the Flutter Memory feature parses.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

/** Shape a memory row the way the Flutter app expects. */
function memory_public(array $m): array {
    $tags = [];
    if (!empty($m['tags'])) {
        $decoded = json_decode($m['tags'], true);
        if (is_array($decoded)) {
            $tags = array_values(array_filter(array_map('strval', $decoded), fn($t) => $t !== ''));
        }
    }
    return [
        'id'          => $m['id'],
        'title'       => $m['title'] !== null && $m['title'] !== '' ? $m['title'] : null,
        'content'     => $m['content'],
        'source_type' => $m['source_type'],
        'tags'        => $tags,
        'pinned'      => (bool) $m['pinned'],
        'importance'  => isset($m['importance']) ? (float) $m['importance'] : 0.5,
        'created_at'  => iso($m['created_at']),
        'updated_at'  => iso($m['updated_at']),
    ];
}

/** Fetch an active memory owned by this user, or send 404. */
function require_memory(PDO $pdo, string $userId, string $id): array {
    $stmt = $pdo->prepare("SELECT * FROM memories WHERE id = ? AND user_id = ? AND status = 'active'");
    $stmt->execute([$id, $userId]);
    $row = $stmt->fetch();
    if (!$row) error_out(404, 'not_found', 'Memory not found.');
    return $row;
}

// ---- List memories (pinned first, then newest) ----
route('GET', '/memory', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);

    $limit  = max(1, min(200, (int) ($_GET['limit'] ?? 50)));
    $offset = max(0, (int) ($_GET['offset'] ?? 0));

    $stmt = $pdo->prepare(
        "SELECT * FROM memories WHERE user_id = ? AND status = 'active'
         ORDER BY pinned DESC, created_at DESC, id DESC
         LIMIT $limit OFFSET $offset"
    );
    $stmt->execute([$user['id']]);
    json_out(array_map('memory_public', $stmt->fetchAll()), 200);
});

// ---- Create a memory / note ----
route('POST', '/memory', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);

    $b = body();
    $content = isset($b['content']) ? trim((string) $b['content']) : '';
    if ($content === '') error_out(422, 'validation_error', 'Content cannot be empty.');

    $title = isset($b['title']) ? trim((string) $b['title']) : '';
    $title = $title !== '' ? mb_substr($title, 0, 300) : null;

    $sourceType = isset($b['source_type']) ? trim((string) $b['source_type']) : 'note';
    if ($sourceType === '') $sourceType = 'note';
    $sourceType = mb_substr($sourceType, 0, 32);

    // Tags: accept an array of strings (ignore anything else).
    $tags = [];
    if (isset($b['tags']) && is_array($b['tags'])) {
        foreach ($b['tags'] as $t) {
            $t = trim((string) $t);
            if ($t !== '') $tags[] = mb_substr($t, 0, 64);
        }
    }

    $now = now_utc();
    $id  = uuidv7();
    $pdo->prepare(
        "INSERT INTO memories
           (id, user_id, source_type, source_ref, title, content, tags, importance, pinned, status, access_count, created_at, updated_at)
         VALUES (?, ?, ?, NULL, ?, ?, ?, 0.5, 0, 'active', 0, ?, ?)"
    )->execute([$id, $user['id'], $sourceType, $title, $content, json_encode($tags, JSON_UNESCAPED_UNICODE), $now, $now]);

    audit($pdo, 'memory_create', $user['id']);
    $row = require_memory($pdo, $user['id'], $id);
    json_out(memory_public($row), 201);
});

// ---- Search memories (FULLTEXT, with a LIKE fallback) ----
route('POST', '/memory/search', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);

    $b = body();
    $query = isset($b['query']) ? trim((string) $b['query']) : '';
    if ($query === '') error_out(422, 'validation_error', 'Search query cannot be empty.');
    $topK = (int) ($b['top_k'] ?? 8);
    $topK = max(1, min(50, $topK));

    $rows = [];
    // Primary: MySQL/MariaDB natural-language FULLTEXT search with a relevance score.
    try {
        $stmt = $pdo->prepare(
            "SELECT *, MATCH(title, content) AGAINST(? IN NATURAL LANGUAGE MODE) AS relevance
             FROM memories
             WHERE user_id = ? AND status = 'active'
               AND MATCH(title, content) AGAINST(? IN NATURAL LANGUAGE MODE)
             ORDER BY relevance DESC
             LIMIT $topK"
        );
        $stmt->execute([$query, $user['id'], $query]);
        $rows = $stmt->fetchAll();
    } catch (Throwable $e) {
        $rows = []; // FULLTEXT unavailable → fall through to LIKE below.
    }

    // Fallback: simple LIKE match when FULLTEXT finds nothing (e.g. short words
    // below the index token length) or is unavailable.
    if (!$rows) {
        $like = '%' . str_replace(['%', '_'], ['\\%', '\\_'], $query) . '%';
        $stmt = $pdo->prepare(
            "SELECT *, 0 AS relevance FROM memories
             WHERE user_id = ? AND status = 'active'
               AND (content LIKE ? OR title LIKE ?)
             ORDER BY pinned DESC, created_at DESC
             LIMIT $topK"
        );
        $stmt->execute([$user['id'], $like, $like]);
        $rows = $stmt->fetchAll();
    }

    $results = [];
    $hitIds  = [];
    foreach ($rows as $row) {
        $score = (float) ($row['relevance'] ?? 0);
        $results[] = [
            'memory'     => memory_public($row),
            'score'      => $score,
            // Map the raw FULLTEXT score into a 0..1 range for display.
            'similarity' => $score > 0 ? round($score / (1 + $score), 4) : 0.0,
        ];
        $hitIds[] = $row['id'];
    }

    // Best-effort: bump access_count on the memories we returned.
    if ($hitIds) {
        $in = implode(',', array_fill(0, count($hitIds), '?'));
        try {
            $pdo->prepare("UPDATE memories SET access_count = access_count + 1 WHERE id IN ($in)")
                ->execute($hitIds);
        } catch (Throwable $e) { /* non-critical */ }
    }

    json_out(['query' => $query, 'results' => $results], 200);
});

// ---- Delete a memory (soft delete) ----
route('DELETE', '/memory/{id}', function ($params) {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $mem = require_memory($pdo, $user['id'], $params[0]);

    $pdo->prepare("UPDATE memories SET status = 'deleted', updated_at = ? WHERE id = ?")
        ->execute([now_utc(), $mem['id']]);
    audit($pdo, 'memory_delete', $user['id']);
    json_out(['detail' => 'Memory deleted.'], 200);
});
