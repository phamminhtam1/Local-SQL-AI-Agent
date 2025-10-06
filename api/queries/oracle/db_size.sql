-- Kích thước theo object trong schema hiện tại (ít quyền, chạy được với user thường)
SELECT
  (SELECT SYS_CONTEXT('USERENV','CURRENT_SCHEMA') FROM dual) AS owner,
  segment_name AS object_name,
  segment_type,
  ROUND(SUM(bytes) / 1024 / 1024, 2) AS size_mb
FROM user_segments
GROUP BY segment_name, segment_type
ORDER BY size_mb DESC;