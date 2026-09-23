---
id: 50
title: The map is a diagram of empty boxes
type: feature
status: done
milestone: v2.2
assignee: Oddur Sigurdsson
created: 2026-09-23
updated: 2026-09-23
closed_at: 2026-09-23
priority: p1
effort: m
area: tui
---

## Problem

The area map is the most visual screen andy has and the only one with no
colour on it at all: outlines, a label, a figure, a share, and air. Area
answers how big; nothing answers what any of it would cost to reclaim, which
is the question the map is best placed to answer at a glance.

## Proposal

Fill each cell with a light shade in the hue of its dominant rating, dimmed —
the rating that holds the most bytes inside that rectangle. Area stays the
magnitude, and the wash says whether that area is yours to take.

Texture rather than a painted background, because the design language paints
no background but the cursor's, and a glyph in the terminal's own foreground
inherits where a background colour would not. Light shade at dim strength is
about as quiet as colour gets while still reading across a rectangle.

The `classic` theme keeps its grey ramp, which is what it is for.

## Acceptance criteria

- [x] A cell is washed with the hue of the rating that dominates it
- [x] The wash is texture, not a painted background
- [x] A cell of mixed ratings takes the one holding the most bytes
- [x] The label and figures stay readable on top of it
- [x] `classic` is unchanged

## 2026-09-23

Washing the whole rectangle was tried first and thrown away. A light shade at
dim strength across every cell turned the map into a wall of texture: the
colour was legible but the shapes were not, and shape is what the map is for.

The colour went into the frame instead. Each cell is outlined in the rating
holding the most bytes inside it, the interior stays air, and the map reads as
quickly as before while saying something it never said.

An unrated rectangle keeps the muted outline, so furniture with nothing to
report still looks like furniture.
