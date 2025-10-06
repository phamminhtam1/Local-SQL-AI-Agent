-- Tổng kích thước database (MB)
SELECT
  'main' AS DatabaseName,
  ROUND(
    ( (SELECT page_count FROM pragma_page_count()) *
      (SELECT page_size  FROM pragma_page_size()) ) / 1048576.0
  , 2) AS SizeMB;