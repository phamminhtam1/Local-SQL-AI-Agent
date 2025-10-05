SELECT
    blocking_session_id AS BlockingSessionID,
    session_id AS BlockedSessionID,
    wait_type,
    wait_time,
    wait_resource
FROM sys.dm_exec_requests
WHERE blocking_session_id <> 0;