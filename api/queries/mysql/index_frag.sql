-- Approximation using statistics; MySQL không có DMV fragmentation như SQL Server
SELECT
  t.TABLE_SCHEMA   AS DbName,
  t.TABLE_NAME     AS TableName,
  i.INDEX_NAME     AS IndexName,
  i.NON_UNIQUE     AS NonUnique,
  i.SEQ_IN_INDEX   AS SeqInIndex,
  i.CARDINALITY    AS Cardinality,
  t.ENGINE         AS Engine
FROM information_schema.STATISTICS i
JOIN information_schema.TABLES t
  ON t.TABLE_SCHEMA = i.TABLE_SCHEMA
 AND t.TABLE_NAME   = i.TABLE_NAME
WHERE t.TABLE_SCHEMA = :db_name
ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, i.INDEX_NAME, i.SEQ_IN_INDEX;