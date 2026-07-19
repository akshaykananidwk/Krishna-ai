<?php
// Calls the Anthropic (Claude) Messages API over cURL, with true SSE streaming.
if (!defined('KRISHNA')) { http_response_code(403); exit('Forbidden'); }

/**
 * Stream an assistant reply from Claude.
 *
 * @param array    $config    app config (needs anthropic_api_key, anthropic_model)
 * @param string   $system    system prompt
 * @param array    $messages  [['role'=>'user'|'assistant','content'=>'...'], ...]
 * @param int      $maxTokens max output tokens
 * @param callable $onDelta   called with each text chunk as it streams in
 * @return array   ['ok'=>bool, 'text'=>string, 'error'=>?string]
 */
function anthropic_stream(array $config, string $system, array $messages, int $maxTokens, callable $onDelta): array {
    $buffer = '';
    $full   = '';
    $error  = null;

    $payload = [
        'model'      => $config['anthropic_model'] ?: 'claude-opus-4-8',
        'max_tokens' => $maxTokens,
        'system'     => $system,
        'messages'   => $messages,
        'stream'     => true,
    ];

    $ch = curl_init('https://api.anthropic.com/v1/messages');
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => [
            'content-type: application/json',
            'x-api-key: ' . $config['anthropic_api_key'],
            'anthropic-version: 2023-06-01',
        ],
        CURLOPT_POSTFIELDS     => json_encode($payload, JSON_UNESCAPED_UNICODE),
        CURLOPT_RETURNTRANSFER => false,
        CURLOPT_TIMEOUT        => 180,
        CURLOPT_WRITEFUNCTION  => function ($ch, $chunk) use (&$buffer, &$full, &$error, $onDelta) {
            // Anthropic streams Server-Sent Events; a chunk may split a line, so
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
                $type = $data['type'] ?? '';
                if ($type === 'content_block_delta' && ($data['delta']['type'] ?? '') === 'text_delta') {
                    $text = $data['delta']['text'] ?? '';
                    $full .= $text;
                    $onDelta($text);
                } elseif ($type === 'error') {
                    $error = $data['error']['message'] ?? 'LLM provider error.';
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

    // On an HTTP error, Anthropic returns a JSON error body (not SSE); it stays
    // unparsed in the buffer — pull the message out of it.
    if ($error === null && $code >= 400) {
        $j = json_decode(trim($buffer), true);
        $error = $j['error']['message'] ?? ('AI service returned HTTP ' . $code);
    }

    return ['ok' => $error === null, 'text' => $full, 'error' => $error];
}
