-- Kích thước chi tiết theo bảng trong một schema (database)
SELECT
  TABLE_SCHEMA   AS DatabaseName,
  TABLE_NAME     AS TableName,
  ROUND(DATA_LENGTH / 1024 / 1024, 2)  AS DataMB,
  ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS IndexMB,
  ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS TotalMB
FROM information_schema.tables
WHERE TABLE_SCHEMA = :db_name
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;