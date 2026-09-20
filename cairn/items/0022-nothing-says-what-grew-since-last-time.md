---
id: 22
title: Nothing says what grew since last time
type: feature
status: done
milestone: v1.3
assignee: Oddur Sigurdsson
created: 2026-09-20
updated: 2026-09-20
priority: p1
effort: m
area: output
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-20

andy answers "where has my disk gone". The more useful question, once you have run it twice, is "what is taking it now" -- and andy has been one subtraction away from answering that since 1.0 without ever offering it.

The cache already holds a size per path and a timestamp:

    {"ts": ..., "version": ..., "roots": [...], "sizes": {path: bytes}, "found": [...]}

So the delta is the current measurement minus the cached one, and the age of the comparison is the age of the cache.

Proposal. `--delta` (and a column in the interactive view) showing the change since the previous scan: `+2.1G`, `-840M`, or nothing for unchanged. Sorted by change rather than by size, because the thing that grew 2G last night matters more than the 30G that has been there all year.

What it must not do is lie about the interval. The cache is whenever andy last ran, which might be ten minutes or three weeks ago, so the output says so: "since 3 days ago" rather than an unqualified number. A path with no cached figure is new, and says "new" rather than showing its whole size as growth. A path that has gone says so too, because a cache entry that has vanished is the most interesting kind of change.

This is the one place andy gets to be about time rather than about now, so the honest framing matters more than the arithmetic.

Acceptance criteria
- [x] `--delta` reports change per location against the previous scan
- [x] The age of the comparison is stated, never implied
- [x] A location with no previous figure reads as new, not as growth
- [x] A location that has disappeared is reported
- [x] `--json` carries the previous figure and the interval
- [x] Nothing to compare against is a clear sentence, not an empty table

## 2026-09-20

Three totals, not one, and that came out of a test rather than a plan. The first version summed growth, new locations and disappearances into a single net. A test asserting that a never-before-measured location is not reported as growth failed on the net line, which was the right failure: "new to andy" and "new on disk" are different claims, and the catalog gained fifty entries in v1.2 alone -- every one of which would have shown as growth on the next delta for bytes that had been there all along. Now the net covers only what andy can compare, and the other two are subtotals with their own wording.

Also flushed out a bug that had been quietly corrupting real data: Scanner.run saves the cache whatever --fresh said, and the scan tests did not redirect CACHE_FILE. So every test run replaced the user own ~/.cache/andy/scan.json with a handful of temp directories -- which is why the first --delta I ran reported 322 locations as new. Harmless until this feature existed and then not. Isolated, with a test that runs a Scanner and asserts the real cache file mtime does not move.
