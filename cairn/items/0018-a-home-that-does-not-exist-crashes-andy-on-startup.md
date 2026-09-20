---
id: 18
title: A HOME that does not exist crashes andy on startup
type: bug
status: done
milestone: v1.2
created: 2026-09-20
updated: 2026-09-20
priority: p1
effort: s
area: platform
---

## What happens

`Model.__init__` calls `shutil.disk_usage(HOME)` with no guard:

```
  File "andy", line 1416, in __init__
    self.disk = shutil.disk_usage(HOME)
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/andy-nonexistent'
```

A traceback, before andy has done anything, because of a directory it never
needed to read.

## Why this matters off a Mac

macOS always has a real home. Linux frequently does not:

- a container running as a uid with no entry in `/etc/passwd`, where `HOME` is
  inherited or absent
- a systemd unit with `HOME` unset, or set to a `RuntimeDirectory` that has not
  been created yet
- `su` without `-`, which keeps the previous user's `HOME`
- a CI image where `HOME` points somewhere the checkout step later replaced

Found by a test that set `HOME` to a path it had not created — which is exactly
what those environments do.

## Proposal

Fall back rather than die: the volume andy is reporting on is a header
detail, not the scan. Try `HOME`, then the working directory, then the root,
then give up and report zeros. The report already handles a zero total, because
`used` of zero is a valid answer.

## Acceptance criteria

- [x] Every mode runs with `HOME` set to a path that does not exist
- [x] The volume line degrades rather than the program
- [x] A rescan in the TUI uses the same fallback
- [x] Tested with a missing `HOME`, not only a present one
