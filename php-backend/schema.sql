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
