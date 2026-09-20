---
id: 15
title: CI covers one shape of Linux, and Linux has several
type: chore
status: done
milestone: v1.2
created: 2026-09-20
updated: 2026-09-20
priority: p1
effort: m
area: tests
---

## 2026-09-20

The workflow runs ubuntu-latest and calls it Linux. The bugs in 0010, 0011 and 0012 would all have passed that job, because glibc + a full Python + a UTF-8 locale + default XDG paths is the one configuration where andy already worked.

Proposal: add jobs for the shapes that break it.

- Alpine, for musl and busybox du/find. Verified by hand already: busybox is fine and both engines agree to the byte, so this is about keeping it that way.
- A Python with _curses removed, for 0011.
- PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 LC_ALL=C, for 0012.
- XDG_CACHE_HOME and friends pointed somewhere else, for 0010.

Each of these is a few lines and they run in seconds. The point is that all four are configurations a real user has and CI did not.

Acceptance criteria
- [x] Alpine job: suite green, both engines agree on busybox du
- [x] no-curses job: every non-TUI mode works, -i fails cleanly
- [x] C-locale job: every output mode runs clean
- [x] XDG job: andy finds files in relocated XDG directories
- [x] All green on GitHub, not just locally
