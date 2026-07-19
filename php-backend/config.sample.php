<?php
// Reference only. The web installer (/install) generates the real config.php
// in the document root with your values. You normally never edit this by hand.
return [
    'db_host'           => 'localhost',
    'db_name'           => 'krishnaai',
    'db_user'           => 'krishnaai',
    'db_pass'           => 'your-db-password',
    'db_charset'        => 'utf8mb4',

    // Generated automatically by the installer: bin2hex(random_bytes(32))
    'jwt_secret'        => 'change-me-64-hex-characters',
    'access_ttl'        => 1800,      // access token lifetime, seconds (30 min)
    'refresh_ttl'       => 2592000,   // refresh token lifetime, seconds (30 days)

    // Used by the Chat module. Google Gemini (generativelanguage.googleapis.com).
    'gemini_api_key'    => '',
    'gemini_model'      => 'gemini-2.0-flash',

    'app_url'           => 'https://krishnaai.akdwk.in',
];
