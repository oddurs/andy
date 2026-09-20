---
id: 13
title: andy counts its own cache directory
type: bug
status: backlog
milestone: v1.2
created: 2026-09-20
updated: 2026-09-20
priority: p3
effort: s
area: catalog
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-20

Trivial, and it kept fooling me. andy caches its scan in ~/.cache/andy, and ~/.cache is a catalog entry, so the second run of any pair reports 4096 bytes of "other in ~/.cache" that the first run created. It cost me two false bug reports while testing the measurement engines -- twice the two engines appeared to disagree by exactly one block, and twice it was this.

Proposal: give it a row of its own rather than hide it. Nesting subtraction then takes it out of "other in ~/.cache", it is named rather than lurking, and andy is honest about its own footprint -- which is the right answer for a tool whose entire claim is telling you where your disk went.

Acceptance criteria
- [ ] andy accounts for its own cache under its own name
- [ ] "other in ~/.cache" no longer moves because andy ran
- [ ] Two consecutive scans of the same tree report the same total
