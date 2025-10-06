-- Ước lượng fragmentation qua bloat (pg_stat_user_indexes + pg_class)
-- Cần quyền đọc catalog; chính xác hơn nếu có extension pgstattuple
WITH idx AS (
  SELECT
    n.nspname AS schema,
    c.relname AS index_name,
    c.relpages AS pages,
    pg_relation_size(c.oid) AS index_size
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE c.relkind = 'i'
)
SELECT
  schema,
  index_name,
  index_size,
  pages,
  ROUND(GREATEST((pages - (index_size / current_setting('block_size')::int))::numeric, 0), 2) AS approx_free_pages
FROM idx
ORDER BY index_size DESC
LIMIT 200;