-- Redo log files info (log space perspective)
SELECT
  lf.group#                    AS group_id,
  lf.member                    AS member_path,
  ROUND(l.bytes/1024/1024, 2)  AS log_size_mb,
  l.status                     AS log_status
FROM v$log l
JOIN v$logfile lf ON lf.group# = l.group#
ORDER BY lf.group#, lf.member;