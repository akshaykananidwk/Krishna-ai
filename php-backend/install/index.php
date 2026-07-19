<?php
// ============================================================
// Krishna AI — web installer.
// Open https://YOURDOMAIN/install in a browser and follow the form.
// After a successful install it locks itself; delete this folder afterwards.
// ============================================================

$docRoot    = dirname(__DIR__);
$configPath = $docRoot . '/config.php';
$lockPath   = __DIR__ . '/.lock';
$errors     = [];
$success    = false;
$adminEmail = '';

// ---- All CREATE TABLE statements (kept in sync with schema.sql) ----
$SCHEMA = [
"CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) NOT NULL PRIMARY KEY,
  email VARCHAR(320) NOT NULL,
  password_hash VARCHAR(255) NULL,
  full_name VARCHAR(255) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  is_verified TINYINT(1) NOT NULL DEFAULT 0,
  is_admin TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  last_login_at DATETIME NULL,
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

"CREATE TABLE IF NOT EXISTS refresh_tokens (
  id CHAR(36) NOT NULL PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  token_hash CHAR(64) NOT NULL,
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uq_refresh_hash (token_hash),
  KEY ix_refresh_user (user_id),
  CONSTRAINT fk_refresh_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

"CREATE TABLE IF NOT EXISTS conversations (
  id CHAR(36) NOT NULL PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  title VARCHAR(200) NOT NULL DEFAULT 'New chat',
  last_message_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  KEY ix_conv_user (user_id),
  CONSTRAINT fk_conv_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

"CREATE TABLE IF NOT EXISTS messages (
  id CHAR(36) NOT NULL PRIMARY KEY,
  conversation_id CHAR(36) NOT NULL,
  role VARCHAR(16) NOT NULL,
  content MEDIUMTEXT NOT NULL,
  model VARCHAR(64) NULL,
  created_at DATETIME NOT NULL,
  KEY ix_msg_conv (conversation_id),
  CONSTRAINT fk_msg_conv FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

"CREATE TABLE IF NOT EXISTS memories (
  id CHAR(36) NOT NULL PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  source_type VARCHAR(32) NOT NULL DEFAULT 'note',
  source_ref VARCHAR(128) NULL,
  title VARCHAR(300) NULL,
  content MEDIUMTEXT NOT NULL,
  tags TEXT NULL,
  importance FLOAT NOT NULL DEFAULT 0.5,
  pinned TINYINT(1) NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  access_count INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  KEY ix_mem_user_status (user_id, status),
  FULLTEXT KEY ft_mem (title, content),
  CONSTRAINT fk_mem_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

"CREATE TABLE IF NOT EXISTS cache (
  cache_key VARCHAR(191) NOT NULL PRIMARY KEY,
  cache_value MEDIUMTEXT NULL,
  expires_at DATETIME NULL,
  KEY ix_cache_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

"CREATE TABLE IF NOT EXISTS audit_log (
  id CHAR(36) NOT NULL PRIMARY KEY,
  user_id CHAR(36) NULL,
  action VARCHAR(64) NOT NULL,
  detail VARCHAR(512) NULL,
  ip_address VARCHAR(45) NULL,
  user_agent VARCHAR(512) NULL,
  created_at DATETIME NOT NULL,
  KEY ix_audit_user (user_id),
  KEY ix_audit_action (action),
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
];

// ---- Pre-flight environment checks ----
$checks = [
    'PHP version >= 8.0'        => PHP_VERSION_ID >= 80000,
    'PDO MySQL extension'       => extension_loaded('pdo_mysql'),
    'cURL extension'            => extension_loaded('curl'),
    'mbstring extension'        => extension_loaded('mbstring'),
    'JSON support'              => function_exists('json_encode'),
    'Document root is writable' => is_writable($docRoot),
];
$allGreen = !in_array(false, $checks, true);
$locked   = file_exists($lockPath);

// ---- Handle submission ----
if ($_SERVER['REQUEST_METHOD'] === 'POST' && !$locked) {
    $dbHost   = trim($_POST['db_host'] ?? '');
    $dbName   = trim($_POST['db_name'] ?? '');
    $dbUser   = trim($_POST['db_user'] ?? '');
    $dbPass   = (string) ($_POST['db_pass'] ?? '');
    $apiKey   = trim($_POST['gemini_key'] ?? '');
    $model    = trim($_POST['gemini_model'] ?? '') ?: 'gemini-2.0-flash';
    $adminEmail = strtolower(trim($_POST['admin_email'] ?? ''));
    $adminPass  = (string) ($_POST['admin_pass'] ?? '');

    if ($dbHost === '' || $dbName === '' || $dbUser === '') $errors[] = 'Database host, name and user are required.';
    if (!filter_var($adminEmail, FILTER_VALIDATE_EMAIL)) $errors[] = 'Enter a valid admin email.';
    if (strlen($adminPass) < 8) $errors[] = 'Admin password must be at least 8 characters.';
    if (!$allGreen) $errors[] = 'Please fix the failing environment checks above first.';

    $pdo = null;
    if (!$errors) {
        try {
            $pdo = new PDO(
                "mysql:host=$dbHost;dbname=$dbName;charset=utf8mb4",
                $dbUser, $dbPass,
                [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
            );
        } catch (Throwable $e) {
            $errors[] = 'Database connection failed: ' . $e->getMessage();
        }
    }

    if (!$errors && $pdo) {
        try {
            foreach ($SCHEMA as $sql) { $pdo->exec($sql); }
        } catch (Throwable $e) {
            $errors[] = 'Creating tables failed: ' . $e->getMessage();
        }
    }

    // Write config.php
    if (!$errors && $pdo) {
        $config = [
            'db_host'           => $dbHost,
            'db_name'           => $dbName,
            'db_user'           => $dbUser,
            'db_pass'           => $dbPass,
            'db_charset'        => 'utf8mb4',
            'jwt_secret'        => bin2hex(random_bytes(32)),
            'access_ttl'        => 1800,
            'refresh_ttl'       => 2592000,
            'gemini_api_key'    => $apiKey,
            'gemini_model'      => $model,
            'app_url'           => 'https://' . ($_SERVER['HTTP_HOST'] ?? 'krishnaai.akdwk.in'),
        ];
        $php = "<?php\n// Generated by the Krishna AI installer. Do not commit this file.\nreturn "
             . var_export($config, true) . ";\n";
        if (@file_put_contents($configPath, $php) === false) {
            $errors[] = 'Could not write config.php. Create it manually at ' . $configPath
                . ' with the contents shown below.';
            $manualConfig = $php;
        }
    }

    // Create the admin user
    if (!$errors && $pdo) {
        try {
            $exists = $pdo->prepare('SELECT id FROM users WHERE email = ?');
            $exists->execute([$adminEmail]);
            if ($exists->fetch()) {
                $errors[] = 'A user with that admin email already exists.';
            } else {
                $now = gmdate('Y-m-d H:i:s');
                $b = random_bytes(16);
                $b[6] = chr((ord($b[6]) & 0x0f) | 0x40);
                $b[8] = chr((ord($b[8]) & 0x3f) | 0x80);
                $uuid = vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($b), 4));
                $pdo->prepare(
                    'INSERT INTO users (id, email, password_hash, full_name, is_active, is_verified, is_admin, created_at, updated_at)
                     VALUES (?, ?, ?, ?, 1, 1, 1, ?, ?)'
                )->execute([$uuid, $adminEmail, password_hash($adminPass, PASSWORD_BCRYPT), 'Admin', $now, $now]);
            }
        } catch (Throwable $e) {
            $errors[] = 'Creating the admin user failed: ' . $e->getMessage();
        }
    }

    if (!$errors) {
        @file_put_contents($lockPath, gmdate('c'));
        $success = true;
        $locked  = true;
    }
}

function tick(bool $ok): string {
    return $ok
        ? '<span style="color:#128a3a;font-weight:700">&#10004; OK</span>'
        : '<span style="color:#c0261b;font-weight:700">&#10008; MISSING</span>';
}
$host = $_SERVER['HTTP_HOST'] ?? 'krishnaai.akdwk.in';
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Krishna AI — Installer</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 640px; margin: 32px auto; padding: 0 16px; line-height: 1.5; }
  h1 { font-size: 1.5rem; }
  .card { border: 1px solid #8883; border-radius: 12px; padding: 20px; margin: 18px 0; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 6px 4px; border-bottom: 1px solid #8882; }
  label { display: block; font-weight: 600; margin: 12px 0 4px; }
  input { width: 100%; padding: 10px 12px; border: 1px solid #8886; border-radius: 8px;
          font-size: 1rem; box-sizing: border-box; background: transparent; color: inherit; }
  button { margin-top: 20px; width: 100%; padding: 12px; border: 0; border-radius: 8px;
           background: #3e5cff; color: #fff; font-size: 1rem; font-weight: 600; cursor: pointer; }
  button[disabled] { background: #8888; cursor: not-allowed; }
  .err { background: #c0261b22; border: 1px solid #c0261b; padding: 12px; border-radius: 8px; }
  .ok  { background: #128a3a22; border: 1px solid #128a3a; padding: 12px; border-radius: 8px; }
  code, pre { background: #8881; padding: 2px 6px; border-radius: 6px; }
  pre { padding: 12px; overflow: auto; }
  small { color: #8886; }
</style>
</head>
<body>
<h1>🕉️ Krishna AI — Installer</h1>

<?php if ($success): ?>
  <div class="card ok">
    <h2>✅ Installation complete</h2>
    <p>The database tables were created, <code>config.php</code> was written, and your admin
       account <strong><?= htmlspecialchars($adminEmail) ?></strong> is ready.</p>
    <p><strong>Do these two things now:</strong></p>
    <ol>
      <li>Delete the <code>install</code> folder from your site (in aaPanel File Manager) so it can never run again.</li>
      <li>Test the API: open <code>https://<?= htmlspecialchars($host) ?>/api/auth/me</code> —
          it should return a JSON <code>invalid_token</code> error (that means routing works).</li>
    </ol>
    <p>Then point the Flutter app at <code>https://<?= htmlspecialchars($host) ?>/api</code>
       (see the instructions you were given).</p>
  </div>
<?php elseif ($locked): ?>
  <div class="card ok">
    <h2>🔒 Already installed</h2>
    <p>The installer is locked (a <code>install/.lock</code> file exists). Delete the whole
       <code>install</code> folder. To reinstall from scratch, delete <code>config.php</code>
       and <code>install/.lock</code>, then reload this page.</p>
  </div>
<?php else: ?>

  <div class="card">
    <h2>1. Environment checks</h2>
    <table>
      <?php foreach ($checks as $name => $ok): ?>
        <tr><td><?= htmlspecialchars($name) ?></td><td style="text-align:right"><?= tick($ok) ?></td></tr>
      <?php endforeach; ?>
    </table>
    <?php if (!$allGreen): ?>
      <p class="err" style="margin-top:14px">Fix the red items in aaPanel (PHP settings → Extensions,
         or folder permissions) before continuing.</p>
    <?php endif; ?>
  </div>

  <?php if ($errors): ?>
    <div class="card err">
      <strong>Could not install:</strong>
      <ul><?php foreach ($errors as $e): ?><li><?= htmlspecialchars($e) ?></li><?php endforeach; ?></ul>
      <?php if (!empty($manualConfig)): ?>
        <p>Create <code>config.php</code> in your document root with exactly this:</p>
        <pre><?= htmlspecialchars($manualConfig) ?></pre>
      <?php endif; ?>
    </div>
  <?php endif; ?>

  <form method="post" class="card" autocomplete="off">
    <h2>2. Configuration</h2>
    <p><small>Create the database and a database user in aaPanel first, then enter them here.</small></p>

    <label>Database host</label>
    <input name="db_host" value="<?= htmlspecialchars($_POST['db_host'] ?? 'localhost') ?>" required>

    <label>Database name</label>
    <input name="db_name" value="<?= htmlspecialchars($_POST['db_name'] ?? '') ?>" required>

    <label>Database user</label>
    <input name="db_user" value="<?= htmlspecialchars($_POST['db_user'] ?? '') ?>" required>

    <label>Database password</label>
    <input name="db_pass" type="password" value="">

    <label>Google Gemini API key <small>(used for chat — get one at aistudio.google.com/apikey)</small></label>
    <input name="gemini_key" value="<?= htmlspecialchars($_POST['gemini_key'] ?? '') ?>">

    <label>Gemini model</label>
    <input name="gemini_model" value="<?= htmlspecialchars($_POST['gemini_model'] ?? 'gemini-2.0-flash') ?>">

    <hr style="margin:20px 0;border:none;border-top:1px solid #8883">

    <label>Admin email</label>
    <input name="admin_email" type="email" value="<?= htmlspecialchars($_POST['admin_email'] ?? '') ?>" required>

    <label>Admin password <small>(min 8 characters)</small></label>
    <input name="admin_pass" type="password" required>

    <button type="submit" <?= $allGreen ? '' : 'disabled' ?>>Install Krishna AI</button>
  </form>
<?php endif; ?>

</body>
</html>
