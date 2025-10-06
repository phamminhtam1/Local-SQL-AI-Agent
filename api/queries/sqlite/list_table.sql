-- SQLite: List all tables in the database
-- Note: SQLite doesn't have schemas, so db_name parameter is ignored
SELECT 
    'main' AS database_name,
    name AS table_name,
    'BASE TABLE' AS table_type,
    (SELECT COUNT(*) FROM pragma_table_info(name)) AS column_count,
    ROUND((SELECT SUM(pgsize) FROM dbstat WHERE name = t.name) / 1024.0 / 1024.0, 2) AS size_mb,
    'No description available' AS table_comment,
    NULL AS created_at,
    NULL AS updated_at
FROM sqlite_master t
WHERE type = 'table'
    AND name NOT LIKE 'sqlite_%'
ORDER BY name;
