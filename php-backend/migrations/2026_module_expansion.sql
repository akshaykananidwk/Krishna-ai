-- ============================================================
-- Krishna AI — module expansion migration.
-- Adds the tables for: User Profile, Notes, Tasks, Reminders,
-- Calendar, Habits, Goals, Settings, Notifications, Meetings.
-- Safe to run on an existing install (all statements are additive
-- and idempotent). Paste into phpMyAdmin → SQL, on the Krishna DB.
-- ============================================================

SET NAMES utf8mb4;

-- ---- User Profile: extend the users table ----
-- (Run these once; if a column already exists MySQL will error on that
--  single line only — you can ignore "Duplicate column name" errors.)
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512) NULL;
ALTER TABLE users ADD COLUMN bio        VARCHAR(500) NULL;
ALTER TABLE users ADD COLUMN timezone   VARCHAR(64)  NULL;

-- ---- Notes ----
CREATE TABLE IF NOT EXISTS notes (
  id         CHAR(36)     NOT NULL PRIMARY KEY,
  user_id    CHAR(36)     NOT NULL,
  title      VARCHAR(300) NULL,
  body       MEDIUMTEXT   NOT NULL,
  color      VARCHAR(16)  NULL,
  pinned     TINYINT(1)   NOT NULL DEFAULT 0,
  created_at DATETIME     NOT NULL,
  updated_at DATETIME     NOT NULL,
  KEY ix_notes_user (user_id),
  FULLTEXT KEY ft_notes (title, body),
  CONSTRAINT fk_notes_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Tasks ----
CREATE TABLE IF NOT EXISTS tasks (
  id           CHAR(36)     NOT NULL PRIMARY KEY,
  user_id      CHAR(36)     NOT NULL,
  title        VARCHAR(300) NOT NULL,
  notes        MEDIUMTEXT   NULL,
  priority     TINYINT      NOT NULL DEFAULT 1,   -- 0 low, 1 normal, 2 high
  is_done      TINYINT(1)   NOT NULL DEFAULT 0,
  due_at       DATETIME     NULL,
  completed_at DATETIME     NULL,
  created_at   DATETIME     NOT NULL,
  updated_at   DATETIME     NOT NULL,
  KEY ix_tasks_user (user_id, is_done),
  KEY ix_tasks_due (user_id, due_at),
  CONSTRAINT fk_tasks_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Reminders ----
CREATE TABLE IF NOT EXISTS reminders (
  id         CHAR(36)     NOT NULL PRIMARY KEY,
  user_id    CHAR(36)     NOT NULL,
  title      VARCHAR(300) NOT NULL,
  remind_at  DATETIME     NOT NULL,
  is_done    TINYINT(1)   NOT NULL DEFAULT 0,
  created_at DATETIME     NOT NULL,
  updated_at DATETIME     NOT NULL,
  KEY ix_reminders_user (user_id, remind_at),
  CONSTRAINT fk_reminders_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Calendar events ----
CREATE TABLE IF NOT EXISTS events (
  id          CHAR(36)     NOT NULL PRIMARY KEY,
  user_id     CHAR(36)     NOT NULL,
  title       VARCHAR(300) NOT NULL,
  description MEDIUMTEXT   NULL,
  location    VARCHAR(300) NULL,
  start_at    DATETIME     NOT NULL,
  end_at      DATETIME     NULL,
  all_day     TINYINT(1)   NOT NULL DEFAULT 0,
  created_at  DATETIME     NOT NULL,
  updated_at  DATETIME     NOT NULL,
  KEY ix_events_user (user_id, start_at),
  CONSTRAINT fk_events_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Habits + check-ins ----
CREATE TABLE IF NOT EXISTS habits (
  id         CHAR(36)     NOT NULL PRIMARY KEY,
  user_id    CHAR(36)     NOT NULL,
  name       VARCHAR(200) NOT NULL,
  schedule   VARCHAR(16)  NOT NULL DEFAULT 'daily',
  color      VARCHAR(16)  NULL,
  archived   TINYINT(1)   NOT NULL DEFAULT 0,
  created_at DATETIME     NOT NULL,
  updated_at DATETIME     NOT NULL,
  KEY ix_habits_user (user_id, archived),
  CONSTRAINT fk_habits_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS habit_checkins (
  id         CHAR(36) NOT NULL PRIMARY KEY,
  habit_id   CHAR(36) NOT NULL,
  user_id    CHAR(36) NOT NULL,
  check_date DATE     NOT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uq_habit_date (habit_id, check_date),
  KEY ix_checkins_user (user_id),
  CONSTRAINT fk_checkins_habit FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Goals ----
CREATE TABLE IF NOT EXISTS goals (
  id          CHAR(36)     NOT NULL PRIMARY KEY,
  user_id     CHAR(36)     NOT NULL,
  title       VARCHAR(300) NOT NULL,
  description MEDIUMTEXT   NULL,
  target_date DATE         NULL,
  progress    INT          NOT NULL DEFAULT 0,     -- 0..100
  status      VARCHAR(16)  NOT NULL DEFAULT 'active',
  created_at  DATETIME     NOT NULL,
  updated_at  DATETIME     NOT NULL,
  KEY ix_goals_user (user_id, status),
  CONSTRAINT fk_goals_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Per-user settings (single JSON blob) ----
CREATE TABLE IF NOT EXISTS user_settings (
  user_id    CHAR(36)   NOT NULL PRIMARY KEY,
  data       MEDIUMTEXT NULL,      -- JSON object
  updated_at DATETIME   NOT NULL,
  CONSTRAINT fk_settings_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Device push tokens ----
CREATE TABLE IF NOT EXISTS device_tokens (
  id         CHAR(36)     NOT NULL PRIMARY KEY,
  user_id    CHAR(36)     NOT NULL,
  token      VARCHAR(512) NOT NULL,
  platform   VARCHAR(16)  NOT NULL DEFAULT 'android',
  created_at DATETIME     NOT NULL,
  UNIQUE KEY uq_device_token (token),
  KEY ix_device_user (user_id),
  CONSTRAINT fk_device_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- In-app notifications ----
CREATE TABLE IF NOT EXISTS notifications (
  id         CHAR(36)     NOT NULL PRIMARY KEY,
  user_id    CHAR(36)     NOT NULL,
  title      VARCHAR(300) NOT NULL,
  body       MEDIUMTEXT   NULL,
  type       VARCHAR(32)  NOT NULL DEFAULT 'general',
  is_read    TINYINT(1)   NOT NULL DEFAULT 0,
  created_at DATETIME     NOT NULL,
  KEY ix_notif_user (user_id, is_read),
  CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---- Meetings (transcript + AI summary) ----
CREATE TABLE IF NOT EXISTS meetings (
  id           CHAR(36)     NOT NULL PRIMARY KEY,
  user_id      CHAR(36)     NOT NULL,
  title        VARCHAR(300) NOT NULL,
  transcript   MEDIUMTEXT   NOT NULL,
  summary      MEDIUMTEXT   NULL,
  action_items MEDIUMTEXT   NULL,     -- JSON array
  created_at   DATETIME     NOT NULL,
  updated_at   DATETIME     NOT NULL,
  KEY ix_meetings_user (user_id),
  CONSTRAINT fk_meetings_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
