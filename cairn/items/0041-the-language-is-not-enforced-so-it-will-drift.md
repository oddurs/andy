---
id: 41
title: The language is not enforced, so it will drift
type: chore
status: done
milestone: v2.0
created: 2026-09-21
updated: 2026-09-21
priority: p1
effort: m
area: tests
---

## 2026-09-21

A design language that cannot be checked is a style guide, and style guides
rot. The rules here are mechanical enough to test:

  - the raw curses constants and colour pairs appear only where the palette is
    defined; every drawing call asks for a role by name
  - green, yellow and red are reachable only through the consequence role
  - reverse is reachable only through the selection role
  - bold is reachable only through the heading role
  - every list row is emitted through the one skeleton
  - the header occupies its stated number of lines

Written as tests over the source and over a rendered screen, so a future
change that quietly reintroduces a coloured magnitude fails rather than ships.

Acceptance criteria
- [x] A test reads the source and fails on a raw attribute outside the palette
- [x] A test asserts each hue is reachable through exactly one role
- [x] A test renders a screen and checks the pane geometry
- [x] The tests name the rule they enforce, so a failure teaches it

## 2026-09-21

Checked that the tests can fail, because a test that cannot fail is not enforcement. Reintroduced exactly the bug the language exists to prevent -- a size coloured red by magnitude, reaching past the roles for a raw attribute -- and both source tests failed and named it:

    Tui.draw_body line 3194: curses.A_BOLD
    Tui.draw_body line 3194: _red

The experiment also found a hazard in this environment: cp is aliased to cp -i, so the restore step waited on a y/n prompt forever and left andy containing the deliberate violation. Restored with shutil and verified against the backup with cmp before going on.

Rules enforced: attributes reached only through roles; the palette private; the warm scale only through consequence; reverse only through selection; magnitude never coloured, in the browser or the reports; direction of change carried by the sign; two label-and-value forms sharing one gutter; the header three lines; one rule per pane boundary; the row skeleton order; and the language written down in the source and the README. Each test says in its docstring which rule it is for.
