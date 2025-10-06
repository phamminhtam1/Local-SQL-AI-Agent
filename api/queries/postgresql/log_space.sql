-- MySQL equivalent for log space information across all databases
-- Total size per database (MB)
SELECT
  d.datname AS database_name,
  ROUND(pg_database_size(d.datname) / 1024.0 / 1024.0, 2) AS size_mb
FROM pg_database d
WHERE d.datistemplate = false
ORDER BY pg_database_size(d.datname) DESC;