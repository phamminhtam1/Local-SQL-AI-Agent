-- SQLite health check
SELECT
  'SQLite' AS DatabaseType,
  sqlite_version() AS Version,
  'localhost' AS Hostname,
  0 AS Port,
  'main' AS CurrentDatabase,
  datetime('now') AS CurrentTime,
  (SELECT COUNT(*) FROM pragma_table_list) AS TableCount,
  (SELECT COUNT(*) FROM pragma_index_list('main')) AS IndexCount,
  (SELECT COUNT(*) FROM pragma_foreign_key_list('main')) AS ForeignKeyCount;