<?php
// Calls the Google Gemini API over cURL, with true SSE streaming.
// Exposes gemini_stream(), a drop-in replacement for the old anthropic_stream():
// same arguments, same return shape, so api/routes/chat.php is unchanged.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

/**
 * Stream an assistant reply from Google Gemini.
 *
 * @param array    $config    app config (needs gemini_api_key, gemini_model)
 * @param string   $system    system prompt
 * @param array    $messages  [['role'=>'user'|'assistant','content'=>'...'], ...]
 * @param int      $maxTokens max output tokens
 * @param callable $onDelta   called with each text chunk as it streams in
 * @return array   ['ok'=>bool, 'text'=>string, 'error'=>?string]
 */
function gemini_stream(array $config, string $system, array $messages, int $maxTokens, callable $onDelta): array {
    $apiKey = trim((string) ($config['gemini_api_key'] ?? ''));
    if ($apiKey === '') {
        return ['ok' => false, 'text' => '', 'error' => 'No Gemini API key configured. Add gemini_api_key to config.php.'];
    }
    $model = $config['gemini_model'] ?? '';
    if ($model === '') $model = 'gemini-2.0-flash';

    // Convert our history into Gemini's "contents" format (roles: user | model).
    $contents = [];
    foreach ($messages as $m) {
        $role = ($m['role'] ?? 'user') === 'assistant' ? 'model' : 'user';
        $contents[] = ['role' => $role, 'parts' => [['text' => (string) ($m['content'] ?? '')]]];
    }

    $payload = [
        'contents'          => $contents,
        'generationConfig'  => ['maxOutputTokens' => $maxTokens],
    ];
    if ($system !== '') {
        $payload['systemInstruction'] = ['parts' => [['text' => $system]]];
    }

    $buffer  = '';
    $full    = '';
    $error   = null;
    $blocked = null;

    $url = 'https://generativelanguage.googleapis.com/v1beta/models/'
         . rawurlencode($model) . ':streamGenerateContent?alt=sse&key=' . rawurlencode($apiKey);

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => ['content-type: application/json'],
        CURLOPT_POSTFIELDS     => json_encode($payload, JSON_UNESCAPED_UNICODE),
        CURLOPT_RETURNTRANSFER => false,
        CURLOPT_TIMEOUT        => 180,
        CURLOPT_WRITEFUNCTION  => function ($ch, $chunk) use (&$buffer, &$full, &$error, &$blocked, $onDelta) {
            // Gemini streams Server-Sent Events; a chunk may split a line, so
            // buffer and process only complete lines.
            $buffer .= $chunk;
            while (($nl = strpos($buffer, "\n")) !== false) {
                $line   = trim(substr($buffer, 0, $nl));
                $buffer = substr($buffer, $nl + 1);
                if ($line === '' || strncmp($line, 'data:', 5) !== 0) continue;
                $json = trim(substr($line, 5));
                if ($json === '' || $json === '[DONE]') continue;
                $data = json_decode($json, true);
                if (!is_array($data)) continue;

                // A blocked prompt comes back as promptFeedback.blockReason.
                if (!empty($data['promptFeedback']['blockReason'])) {
                    $blocked = $data['promptFeedback']['blockReason'];
                }
                if (isset($data['candidates'][0])) {
                    $cand = $data['candidates'][0];
                    foreach ($cand['content']['parts'] ?? [] as $part) {
                        if (isset($part['text']) && $part['text'] !== '') {
                            $full .= $part['text'];
                            $onDelta($part['text']);
                        }
                    }
                    // A blocked / recited answer stops with a non-STOP reason.
                    $finish = $cand['finishReason'] ?? '';
                    if ($finish !== '' && !in_array($finish, ['STOP', 'MAX_TOKENS', ''], true)) {
                        $blocked = $finish;
                    }
                }
            }
            return strlen($chunk);
        },
    ]);

    $result = curl_exec($ch);
    $code   = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    if ($result === false && $error === null) {
        $error = 'Could not reach the AI service: ' . curl_error($ch);
    }
    curl_close($ch);

    // On an HTTP error, Gemini returns a JSON error body (not SSE); it stays
    // unparsed in the buffer — pull the message out of it.
    if ($error === null && $code >= 400) {
        $j = json_decode(trim($buffer), true);
        $msg = $j['error']['message'] ?? '';
        if ($code === 429) {
            $error = 'The AI service quota was exceeded. Please try again later.'
                   . ($msg ? ' (' . $msg . ')' : '');
        } else {
            $error = $msg !== '' ? $msg : ('AI service returned HTTP ' . $code);
        }
    }

    // If nothing was produced because the content was blocked, surface that.
    if ($error === null && $full === '' && $blocked !== null) {
        $error = 'The response was blocked by the AI safety filter (' . $blocked . ').';
    }

    return ['ok' => $error === null, 'text' => $full, 'error' => $error];
}
