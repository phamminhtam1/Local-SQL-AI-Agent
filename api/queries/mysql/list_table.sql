-- MySQL: List all tables in a specific database
SELECT 
    table_schema AS database_name,
    table_name AS table_name,
    table_type AS table_type,
    table_rows AS estimated_rows,
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb,
    table_comment AS table_comment,
    create_time AS created_at,
    update_time AS updated_at
FROM information_schema.tables 
WHERE table_schema = :db_name
    AND table_type = 'BASE TABLE'
ORDER BY table_name;
