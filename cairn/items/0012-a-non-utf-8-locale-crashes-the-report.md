---
id: 12
title: A non-UTF-8 locale crashes the report
type: bug
status: backlog
milestone: v1.2
created: 2026-09-20
updated: 2026-09-20
priority: p1
effort: m
area: output
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-20

The report prints a middle dot, box drawing, eighth-blocks, an ellipsis and a braille spinner. In a non-UTF-8 locale that is a crash:

    UnicodeEncodeError: ascii codec cannot encode character · in position 20

Python normally saves andy here: PEP 538 coerces the C locale to C.UTF-8. With that coercion defeated -- PYTHONCOERCECLOCALE=0, which some containers and init systems set, or a genuinely 8-bit locale like en_US.ISO-8859-1 -- the default report dies on its first line. macOS never sees this because it is UTF-8 everywhere.

Proposal: decide once at startup whether stdout can encode the glyphs, and keep an ASCII set for when it cannot -- = for a full block, a plain period, a hyphen rule, ... for the ellipsis, >= for the floor marker. Plus errors="replace" on stdout as a backstop, so an encoding nobody anticipated degrades instead of raising. The TUI draws through curses and gets the same glyph set, so it degrades the same way.

Not a fallback nobody sees: -m/--min output piped into a file or a log under systemd hits this.

Acceptance criteria
- [ ] Every output mode runs clean under PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 LC_ALL=C
- [ ] The ASCII rendering is deliberate and readable, not mojibake or question marks
- [ ] UTF-8 output is byte-identical to before
- [ ] Chosen from the actual stdout encoding, not from the platform
- [ ] Tested by forcing the encoding rather than by trusting the environment
