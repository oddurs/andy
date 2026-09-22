---
id: 39
title: There is no design language, only four accumulated styles
type: feature
status: done
milestone: v2.0
assignee: Oddur Sigurdsson
created: 2026-09-21
updated: 2026-09-21
priority: p0
effort: l
area: tui
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-21

The interface grew a screen at a time. There are four ways to write a label beside a value -- the header pair, the detail pane pair, the footer key hints and the help overlay columns -- none sharing code and none quite agreeing on gutter, casing or emphasis. Bold marks the title, category rows, the detail title, map cell labels, the help title and the toast: six different jobs. Reverse video marks the cursor and also the entire help panel, so the help looks like a window-sized cursor.

Proposal. Name the channels a terminal actually has -- position, length, weight, hue, reverse, glyph -- and give each exactly one job.

  position  what kind of thing this is: the grid
  length    proportion: the bar, and nothing else
  weight    structure. bold is a heading, dim is supporting, normal is content
  hue       consequence (warm scale), or interaction (cyan). Never data
  reverse   the cursor. Only ever the cursor
  glyph     state: open, closed, marked, unmeasured, a floor

Then two forms, each with one meaning, used everywhere:

  field(key, value)   a fact. dim key in a fixed gutter, value beside it
  hint(key, label)    something you can press. cyan key, dim label

And one row skeleton for every list in the program:

  state . name . context . consequence . quantity . proportion

Written into the file above the drawing code, because a language that lives
only in a commit message is not one, and into the README, because the reader
looking at a screenshot is the person it is for.

Acceptance criteria
- [x] Every attribute in the UI comes from a named role, not a raw constant
- [x] Two label-and-value forms exist and everything uses one of them
- [x] Every list uses the one row skeleton
- [x] The rules are written down where the drawing code is
- [x] The interface loses no information anywhere
