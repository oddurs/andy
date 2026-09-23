---
id: 47
title: There is no tone between the text and the background
type: feature
status: done
milestone: v2.2
assignee: Oddur Sigurdsson
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

The palette has three steps: the text, dim text, and the background. Every rule,
every box outline, every piece of furniture is drawn in dim text -- the same ink
as a secondary label -- so structure and content sit on one plane and the eye
has nothing to rest against.

Every theme measured defines a true middle tone at ANSI 8, and andy has never
touched it:

    theme                ANSI 8 vs bg   text vs bg
    Paris Guimard                3.66        10.68
    Subway Seat                  3.65        10.75
    London Portland              3.93        11.53
    Paris Carrelage              3.89        11.50

Proposal. A `muted` role, ANSI 8, for furniture and nothing else: pane rules,
the outlines of map cells, the track behind a bar. Never text, because 3.7:1
does not pass for text and does not need to -- furniture is not read, it is
seen past.

Four tonal steps where there were three, all of them the theme's own, and
structure separated from content for the first time.

Acceptance criteria
- [x] A `muted` role exists, distinct from `supporting`
- [x] Furniture uses it; no text does
- [x] It degrades where the terminal has no bright colours
- [x] The design language records what it is for
