---
id: 11
title: andy will not start on a Python without curses
type: bug
status: backlog
milestone: v1.2
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: s
area: platform
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-20

andy imports curses at module scope, and the Tui class body evaluates curses constants at class-definition time. So a Python built without _curses cannot run andy at all -- not --json, not --tree, not --commands, none of which want a terminal.

Reproduced by moving _curses out of the way:

    ModuleNotFoundError: No module named _curses

This is not exotic. Minimal container images, Python built from source without ncurses headers, and some distro python3 packages all land here, and those are exactly the machines where someone wants andy --json from a script.

Proposal: import curses in a try/except at module scope and let it be None; move the three mouse constants off the class body into setup(), which only runs inside curses.wrapper. -i then fails with a sentence instead of a traceback, and every other mode works.

Acceptance criteria
- [ ] andy --json, --tree, --commands and the default report all work with no _curses
- [ ] andy -i without curses prints one clear line and exits non-zero
- [ ] With curses present nothing changes
- [ ] A test removes curses from sys.modules and proves it
