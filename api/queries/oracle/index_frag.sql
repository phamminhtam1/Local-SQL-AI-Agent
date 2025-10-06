SELECT
  i.owner,
  i.index_name,
  i.table_name,
  i.blevel,
  i.leaf_blocks,
  i.distinct_keys,
  i.clustering_factor
FROM dba_indexes i
WHERE i.owner = UPPER(:schema_name)
ORDER BY i.leaf_blocks DESC;