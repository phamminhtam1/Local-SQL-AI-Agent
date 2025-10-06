SELECT
  bl.pid                  AS BlockingPid,
  wl.pid                  AS BlockedPid,
  wl.usename              AS BlockedUser,
  bl.usename              AS BlockingUser,
  wl.datname              AS DatabaseName,
  wl.state                AS State,
  wl.wait_event_type      AS WaitEventType,
  wl.wait_event           AS WaitEvent
FROM pg_locks l1
JOIN pg_stat_activity wl ON wl.pid = l1.pid
JOIN pg_locks l2
  ON l1.locktype = l2.locktype
 AND l1.DATABASE IS NOT DISTINCT FROM l2.DATABASE
 AND l1.relation IS NOT DISTINCT FROM l2.relation
 AND l1.page IS NOT DISTINCT FROM l2.page
 AND l1.tuple IS NOT DISTINCT FROM l2.tuple
 AND l1.classid IS NOT DISTINCT FROM l2.classid
 AND l1.objid IS NOT DISTINCT FROM l2.objid
 AND l1.objsubid IS NOT DISTINCT FROM l2.objsubid
 AND l1.pid <> l2.pid
JOIN pg_stat_activity bl ON bl.pid = l2.pid
WHERE NOT l1.granted AND l2.granted
ORDER BY wl.datname, wl.pid;