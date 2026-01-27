-- Email action tokens for passwordless task actions
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS email_action_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    action TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast token lookups
CREATE INDEX IF NOT EXISTS idx_email_tokens_token ON email_action_tokens(token);
CREATE INDEX IF NOT EXISTS idx_email_tokens_expires ON email_action_tokens(expires_at);
