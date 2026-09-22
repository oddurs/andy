---
id: 40
title: The chrome spends five lines on two facts
type: feature
status: done
milestone: v2.0
created: 2026-09-21
updated: 2026-09-21
priority: p1
effort: m
area: tui
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-21

The header is five lines:

    andy                                      303 locations . 7.2s
    ----------------------------------------------------------------
    volume  228G . 218G used . 9.9G free  #################  96%
    mapped  79.9G  37% of used space
    ----------------------------------------------------------------

Two rules within five lines, a line holding one word and a right-aligned
status, and two facts. On a 24-row terminal that is a fifth of the screen
spent on chrome, and the rules are doing decoration rather than separation --
there is nothing between them that needs separating from the thing above.

The detail pane costs six more, with its own label-and-value style, and the
footer a seventh.

Proposal. Rules separate panes and there is one at each boundary. The title
line carries the scan state because that is what a title bar is for, and the
volume and mapped facts share a line, in the field form, because they are the
same kind of fact. Three lines instead of five, so two more rows of the disk
you came to look at.

The detail pane gets the same field form and drops to four lines. The help
overlay stops being drawn in reverse video -- it is a panel, not a cursor --
and is framed with the same rule character the panes use.

Acceptance criteria
- [x] The header is three lines and still says everything it said
- [x] One rule per pane boundary, never two within a few lines
- [x] The detail pane uses the field form
- [x] The help overlay is not drawn as a window-sized cursor
- [x] Everything still fits at every width and height already tested
