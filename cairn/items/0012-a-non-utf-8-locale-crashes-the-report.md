---
id: 12
title: A non-UTF-8 locale crashes the report
type: bug
status: done
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
- [x] Every output mode runs clean under PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 LC_ALL=C
- [x] The ASCII rendering is deliberate and readable, not mojibake or question marks
- [x] UTF-8 output is byte-identical to before
- [x] Chosen from the actual stdout encoding, not from the platform
- [x] Tested by forcing the encoding rather than by trusting the environment

## 2026-09-20

The glyph table is the interesting part, not the fallback. Every drawing character in the file now goes through it, and a test walks the source asserting none is written inline -- otherwise the ASCII set drifts out of step with the Unicode one the first time someone adds a row.

That test immediately found six more: an em dash, a breadcrumb chevron and the four arrow keys in the help.

The suite itself was not locale-independent either. Seven tests hardcoded the Unicode glyphs and failed under LC_ALL=C, which is why the c-locale CI job runs the suite as well as the program.
