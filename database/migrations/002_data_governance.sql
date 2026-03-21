-- ============================================================================
-- Data Governance: PII Classification, Retention Policies, Right-to-Delete
--
-- This migration adds PII metadata, retention enforcement via pg_cron,
-- and a GDPR right-to-delete cascade workflow.
-- ============================================================================

-- ── PII Classification Metadata ────────────────────────────────────────────
-- Tag columns with sensitivity levels for automated compliance scanning
COMMENT ON COLUMN users.email IS 'PII:HIGH - User email address';
COMMENT ON COLUMN users.full_name IS 'PII:HIGH - User full name';
COMMENT ON COLUMN users.password_hash IS 'PII:CRITICAL - Hashed password';
COMMENT ON COLUMN users.preferences IS 'PII:MEDIUM - User preferences (may contain personal data)';
COMMENT ON COLUMN connected_accounts.access_token_encrypted IS 'PII:CRITICAL - Encrypted OAuth token';
COMMENT ON COLUMN connected_accounts.refresh_token_encrypted IS 'PII:CRITICAL - Encrypted refresh token';
COMMENT ON COLUMN connected_accounts.account_identifier IS 'PII:HIGH - Platform username/ID';
COMMENT ON COLUMN messages.content IS 'PII:HIGH - Message content (may contain personal data)';
COMMENT ON COLUMN messages.sender IS 'PII:MEDIUM - Sender identifier';
COMMENT ON COLUMN notifications.message IS 'PII:LOW - Notification text';

-- ── Data Retention Table ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS data_retention_policies (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL UNIQUE,
    retention_days INTEGER NOT NULL,
    pii_level VARCHAR(20) NOT NULL DEFAULT 'NONE',
    deletion_strategy VARCHAR(50) NOT NULL DEFAULT 'HARD_DELETE',
    last_cleanup_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO data_retention_policies (table_name, retention_days, pii_level, deletion_strategy) VALUES
    ('messages', 365, 'HIGH', 'HARD_DELETE'),
    ('notifications', 90, 'LOW', 'HARD_DELETE'),
    ('analytics', 730, 'MEDIUM', 'ANONYMIZE'),
    ('ai_suggestions', 180, 'MEDIUM', 'HARD_DELETE'),
    ('matches', 365, 'MEDIUM', 'ANONYMIZE')
ON CONFLICT (table_name) DO NOTHING;

-- ── Automated Retention Cleanup Functions ──────────────────────────────────
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS void AS $$
DECLARE
    policy RECORD;
    cutoff TIMESTAMPTZ;
    deleted_count BIGINT;
BEGIN
    FOR policy IN SELECT * FROM data_retention_policies LOOP
        cutoff := NOW() - (policy.retention_days || ' days')::INTERVAL;

        IF policy.deletion_strategy = 'HARD_DELETE' THEN
            EXECUTE format(
                'DELETE FROM %I WHERE created_at < $1',
                policy.table_name
            ) USING cutoff;
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
        ELSIF policy.deletion_strategy = 'ANONYMIZE' THEN
            -- Anonymize PII fields but retain aggregate data
            IF policy.table_name = 'analytics' THEN
                UPDATE analytics SET
                    user_id = '00000000-0000-0000-0000-000000000000'::UUID
                WHERE calculated_at < cutoff
                  AND user_id != '00000000-0000-0000-0000-000000000000'::UUID;
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
            ELSIF policy.table_name = 'matches' THEN
                UPDATE matches SET
                    matched_user_name = 'ANONYMIZED'
                WHERE created_at < cutoff
                  AND matched_user_name != 'ANONYMIZED';
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
            END IF;
        END IF;

        -- Update last cleanup timestamp
        UPDATE data_retention_policies
        SET last_cleanup_at = NOW()
        WHERE table_name = policy.table_name;

        RAISE NOTICE 'Retention cleanup: % rows processed for %',
            deleted_count, policy.table_name;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Schedule nightly cleanup (requires pg_cron extension)
-- SELECT cron.schedule('retention-cleanup', '0 3 * * *', 'SELECT cleanup_expired_data()');

-- ── GDPR Right-to-Delete (Article 17) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS deletion_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    tables_processed TEXT[],
    error_details TEXT
);

CREATE INDEX IF NOT EXISTS idx_deletion_requests_status
    ON deletion_requests(status) WHERE status = 'PENDING';

CREATE OR REPLACE FUNCTION process_deletion_request(p_request_id UUID)
RETURNS void AS $$
DECLARE
    v_user_id UUID;
    v_tables_done TEXT[] := '{}';
BEGIN
    SELECT user_id INTO v_user_id
    FROM deletion_requests
    WHERE id = p_request_id AND status = 'PENDING';

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Invalid or already processed deletion request: %', p_request_id;
    END IF;

    -- Update status to IN_PROGRESS
    UPDATE deletion_requests SET status = 'IN_PROGRESS' WHERE id = p_request_id;

    -- Delete in dependency order (children first)
    DELETE FROM ai_suggestions WHERE user_id = v_user_id;
    v_tables_done := array_append(v_tables_done, 'ai_suggestions');

    DELETE FROM analytics WHERE user_id = v_user_id;
    v_tables_done := array_append(v_tables_done, 'analytics');

    DELETE FROM notifications WHERE user_id = v_user_id;
    v_tables_done := array_append(v_tables_done, 'notifications');

    DELETE FROM messages WHERE user_id = v_user_id;
    v_tables_done := array_append(v_tables_done, 'messages');

    DELETE FROM matches WHERE user_id = v_user_id;
    v_tables_done := array_append(v_tables_done, 'matches');

    DELETE FROM connected_accounts WHERE user_id = v_user_id;
    v_tables_done := array_append(v_tables_done, 'connected_accounts');

    -- Finally delete user profile
    DELETE FROM users WHERE id = v_user_id;
    v_tables_done := array_append(v_tables_done, 'users');

    -- Mark request as completed
    UPDATE deletion_requests SET
        status = 'COMPLETED',
        completed_at = NOW(),
        tables_processed = v_tables_done
    WHERE id = p_request_id;

    RAISE NOTICE 'Deletion request % completed for user %. Tables: %',
        p_request_id, v_user_id, v_tables_done;

EXCEPTION WHEN OTHERS THEN
    UPDATE deletion_requests SET
        status = 'FAILED',
        error_details = SQLERRM
    WHERE id = p_request_id;
    RAISE;
END;
$$ LANGUAGE plpgsql;
