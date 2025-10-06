SELECT
  s1.sid        AS BlockingSid,
  s2.sid        AS BlockedSid,
  s1.username   AS BlockingUser,
  s2.username   AS BlockedUser,
  s2.event      AS WaitEvent,
  s2.seconds_in_wait AS SecondsInWait
FROM v$lock l1
JOIN v$lock l2 ON l1.id1 = l2.id1 AND l1.id2 = l2.id2
JOIN v$session s1 ON s1.sid = l1.sid
JOIN v$session s2 ON s2.sid = l2.sid
WHERE l1.block = 1 AND l2.request > 0
ORDER BY s2.seconds_in_wait DESC;