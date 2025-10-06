-- MySQL health check
SELECT
  'MySQL' AS DatabaseType,
  VERSION() AS Version,
  @@hostname AS Hostname,
  @@port AS Port,
  DATABASE() AS CurrentDatabase,
  NOW() AS CurrentTime,
  @@max_connections AS MaxConnections,
  -- Use status variables instead of invalid @@max_used_connections
  (SELECT VARIABLE_VALUE
     FROM performance_schema.global_status
     WHERE VARIABLE_NAME = 'Max_used_connections') AS MaxUsedConnections,
  (SELECT VARIABLE_VALUE
     FROM performance_schema.global_status
     WHERE VARIABLE_NAME = 'Threads_connected') AS CurrentConnections,
  ROUND(@@key_buffer_size / 1024 / 1024, 2) AS KeyBufferSizeMB,
  ROUND(@@innodb_buffer_pool_size / 1024 / 1024, 2) AS InnoDBBufferPoolSizeMB,
  @@slow_query_log AS SlowQueryLogEnabled,
  @@long_query_time AS LongQueryTime,
  (SELECT COUNT(*) FROM information_schema.processlist) AS ActiveConnections;