-- Kích thước chi tiết theo bảng trong DB hiện tại (Postgres xác định DB qua connection)
SELECT
  n.nspname         AS schema_name,
  c.relname         AS table_name,
  ROUND(pg_total_relation_size(c.oid) / 1024.0 / 1024.0, 2) AS total_mb,
  ROUND(pg_relation_size(c.oid) / 1024.0 / 1024.0, 2)       AS data_mb,
  ROUND((pg_total_relation_size(c.oid) - pg_relation_size(c.oid)) / 1024.0 / 1024.0, 2) AS index_mb
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r','p')  -- tables + partitioned tables
ORDER BY pg_total_relation_size(c.oid) DESC;