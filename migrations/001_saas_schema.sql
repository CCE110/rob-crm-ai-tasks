-- Jottask SaaS Database Migration
-- Run this in your Supabase SQL Editor

-- =============================================
-- 1. USERS TABLE (extends Supabase Auth)
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    company_name TEXT,
    phone TEXT,
    timezone TEXT DEFAULT 'Australia/Brisbane',
    avatar_url TEXT,

    -- Subscription
    subscription_status TEXT DEFAULT 'trial' CHECK (subscription_status IN ('trial', 'active', 'cancelled', 'expired')),
    subscription_tier TEXT DEFAULT 'starter' CHECK (subscription_tier IN ('starter', 'pro', 'business')),
    trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days'),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,

    -- Settings
    email_notifications BOOLEAN DEFAULT true,
    daily_summary_time TIME DEFAULT '08:00:00',
    reminder_minutes_before INTEGER DEFAULT 30,

    -- Onboarding
    onboarding_completed BOOLEAN DEFAULT false,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- =============================================
-- 2. ADD user_id TO EXISTING TASKS TABLE
-- =============================================
DO $$
BEGIN
    -- Add user_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE tasks ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
        CREATE INDEX idx_tasks_user_id ON tasks(user_id);
    END IF;
END $$;

-- =============================================
-- 3. EMAIL CONNECTIONS (for email processing)
-- =============================================
CREATE TABLE IF NOT EXISTS email_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Connection type
    provider TEXT NOT NULL CHECK (provider IN ('gmail', 'outlook', 'imap')),
    email_address TEXT NOT NULL,

    -- Credentials (encrypted in production)
    access_token TEXT,
    refresh_token TEXT,
    imap_password TEXT,  -- For app passwords

    -- Settings
    is_active BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMPTZ,
    sync_frequency_minutes INTEGER DEFAULT 15,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, email_address)
);

-- =============================================
-- 4. SUBSCRIPTION PLANS (for reference)
-- =============================================
CREATE TABLE IF NOT EXISTS subscription_plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_monthly DECIMAL(10,2),
    price_yearly DECIMAL(10,2),

    -- Limits
    max_tasks INTEGER,
    max_email_connections INTEGER,
    max_team_members INTEGER,

    -- Features
    ai_summaries BOOLEAN DEFAULT false,
    custom_statuses BOOLEAN DEFAULT false,
    api_access BOOLEAN DEFAULT false,
    priority_support BOOLEAN DEFAULT false,

    stripe_price_id_monthly TEXT,
    stripe_price_id_yearly TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default plans
INSERT INTO subscription_plans (id, name, price_monthly, price_yearly, max_tasks, max_email_connections, max_team_members, ai_summaries, custom_statuses, api_access, priority_support)
VALUES
    ('starter', 'Starter', 0, 0, 50, 1, 1, false, false, false, false),
    ('pro', 'Pro', 19, 190, 500, 3, 1, true, true, false, false),
    ('business', 'Business', 49, 490, -1, 10, 10, true, true, true, true)
ON CONFLICT (id) DO NOTHING;

-- =============================================
-- 5. ROW LEVEL SECURITY (RLS)
-- =============================================

-- Enable RLS on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_checklist_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_connections ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = id);

-- Tasks: users can only access their own tasks
CREATE POLICY "Users can view own tasks" ON tasks
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own tasks" ON tasks
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tasks" ON tasks
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tasks" ON tasks
    FOR DELETE USING (auth.uid() = user_id);

-- Task notes: follow task ownership
CREATE POLICY "Users can view own task notes" ON task_notes
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = task_notes.task_id AND tasks.user_id = auth.uid())
    );

CREATE POLICY "Users can create notes on own tasks" ON task_notes
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = task_notes.task_id AND tasks.user_id = auth.uid())
    );

-- Checklist items: follow task ownership
CREATE POLICY "Users can view own checklist items" ON task_checklist_items
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = task_checklist_items.task_id AND tasks.user_id = auth.uid())
    );

CREATE POLICY "Users can manage own checklist items" ON task_checklist_items
    FOR ALL USING (
        EXISTS (SELECT 1 FROM tasks WHERE tasks.id = task_checklist_items.task_id AND tasks.user_id = auth.uid())
    );

-- Email connections
CREATE POLICY "Users can view own email connections" ON email_connections
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own email connections" ON email_connections
    FOR ALL USING (auth.uid() = user_id);

-- =============================================
-- 6. HELPER FUNCTIONS
-- =============================================

-- Function to get user's task count
CREATE OR REPLACE FUNCTION get_user_task_count(p_user_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM tasks WHERE user_id = p_user_id AND status = 'pending');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user is within plan limits
CREATE OR REPLACE FUNCTION check_user_limits(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_tier TEXT;
    v_max_tasks INTEGER;
    v_current_tasks INTEGER;
BEGIN
    SELECT subscription_tier INTO v_tier FROM users WHERE id = p_user_id;
    SELECT max_tasks INTO v_max_tasks FROM subscription_plans WHERE id = v_tier;

    IF v_max_tasks = -1 THEN
        RETURN true;  -- Unlimited
    END IF;

    v_current_tasks := get_user_task_count(p_user_id);
    RETURN v_current_tasks < v_max_tasks;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================
-- 7. INDEXES FOR PERFORMANCE
-- =============================================
CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_user_due ON tasks(user_id, due_date, due_time);
CREATE INDEX IF NOT EXISTS idx_task_notes_task_id ON task_notes(task_id);
CREATE INDEX IF NOT EXISTS idx_checklist_task_id ON task_checklist_items(task_id);
CREATE INDEX IF NOT EXISTS idx_email_connections_user ON email_connections(user_id);

-- Done!
SELECT 'Jottask SaaS schema migration complete!' as status;
