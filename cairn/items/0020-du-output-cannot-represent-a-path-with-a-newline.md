---
id: 20
title: du output cannot represent a path with a newline
type: bug
status: done
milestone: v1.3
assignee: Oddur Sigurdsson
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: s
area: scanner
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-20

du prints one record per line as `size<TAB>path`, and a path may legally contain both a newline and a tab. macOS and Linux both allow it. So the output format cannot represent every path du can be asked about, and DuMeasurer reads it as if it could.

Measured, on a tree of exactly 7.0M under a directory whose name contains a newline:

    du -skx      7.0M
    DuMeasurer  17.0M     <- 2.4x over
    Walker       7.0M

Over, not under, which is the worse direction: each fragment of the mangled path is read as its own record, and the running total adds all of them. A tab is harmless by luck -- partition("\t") takes the first tab, so the size still parses and only the path is truncated.

Proposal. du -kx <root> only ever prints paths under <root>; that is the invariant to lean on. A line whose path is not under the root is a fragment of something mangled, so the output cannot be trusted for that walk -- kill du and measure it in process instead. The walker is already byte-identical to du and already tested against sparse files, hard links, symlinks and mount points, so the fallback is not new code so much as code that already exists being reached.

Extract the per-directory scan so the walker and the fallback share it rather than growing a second copy.

Acceptance criteria
- [x] A path containing a newline measures the same under both engines
- [x] Detection is by the invariant, not by scanning the path for characters
- [x] The fallback is exercised by a test, not merely available
- [x] Tabs, spaces and non-ASCII in paths stay correct
