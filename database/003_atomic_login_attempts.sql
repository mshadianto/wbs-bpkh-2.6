-- Migration 003: Atomic login attempt increment
-- Fixes TOCTOU race condition in login attempt tracking

CREATE OR REPLACE FUNCTION increment_login_attempts(p_user_id UUID)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_attempts INT;
    v_locked_until TIMESTAMPTZ;
BEGIN
    UPDATE users
    SET login_attempts = login_attempts + 1,
        locked_until = CASE
            WHEN login_attempts + 1 >= 5
            THEN NOW() + INTERVAL '30 minutes'
            ELSE locked_until
        END,
        updated_at = NOW()
    WHERE id = p_user_id
    RETURNING login_attempts, locked_until
    INTO v_attempts, v_locked_until;

    RETURN json_build_object(
        'attempts', COALESCE(v_attempts, 0),
        'locked_until', v_locked_until
    );
END;
$$;
