-- Oracle: List all tables in a specific database/schema
SELECT 
    owner AS database_name,
    table_name AS table_name,
    'BASE TABLE' AS table_type,
    num_rows AS estimated_rows,
    ROUND(bytes / 1024 / 1024, 2) AS size_mb,
    comments AS table_comment,
    created AS created_at,
    last_ddl_time AS updated_at
FROM all_tables t
LEFT JOIN all_tab_comments tc ON t.owner = tc.owner AND t.table_name = tc.table_name
LEFT JOIN (
    SELECT 
        owner,
        segment_name,
        SUM(bytes) AS bytes
    FROM dba_segments 
    WHERE segment_type = 'TABLE'
    GROUP BY owner, segment_name
) s ON t.owner = s.owner AND t.table_name = s.segment_name
WHERE t.owner = UPPER(:db_name)
ORDER BY t.table_name;
