---
id: 36
title: The tree does not show safety, which is what you are deciding
type: feature
status: done
milestone: v1.5
created: 2026-09-21
updated: 2026-09-21
priority: p1
effort: s
area: tui
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-21

v1.4 put the safety mark into the report, because that is where the ratings finally became visible. It did not put it into the browser, which is the screen a person actually decides from -- you scan the list, find something big, and the only way to learn whether it regenerates itself is to select it and read the detail pane, one row at a time.

Proposal. The same three marks the report uses -- s, r, ! -- in a one-character
column between the tree and the size. Two columns of width for the one fact the
list is missing.

Colour carries it too, but the mark has to work without colour: the report
legend established s/r/! precisely because safe and review share a first letter,
and a colour-only signal fails on a monochrome terminal, in a pipe, and for a
good proportion of readers.

What not to do. The size figure is already coloured by magnitude, and recolouring it by safety instead would be cheaper in columns -- but the number and the bar both say magnitude already, so it would be trading a redundant signal for a hidden one and ending with two colour systems on one row meaning different things. A separate column stays legible.

Acceptance criteria
- [x] Every row shows its safety as a character, not only as a colour
- [x] The marks match the report, so the legend is learned once
- [x] A row with no rating shows nothing rather than a guess
- [x] Column arithmetic still holds at every width down to one column
