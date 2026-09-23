---
id: 48
title: The bar is a floating blob that carries only length
type: feature
status: done
milestone: v2.2
created: 2026-09-23
updated: 2026-09-23
closed_at: 2026-09-23
priority: p0
effort: m
area: tui
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-23

A bar is drawn as filled blocks padded with spaces, in the plain foreground.
It floats: there is no track, so nothing says how long the bar could have been,
and two bars on adjacent rows share no visible scale. It also carries one fact
where it could carry two -- length is the proportion, and its colour is unspent.

Meanwhile the warm scale is spent on a single character per row, and on this
disk 76% of those characters are the same yellow. Colour is going to the norm.

Proposal, in two parts.

A track. The unfilled remainder of every bar is drawn in `muted`, so each bar
sits in a channel of known length and the column reads as a set of gauges
rather than a ragged edge.

A tint. The filled part takes the hue of the row's rating, dimmed -- a wash,
not a signal. The mark keeps full strength, so precision stays with the
character and mood goes to the field. A row that regenerates itself reads green
at a glance across a screenful; one that wants a look reads warm. Nothing new
is being said: hue still means consequence, and it is now said at two
intensities instead of one.

A category has no single rating and gets no tint.

Acceptance criteria
- [x] Every bar has a track, in muted
- [x] A bar with a rating is tinted with it, dimmed
- [x] A row with no single rating is not tinted
- [x] The plain-text reports get the same treatment
- [x] Bars still fill their exact width, at every width
