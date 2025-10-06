-- Basic blocking sessions check (no special privileges required)
SELECT 
    ID AS ProcessId,
    USER AS `User`,
    HOST AS `Host`,
    DB AS DbName,
    COMMAND AS Cmd,
    TIME AS Seconds,
    STATE AS ProcState,
    INFO AS SqlText
FROM information_schema.PROCESSLIST
WHERE COMMAND <> 'Sleep'
  AND STATE IS NOT NULL
  AND STATE <> ''
  AND TIME > 0
ORDER BY TIME DESC;