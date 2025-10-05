SET NOCOUNT ON;

DECLARE @Now DATETIME = GETDATE();

-----------------------------------------
-- 1) ServerInfo
-----------------------------------------
DECLARE @ServerInfo NVARCHAR(MAX);
;WITH SI AS (
SELECT
    HostName      = CAST(SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS VARCHAR(100)),
    InstanceName  = CAST(SERVERPROPERTY('ServerName') AS VARCHAR(100)),
    SqlVersion    = CONCAT(
                    CASE
                        WHEN CONVERT(VARCHAR(50), SERVERPROPERTY('ProductVersion')) LIKE '16%' THEN 'SQL Server 2022'
                        WHEN CONVERT(VARCHAR(50), SERVERPROPERTY('ProductVersion')) LIKE '15%' THEN 'SQL Server 2019'
                        WHEN CONVERT(VARCHAR(50), SERVERPROPERTY('ProductVersion')) LIKE '14%' THEN 'SQL Server 2017'
                        WHEN CONVERT(VARCHAR(50), SERVERPROPERTY('ProductVersion')) LIKE '13%' THEN 'SQL Server 2016'
                        WHEN CONVERT(VARCHAR(50), SERVERPROPERTY('ProductVersion')) LIKE '12%' THEN 'SQL Server 2014'
                        ELSE 'Unknown'
                    END, ' (', CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50)), ')'
                    ),
    Edition       = CAST(SERVERPROPERTY('Edition') AS VARCHAR(100)),
    CpuCount      = (SELECT cpu_count FROM sys.dm_os_sys_info),
    TotalMemoryGB = CAST((SELECT physical_memory_kb / 1024.0 / 1024.0 FROM sys.dm_os_sys_info) AS DECIMAL(10,0)),
    SqlStartTime  = (SELECT sqlserver_start_time FROM sys.dm_os_sys_info)
)
SELECT @ServerInfo = (SELECT * FROM SI FOR JSON PATH, WITHOUT_ARRAY_WRAPPER);

-----------------------------------------
-- 2) EOL (rough mapping by version token)
-----------------------------------------
DECLARE @EOL NVARCHAR(MAX);
DECLARE @VersionString NVARCHAR(4000) = @@VERSION;
DECLARE @SqlVersionDesc NVARCHAR(100), @SqlEOLDate DATE;

IF @VersionString LIKE '%SQL Server 2022%' SET @SqlVersionDesc = 'SQL Server 2022';
ELSE IF @VersionString LIKE '%SQL Server 2019%' SET @SqlVersionDesc = 'SQL Server 2019';
ELSE IF @VersionString LIKE '%SQL Server 2017%' SET @SqlVersionDesc = 'SQL Server 2017';
ELSE IF @VersionString LIKE '%SQL Server 2016%' SET @SqlVersionDesc = 'SQL Server 2016';
ELSE IF @VersionString LIKE '%SQL Server 2014%' SET @SqlVersionDesc = 'SQL Server 2014';
ELSE SET @SqlVersionDesc = 'Unknown';

SET @SqlEOLDate =
CASE @SqlVersionDesc
    WHEN 'SQL Server 2022' THEN '2033-01-11'
    WHEN 'SQL Server 2019' THEN '2030-01-08'
    WHEN 'SQL Server 2017' THEN '2027-10-12'
    WHEN 'SQL Server 2016' THEN '2026-07-14'
    WHEN 'SQL Server 2014' THEN '2024-07-09'
    ELSE NULL
END;

SELECT @EOL = (
SELECT @SqlVersionDesc AS SqlVersion, @SqlEOLDate AS SqlEolDate
FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
);

-----------------------------------------
-- 3) DbSpace (per user DB)
-----------------------------------------
DECLARE @DbSpace NVARCHAR(MAX);
IF OBJECT_ID('tempdb..#DbSpace') IS NOT NULL DROP TABLE #DbSpace;
CREATE TABLE #DbSpace (
DatabaseName     SYSNAME,
StateDesc        NVARCHAR(100),
RecoveryModel    NVARCHAR(100),
TotalSizeGB      DECIMAL(12,2),
FreeSpaceGB      DECIMAL(12,2),
FreeSpacePercent DECIMAL(6,2)
);

DECLARE @DbName SYSNAME, @SQL NVARCHAR(MAX);

DECLARE cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name FROM sys.databases WHERE database_id > 4 AND state_desc = 'ONLINE';
OPEN cur; FETCH NEXT FROM cur INTO @DbName;
WHILE @@FETCH_STATUS = 0
BEGIN
SET @SQL = N'
USE ' + QUOTENAME(@DbName) + N';
INSERT INTO #DbSpace
SELECT
    DB_NAME(),
    d.state_desc,
    d.recovery_model_desc,
    CAST(SUM(mf.size) * 8.0 / 1024 / 1024 AS DECIMAL(12,2)),
    CAST(SUM(mf.size - FILEPROPERTY(mf.name, ''SpaceUsed'')) * 8.0 / 1024 / 1024 AS DECIMAL(12,2)),
    CAST(CASE WHEN SUM(mf.size)>0
    THEN (SUM(mf.size - FILEPROPERTY(mf.name, ''SpaceUsed'')) * 100.0) / SUM(mf.size)
    ELSE 0 END AS DECIMAL(6,2))
FROM sys.database_files mf
CROSS JOIN sys.databases d
WHERE d.name = DB_NAME()
GROUP BY d.state_desc, d.recovery_model_desc;';
EXEC sys.sp_executesql @SQL;
FETCH NEXT FROM cur INTO @DbName;
END
CLOSE cur; DEALLOCATE cur;

SELECT @DbSpace = (SELECT * FROM #DbSpace ORDER BY FreeSpacePercent ASC FOR JSON PATH);

-----------------------------------------
-- 4) TopTables (Top 10 across all DBs)
-----------------------------------------
DECLARE @TopTables NVARCHAR(MAX);
IF OBJECT_ID('tempdb..#TopTables') IS NOT NULL DROP TABLE #TopTables;
CREATE TABLE #TopTables(
DatabaseName  SYSNAME,
SchemaName    SYSNAME,
TableName     SYSNAME,
TotalRows     BIGINT,
TotalSpaceMB  DECIMAL(18,2),
UsedSpaceMB   DECIMAL(18,2),
UnusedSpaceMB DECIMAL(18,2)
);

DECLARE cur2 CURSOR LOCAL FAST_FORWARD FOR
SELECT name FROM sys.databases WHERE database_id > 4 AND state_desc = 'ONLINE';
OPEN cur2; FETCH NEXT FROM cur2 INTO @DbName;
WHILE @@FETCH_STATUS = 0
BEGIN
SET @SQL = N'
USE ' + QUOTENAME(@DbName) + N';
INSERT INTO #TopTables
SELECT
    DB_NAME(),
    s.name, t.name,
    SUM(p.rows),
    CAST(SUM(au.total_pages)*8.0/1024 AS DECIMAL(18,2)),
    CAST(SUM(au.used_pages)*8.0/1024 AS DECIMAL(18,2)),
    CAST(SUM(au.total_pages - au.used_pages)*8.0/1024 AS DECIMAL(18,2))
FROM sys.tables t
JOIN sys.indexes i           ON t.object_id = i.object_id
JOIN sys.partitions p        ON i.object_id = p.object_id AND i.index_id = p.index_id
JOIN sys.allocation_units au ON p.partition_id = au.container_id
JOIN sys.schemas s           ON t.schema_id = s.schema_id
WHERE i.index_id <= 1
GROUP BY s.name, t.name;';
EXEC sys.sp_executesql @SQL;
FETCH NEXT FROM cur2 INTO @DbName;
END
CLOSE cur2; DEALLOCATE cur2;

;WITH T AS (
SELECT TOP 10
    DatabaseName, SchemaName, TableName, TotalRows,
    CAST(TotalSpaceMB/1024.0 AS DECIMAL(18,1)) AS TotalSpaceGB,
    CAST(UsedSpaceMB/1024.0  AS DECIMAL(18,1)) AS UsedSpaceGB,
    CAST(UnusedSpaceMB/1024.0 AS DECIMAL(18,1)) AS UnusedSpaceGB
FROM #TopTables
ORDER BY TotalSpaceMB DESC
)
SELECT @TopTables = (SELECT * FROM T FOR JSON PATH);

-----------------------------------------
-- 5) BlockingNow (live blocking chains)
-----------------------------------------
DECLARE @BlockingNow NVARCHAR(MAX);
;WITH REQ AS (
SELECT
    r.session_id, r.blocking_session_id, r.status, r.wait_type, r.wait_time,
    r.cpu_time, r.total_elapsed_time, r.database_id,
    DB_NAME(r.database_id) AS DatabaseName,
    SUBSTRING(qt.text, (r.statement_start_offset/2)+1,
    (CASE WHEN r.statement_end_offset = -1
            THEN LEN(CONVERT(NVARCHAR(MAX), qt.text)) * 2
            ELSE r.statement_end_offset END - r.statement_start_offset)/2 + 1) AS RunningStatement,
    qt.text AS BatchText
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) AS qt
WHERE r.session_id <> @@SPID
),
BLK AS (
SELECT * FROM REQ WHERE blocking_session_id <> 0
)
SELECT @BlockingNow = (
SELECT
    b.session_id          AS BlockedSessionId,
    b.blocking_session_id AS BlockerSessionId,
    b.status, b.wait_type, b.wait_time,
    b.cpu_time, b.total_elapsed_time,
    b.DatabaseName,
    b.RunningStatement
FROM BLK b
ORDER BY b.wait_time DESC
FOR JSON PATH
);

-----------------------------------------
-- 6) Deadlocks7d from system_health XE (safe timestamp conversion)
-----------------------------------------
DECLARE @Deadlocks7d NVARCHAR(MAX);
;WITH X AS (
SELECT CAST(xet.target_data AS XML) AS target_data
FROM sys.dm_xe_sessions xes
JOIN sys.dm_xe_session_targets xet
    ON xes.address = xet.event_session_address
WHERE xes.name = 'system_health'
    AND xet.target_name = 'ring_buffer'
),
D AS (
SELECT
    -- Convert XE UTC timestamp to local time safely
    DATEADD(hh,
            DATEDIFF(hh, GETUTCDATE(), SYSDATETIME()),
            CONVERT(datetime2, n.value('(data[@name="timestamp"]/value)[1]','datetime2'))
    ) AS [UtcTime],
    n.query('.') AS DeadlockEventXml
FROM X
CROSS APPLY target_data.nodes('//RingBufferTarget/event[@name="xml_deadlock_report"]') AS t(n)
)
SELECT @Deadlocks7d = (
SELECT CONVERT(date, [UtcTime]) AS [Date],
        COUNT(*) AS DeadlockCount,
        MAX([UtcTime]) AS MostRecent
FROM D
WHERE [UtcTime] >= DATEADD(DAY, -7, @Now)
GROUP BY CONVERT(date, [UtcTime])
ORDER BY [Date] DESC
FOR JSON PATH
);

-----------------------------------------
-- 7) FailedJobs7d (details) + per-day counts
-----------------------------------------
DECLARE @FailedJobs7d NVARCHAR(MAX), @FailedJobsPerDay7d NVARCHAR(MAX);

WITH JobLastRuns AS (
SELECT
    sj.name AS JobName,
    sc.name AS Category,
    CASE sj.enabled WHEN 1 THEN 'True' ELSE 'False' END AS Enabled,
    sjh.run_date, sjh.run_time, sjh.run_status,
    ROW_NUMBER() OVER (PARTITION BY sj.job_id ORDER BY sjh.run_date DESC, sjh.run_time DESC) AS rn
FROM msdb.dbo.sysjobs sj
JOIN msdb.dbo.syscategories sc ON sj.category_id = sc.category_id
JOIN msdb.dbo.sysjobhistory sjh ON sj.job_id = sjh.job_id AND sjh.step_id = 0
)
SELECT @FailedJobs7d = (
SELECT
    JobName,
    Category,
    Enabled,
    CASE run_status WHEN 0 THEN 'FAILED'
                    WHEN 1 THEN 'SUCCESS'
                    WHEN 2 THEN 'RETRY'
                    WHEN 3 THEN 'CANCELLED'
                    ELSE 'UNKNOWN' END AS LastOutcome,
    CONVERT(datetime,
    STUFF(STUFF(CAST(run_date AS varchar(8)),7,0,'-'),5,0,'-') + ' ' +
    STUFF(STUFF(RIGHT('000000'+CAST(run_time AS varchar(6)),6),3,0,':'),6,0,':')
    ) AS LastRun
FROM JobLastRuns
WHERE rn = 1
    AND run_status = 0
    AND CONVERT(datetime,
    STUFF(STUFF(CAST(run_date AS varchar(8)),7,0,'-'),5,0,'-') + ' ' +
    STUFF(STUFF(RIGHT('000000'+CAST(run_time AS varchar(6)),6),3,0,':'),6,0,':')
    ) >= DATEADD(DAY,-7,@Now)
ORDER BY LastRun DESC
FOR JSON PATH
);

WITH Hist AS (
SELECT
    CONVERT(date,
    STUFF(STUFF(CAST(h.run_date AS varchar(8)),7,0,'-'),5,0,'-')
    ) AS RunDate,
    h.run_status
FROM msdb.dbo.sysjobhistory h
WHERE h.step_id = 0
    AND CONVERT(datetime,
    STUFF(STUFF(CAST(h.run_date AS varchar(8)),7,0,'-'),5,0,'-') + ' ' +
    STUFF(STUFF(RIGHT('000000'+CAST(h.run_time AS varchar(6)),6),3,0,':'),6,0,':')
    ) >= DATEADD(DAY,-7,@Now)
)
SELECT @FailedJobsPerDay7d = (
SELECT RunDate AS [Date],
        SUM(CASE WHEN run_status = 0 THEN 1 ELSE 0 END) AS Failed,
        SUM(CASE WHEN run_status = 1 THEN 1 ELSE 0 END) AS Succeeded
FROM Hist
GROUP BY RunDate
ORDER BY [Date] DESC
FOR JSON PATH
);

-----------------------------------------
-- Final single JSON
-----------------------------------------
SELECT
@ServerInfo         AS ServerInfo,
@EOL                AS EOL,
@DbSpace            AS DbSpace,
@TopTables          AS TopTables,
@BlockingNow        AS BlockingNow,
@Deadlocks7d        AS Deadlocks7d,
@FailedJobs7d       AS FailedJobs7d,
@FailedJobsPerDay7d AS FailedJobsPerDay7d
FOR JSON PATH, WITHOUT_ARRAY_WRAPPER;