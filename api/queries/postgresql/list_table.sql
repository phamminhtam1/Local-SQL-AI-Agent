-- PostgreSQL: List all tables in a specific database
SELECT 
    schemaname AS database_name,
    tablename AS table_name,
    'BASE TABLE' AS table_type,
    n_tup_ins AS estimated_rows,
    ROUND(pg_total_relation_size(schemaname||'.'||tablename) / 1024 / 1024, 2) AS size_mb,
    obj_description(c.oid) AS table_comment,
    NULL AS created_at,
    NULL AS updated_at
FROM pg_tables pt
LEFT JOIN pg_class c ON c.relname = pt.tablename
WHERE schemaname = :db_name
    AND schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY tablename;
