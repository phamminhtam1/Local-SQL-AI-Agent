-- PostgreSQL health check
SELECT
  'PostgreSQL' AS DatabaseType,
  version() AS Version,
  inet_server_addr() AS Hostname,
  inet_server_port() AS Port,
  current_database() AS CurrentDatabase,
  now() AS CurrentTime,
  (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS MaxConnections,
  (SELECT count(*) FROM pg_stat_activity) AS CurrentConnections,
  (SELECT setting FROM pg_settings WHERE name = 'shared_buffers') AS SharedBuffers,
  (SELECT setting FROM pg_settings WHERE name = 'work_mem') AS WorkMem,
  (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') AS ActiveConnections;