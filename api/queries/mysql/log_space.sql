-- MySQL equivalent for log space information across all databases
SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Total_Size_MB',
    ROUND(SUM(data_length) / 1024 / 1024, 2) AS 'Data_Size_MB',
    ROUND(SUM(index_length) / 1024 / 1024, 2) AS 'Index_Size_MB',
    COUNT(*) AS 'Table_Count'
FROM information_schema.tables 
WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
GROUP BY table_schema
ORDER BY SUM(data_length + index_length) DESC;
