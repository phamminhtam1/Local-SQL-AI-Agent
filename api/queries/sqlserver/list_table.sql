-- SQL Server: List all tables in a specific database
SELECT 
    DB_NAME() AS database_name,
    t.name AS table_name,
    'BASE TABLE' AS table_type,
    p.rows AS estimated_rows,
    ROUND(SUM(a.total_pages) * 8 / 1024, 2) AS size_mb,
    ISNULL(ep.value, 'No description available') AS table_comment,
    t.create_date AS created_at,
    t.modify_date AS updated_at
FROM sys.tables t
INNER JOIN sys.indexes i ON t.object_id = i.object_id
INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
LEFT JOIN sys.extended_properties ep ON t.object_id = ep.major_id AND ep.minor_id = 0 AND ep.name = 'MS_Description'
WHERE t.is_ms_shipped = 0
GROUP BY t.name, p.rows, ep.value, t.create_date, t.modify_date
ORDER BY t.name;
