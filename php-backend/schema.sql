-- ============================================================
-- Krishna AI — full MySQL / MariaDB schema (create the DB once)
-- Engine: InnoDB, utf8mb4. Tested on MariaDB 10.11.
-- The web installer runs these automatically; this file is a reference copy.
-- ============================================================

SET NAMES utf8mb4;
SET foreign_key_checks = 1;

-- ---- Users ----
CREATE TABLE IF NOT EXISTS users (
  id            CHAR(36)      NOT NULL PRIMARY KEY,
  email         VARCHAR(320)  NOT NULL,
  password_hash VARCHAR(255)  NULL,
  full_name     VARCHAR(255)  NULL,
  is_active     TINYINT(1)    NOT NULL DEFAULT 1,
  is_verified   TINYINT(1)    NOT NULL DEFAULT 0,
  is_admin      TINYINT(1)    NOT NULL DEFAULT 0,
  avatar_url    VARCHAR(512)  NULL,
  bio           VARCHAR(500)  NULL,
  timezone      VARCHAR(64)   NULL,
  created_at    DATETIME      NOT NULL,
  updated_at    DATETIME      NOT NULL,
  last_login_at DATETIME      NULL,
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Refresh tokens (only a SHA-256 hash is stored) ----
CREATE TABLE IF NOT EXISTS refresh_tokens (
  id         CHAR(36)  NOT NULL PRIMARY KEY,
  user_id    CHAR(36)  NOT NULL,
  token_hash CHAR(64)  NOT NULL,
  expires_at DATETIME  NOT NULL,
  revoked_at DATETIME  NULL,
  created_at DATETIME  NOT NULL,
  UNIQUE KEY uq_refresh_hash (token_hash),
  KEY ix_refresh_user (user_id),
  CONSTRAINT fk_refresh_user FOREIGN KEY (user_id)
    REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Conversations (AI Chat — used in Part 2) ----
CREATE TABLE IF NOT EXISTS conversations (
  id              CHAR(36)     NOT NULL PRIMARY KEY,
  user_id         CHAR(36)     NOT NULL,
  title           VARCHAR(200) NOT NULL DEFAULT 'New chat',
  last_message_at DATETIME     NULL,
  created_at      DATETIME     NOT NULL,
  updated_at      DATETIME     NOT NULL,
  KEY ix_conv_user (user_id),
  CONSTRAINT fk_conv_user FOREIGN KEY (user_id)
    REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Messages (AI Chat — used in Part 2) ----
CREATE TABLE IF NOT EXISTS messages (
  id              CHAR(36)    NOT NULL PRIMARY KEY,
  conversation_id CHAR(36)    NOT NULL,
  role            VARCHAR(16) NOT NULL,
  content         MEDIUMTEXT  NOT NULL,
  model           VARCHAR(64) NULL,
  created_at      DATETIME    NOT NULL,
  KEY ix_msg_conv (conversation_id),
  CONSTRAINT fk_msg_conv FOREIGN KEY (conversation_id)
    REFERENCES conversations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Memories / notes (FULLTEXT search — used in Part 3) ----
CREATE TABLE IF NOT EXISTS memories (
  id           CHAR(36)     NOT NULL PRIMARY KEY,
  user_id      CHAR(36)     NOT NULL,
  source_type  VARCHAR(32)  NOT NULL DEFAULT 'note',
  source_ref   VARCHAR(128) NULL,
  title        VARCHAR(300) NULL,
  content      MEDIUMTEXT   NOT NULL,
  tags         TEXT         NULL,             -- JSON array, e.g. ["work","apollo"]
  importance   FLOAT        NOT NULL DEFAULT 0.5,
  pinned       TINYINT(1)   NOT NULL DEFAULT 0,
  status       VARCHAR(16)  NOT NULL DEFAULT 'active',
  access_count INT          NOT NULL DEFAULT 0,
  created_at   DATETIME     NOT NULL,
  updated_at   DATETIME     NOT NULL,
  KEY ix_mem_user_status (user_id, status),
  FULLTEXT KEY ft_mem (title, content),
  CONSTRAINT fk_mem_user FOREIGN KEY (user_id)
    REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Cache (replaces Redis) ----
CREATE TABLE IF NOT EXISTS cache (
  cache_key   VARCHAR(191) NOT NULL PRIMARY KEY,
  cache_value MEDIUMTEXT   NULL,
  expires_at  DATETIME     NULL,
  KEY ix_cache_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Audit log ----
CREATE TABLE IF NOT EXISTS audit_log (
  id         CHAR(36)     NOT NULL PRIMARY KEY,
  user_id    CHAR(36)     NULL,
  action     VARCHAR(64)  NOT NULL,
  detail     VARCHAR(512) NULL,
  ip_address VARCHAR(45)  NULL,
  user_agent VARCHAR(512) NULL,
  created_at DATETIME     NOT NULL,
  KEY ix_audit_user (user_id),
  KEY ix_audit_action (action),
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id)
    REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Module expansion tables: Notes, Tasks, Reminders, Calendar,
-- Habits, Goals, Settings, Notifications, Meetings.
-- ============================================================

CREATE TABLE IF NOT EXISTS notes (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  title VARCHAR(300) NULL, body MEDIUMTEXT NOT NULL, color VARCHAR(16) NULL,
  pinned TINYINT(1) NOT NULL DEFAULT 0, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  KEY ix_notes_user (user_id), FULLTEXT KEY ft_notes (title, body),
  CONSTRAINT fk_notes_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tasks (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  title VARCHAR(300) NOT NULL, notes MEDIUMTEXT NULL, priority TINYINT NOT NULL DEFAULT 1,
  is_done TINYINT(1) NOT NULL DEFAULT 0, due_at DATETIME NULL, completed_at DATETIME NULL,
  created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  KEY ix_tasks_user (user_id, is_done), KEY ix_tasks_due (user_id, due_at),
  CONSTRAINT fk_tasks_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reminders (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  title VARCHAR(300) NOT NULL, remind_at DATETIME NOT NULL, is_done TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  KEY ix_reminders_user (user_id, remind_at),
  CONSTRAINT fk_reminders_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS events (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  title VARCHAR(300) NOT NULL, description MEDIUMTEXT NULL, location VARCHAR(300) NULL,
  start_at DATETIME NOT NULL, end_at DATETIME NULL, all_day TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  KEY ix_events_user (user_id, start_at),
  CONSTRAINT fk_events_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS habits (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  name VARCHAR(200) NOT NULL, schedule VARCHAR(16) NOT NULL DEFAULT 'daily', color VARCHAR(16) NULL,
  archived TINYINT(1) NOT NULL DEFAULT 0, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  KEY ix_habits_user (user_id, archived),
  CONSTRAINT fk_habits_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS habit_checkins (
  id CHAR(36) NOT NULL PRIMARY KEY, habit_id CHAR(36) NOT NULL, user_id CHAR(36) NOT NULL,
  check_date DATE NOT NULL, created_at DATETIME NOT NULL,
  UNIQUE KEY uq_habit_date (habit_id, check_date), KEY ix_checkins_user (user_id),
  CONSTRAINT fk_checkins_habit FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS goals (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  title VARCHAR(300) NOT NULL, description MEDIUMTEXT NULL, target_date DATE NULL,
  progress INT NOT NULL DEFAULT 0, status VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  KEY ix_goals_user (user_id, status),
  CONSTRAINT fk_goals_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_settings (
  user_id CHAR(36) NOT NULL PRIMARY KEY, data MEDIUMTEXT NULL, updated_at DATETIME NOT NULL,
  CONSTRAINT fk_settings_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS device_tokens (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  token VARCHAR(512) NOT NULL, platform VARCHAR(16) NOT NULL DEFAULT 'android', created_at DATETIME NOT NULL,
  UNIQUE KEY uq_device_token (token), KEY ix_device_user (user_id),
  CONSTRAINT fk_device_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notifications (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  title VARCHAR(300) NOT NULL, body MEDIUMTEXT NULL, type VARCHAR(32) NOT NULL DEFAULT 'general',
  is_read TINYINT(1) NOT NULL DEFAULT 0, created_at DATETIME NOT NULL,
  KEY ix_notif_user (user_id, is_read),
  CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS meetings (
  id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL,
  title VARCHAR(300) NOT NULL, transcript MEDIUMTEXT NOT NULL, summary MEDIUMTEXT NULL,
  action_items MEDIUMTEXT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  KEY ix_meetings_user (user_id),
  CONSTRAINT fk_meetings_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
