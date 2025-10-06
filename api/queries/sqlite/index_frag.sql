-- SQLite không có khái niệm fragmentation như RDBMS khác; tham khảo kích thước index
SELECT
  name AS IndexName,
  type AS ObjectType,
  sql AS CreateDDL
FROM sqlite_master
WHERE type = 'index'
ORDER BY name;