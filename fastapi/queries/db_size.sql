SELECT
    DB_NAME(database_id) AS DatabaseName,
    Name AS FileName,
    type_desc AS FileType,
    size * 8 / 1024 AS SizeMB
FROM sys.master_files
WHERE database_id = DB_ID(:db_name);