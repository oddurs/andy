---
id: 49
title: Everything on the screen reads at the same weight
type: feature
status: done
milestone: v2.2
created: 2026-09-23
updated: 2026-09-23
closed_at: 2026-09-23
priority: p1
effort: s
area: tui
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-23

Three things that should not look alike currently do.

A breakdown -- one rustup toolchain of seven -- is drawn exactly like the
location above it, though it is detail rather than a place you would act on.

The volume bar in the header is plain at any level, so a disk at 96% looks the
same as one at 40% until you read the number. The free figure already turns red
under pressure; the bar beside it does not.

And every pane rule, every map outline is dim text, addressed by 0047.

Proposal. Breakdown rows drop to `supporting`, so locations come forward and
their itemisation recedes. The volume bar takes a track like every other bar,
and turns to the review hue only when the disk is nearly full -- consequence,
where it already applies to the figure.

Acceptance criteria
- [x] A breakdown row is quieter than the location it belongs to
- [x] The volume bar has a track and responds to pressure
- [x] Nothing that is not a location borrows a location's weight
