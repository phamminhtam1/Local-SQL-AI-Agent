-- Oracle health check
SELECT
  'Oracle' AS DatabaseType,
  banner AS Version,
  host_name AS Hostname,
  instance_name AS InstanceName,
  sys_context('USERENV', 'DB_NAME') AS CurrentDatabase,
  systimestamp AS CurrentTime,
  (SELECT value FROM v$parameter WHERE name = 'processes') AS MaxProcesses,
  (SELECT COUNT(*) FROM v$session) AS CurrentSessions,
  (SELECT COUNT(*) FROM v$session WHERE status = 'ACTIVE') AS ActiveSessions,
  (SELECT COUNT(*) FROM v$lock WHERE block = 1) AS BlockingLocks
FROM v$instance;