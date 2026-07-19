<?php
// Daily Planner (Module 21) + Weekly Planner (Module 22).
// These aggregate tasks, reminders and events into a day/week view.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

/** Collect tasks/reminders/events that fall on [startDt, endDt). */
function planner_slice(PDO $pdo, string $userId, string $startDt, string $endDt): array {
    $tasks = $pdo->prepare(
        'SELECT * FROM tasks WHERE user_id = ? AND due_at >= ? AND due_at < ? ORDER BY due_at ASC'
    );
    $tasks->execute([$userId, $startDt, $endDt]);

    $reminders = $pdo->prepare(
        'SELECT * FROM reminders WHERE user_id = ? AND remind_at >= ? AND remind_at < ? ORDER BY remind_at ASC'
    );
    $reminders->execute([$userId, $startDt, $endDt]);

    $events = $pdo->prepare(
        'SELECT * FROM events WHERE user_id = ? AND start_at < ? AND (end_at IS NULL AND start_at >= ? OR end_at >= ?) ORDER BY start_at ASC'
    );
    $events->execute([$userId, $endDt, $startDt, $startDt]);

    return [
        'tasks'     => array_map('task_public', $tasks->fetchAll()),
        'reminders' => array_map('reminder_public', $reminders->fetchAll()),
        'events'    => array_map('event_public', $events->fetchAll()),
    ];
}

// GET /planner/daily?date=YYYY-MM-DD  (defaults to today, UTC)
route('GET', '/planner/daily', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $date = parse_date($_GET['date'] ?? null) ?? gmdate('Y-m-d');
    $start = $date . ' 00:00:00';
    $end   = gmdate('Y-m-d H:i:s', strtotime($date . ' +1 day'));
    json_out(array_merge(['date' => $date], planner_slice($pdo, $user['id'], $start, $end)), 200);
});

// GET /planner/weekly?start=YYYY-MM-DD  (defaults to the current week, Monday start)
route('GET', '/planner/weekly', function () {
    global $pdo, $CONFIG;
    $user = require_user($pdo, $CONFIG);
    $start = parse_date($_GET['start'] ?? null);
    if ($start === null) {
        // Monday of the current week (UTC).
        $dow = (int) gmdate('N');   // 1 = Mon
        $start = gmdate('Y-m-d', strtotime('-' . ($dow - 1) . ' days'));
    }
    $days = [];
    for ($i = 0; $i < 7; $i++) {
        $d  = gmdate('Y-m-d', strtotime($start . " +$i day"));
        $s  = $d . ' 00:00:00';
        $e  = gmdate('Y-m-d H:i:s', strtotime($d . ' +1 day'));
        $days[] = array_merge(['date' => $d], planner_slice($pdo, $user['id'], $s, $e));
    }
    json_out(['start' => $start, 'days' => $days], 200);
});
