---
id: 23
title: The interactive browser has no tests at all
type: chore
status: done
milestone: v1.3
assignee: Oddur Sigurdsson
created: 2026-09-20
updated: 2026-09-20
priority: p1
effort: l
area: tests
---

## 2026-09-20

The interactive browser is about a third of the program and no test touches it. Everything it does -- row building, filtering, sorting, expansion, the treemap layout at a given size, mouse hit-testing, the detail pane, rescan -- is reachable only by a person looking at it.

The excuse is that it needs a terminal. It does not need much of one: curses can be driven through a pty, and most of the logic is pure functions over a Model that the other tests already build. The parts worth testing are the parts with arithmetic in them: which rows are visible at a given cursor and height, what the filter selects, what a click at (x, y) resolves to, what the map draws into a given rectangle.

Proposal. Two layers.

A headless layer for the logic: construct a Tui against a stub screen, drive build_rows, filtering, sorting, expansion, movement, scrolling and zone hit-testing directly. No pty, no curses, fast enough to run with everything else.

A pty layer for the parts that genuinely need a terminal: that it starts, draws, responds to keys, and exits cleanly. One test per mode -- tree, map, help, filter, detail, rescan -- asserting no traceback and a clean exit, which is what a person checks by hand today.

Both must skip cleanly where curses is missing, since 0011 made that a supported configuration.

Acceptance criteria
- [x] Row building, filtering, sorting and expansion are tested headlessly
- [x] Cursor movement and scrolling are tested against a known height
- [x] Mouse zone resolution is tested, including overlapping zones
- [x] The map is tested at sizes where cells do and do not fit
- [x] A pty test drives the real program through each view and quits cleanly
- [x] The suite still runs without a terminal, and without curses

## 2026-09-20

Two layers, as proposed, and the headless one paid for itself before it was finished.

Testing the browser needed one small change to it: setup() did two unrelated jobs, putting the terminal into the right mode and choosing colour pairs and mouse bitmasks. The second needs no terminal -- start_color simply raises without one and the fallback is the same monochrome path a colourless terminal takes -- so it is now styles(), and the drawing code can be pointed at a screen object that records instead of renders. Nothing else about the browser changed to make it testable.

Two real bugs fell out, neither of which a person would have found by using it normally:

0024, a crash. draw_footer drops key hints until they fit, popping index 4 once six or fewer remain -- which raises IndexError at four or fewer. Any terminal under about 30 columns took the browser down. Eleven hundred lines of drawing code had never been run at a width nobody happened to try.

0025, silence. build_rows dropped every row with no size and no children, which is exactly the shape of a location whose walk never finished. The browser omitted the locations it could not measure, while --tree and the report both name them. draw_body has a branch rendering those rows as "?" that could never once have been reached.

The pty layer waits for the scan to publish a count rather than sleeping a fixed six seconds, because the first version took the suite from 12s to 72s and a suite that slow stops being run.
