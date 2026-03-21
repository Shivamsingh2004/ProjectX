CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'USER',
  preferences JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS connected_accounts (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  platform_name VARCHAR(100) NOT NULL,
  account_identifier VARCHAR(255) NOT NULL,
  access_token_encrypted TEXT,
  refresh_token_encrypted TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, platform_name, account_identifier)
);

CREATE TABLE IF NOT EXISTS matches (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  platform_name VARCHAR(100) NOT NULL,
  matched_user_name VARCHAR(255) NOT NULL,
  score NUMERIC(5,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id VARCHAR(255) NOT NULL,
  platform_name VARCHAR(100) NOT NULL,
  sender VARCHAR(255) NOT NULL,
  content TEXT NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type VARCHAR(100) NOT NULL,
  message TEXT NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  response_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
  engagement_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  platform_metrics JSONB,
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_suggestions (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  suggestion_type VARCHAR(100) NOT NULL,
  input_context JSONB,
  suggestion_text TEXT NOT NULL,
  score NUMERIC(5,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_connected_accounts_user ON connected_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_conversation ON messages(user_id, conversation_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_matches_user ON matches(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics(user_id, calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_suggestions_user ON ai_suggestions(user_id, created_at DESC);

-- Enterprise Optimizations & Advanced Indexing
CREATE INDEX IF NOT EXISTS idx_users_preferences_gin ON users USING GIN (preferences);
CREATE INDEX IF NOT EXISTS idx_analytics_platform_gin ON analytics USING GIN (platform_metrics);
CREATE INDEX IF NOT EXISTS idx_messages_platform_hash ON messages USING HASH (platform_name);
CREATE INDEX IF NOT EXISTS idx_ai_suggestions_context_gin ON ai_suggestions USING GIN (input_context);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type) WHERE is_read = false;
